from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import pearsonr
import redis
import json
import threading
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import io
import time
from typing import List, Dict, Optional, Tuple

app = Flask(__name__)
CORS(app)

# Redis 配置
try:
    redis_client = redis.Redis(
        host='redis',
        port=6379,
        db=0,
        decode_responses=False,
        socket_connect_timeout=5
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✓ Redis 連接成功")
except:
    REDIS_AVAILABLE = False
    print("✗ Redis 不可用，使用無緩存模式")

# 三大指數配置
INDICES = {
    '^IXIC': {
        'name': 'NASDAQ',
        'constituents': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST', 'NFLX']
    },
    '^DJI': {
        'name': '道瓊工業指數',
        'constituents': ['AAPL', 'MSFT', 'UNH', 'GS', 'HD', 'MCD', 'CAT', 'V', 'AMGN', 'BA']
    },
    '^GSPC': {
        'name': 'S&P 500',
        'constituents': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'BRK-B', 'TSLA', 'V', 'UNH']
    }
}

# 緩存時間設置（秒）
CACHE_TTL_STOCK_DATA = 3600  # 股票數據緩存 1 小時
CACHE_TTL_CORRELATION = 7200  # 相關性數據緩存 2 小時
CACHE_TTL_TICKER_LIST = 86400 * 7  # 股票列表緩存 7 天
CACHE_TTL_FULL_CORRELATION = 3600  # 全市場相關性緩存 1 小時

def get_cache_key(prefix, *args):
    """生成緩存鍵"""
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"

def cache_result(ttl=3600):
    """緩存裝飾器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not REDIS_AVAILABLE:
                return func(*args, **kwargs)
            
            # 生成緩存鍵
            cache_key = get_cache_key(func.__name__, *args, *sorted(kwargs.items()))
            
            try:
                # 嘗試從緩存獲取
                cached = redis_client.get(cache_key)
                if cached:
                    print(f"✓ 緩存命中: {cache_key}")
                    return json.loads(gzip.decompress(cached))
            except Exception as e:
                print(f"緩存讀取錯誤: {e}")
            
            # 執行函數
            result = func(*args, **kwargs)
            
            # 保存到緩存
            try:
                if result is not None:
                    compressed = gzip.compress(json.dumps(result).encode())
                    redis_client.setex(cache_key, ttl, compressed)
                    print(f"✓ 緩存保存: {cache_key}")
            except Exception as e:
                print(f"緩存保存錯誤: {e}")
            
            return result
        return wrapper
    return decorator

@cache_result(ttl=CACHE_TTL_STOCK_DATA)
def download_stock_data(symbol, start_date='2010-01-01', end_date=None):
    """從 Yahoo Finance 下載股票歷史數據（帶緩存）"""
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"下載 {symbol} 數據: {start_date} 至 {end_date}")
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            print(f"警告: {symbol} 無數據")
            return None
        
        print(f"成功下載 {symbol} {len(hist)} 筆數據")
        
        # 轉換為所需格式（優化版：使用向量化操作）
        data = {
            'date': hist.index.strftime('%Y-%m-%d').tolist(),
            'open': hist['Open'].astype(float).tolist(),
            'high': hist['High'].astype(float).tolist(),
            'low': hist['Low'].astype(float).tolist(),
            'close': hist['Close'].astype(float).tolist(),
            'volume': hist['Volume'].astype(int).tolist()
        }
        
        # 轉換為列表格式
        result = [
            {
                'date': data['date'][i],
                'open': data['open'][i],
                'high': data['high'][i],
                'low': data['low'][i],
                'close': data['close'][i],
                'volume': data['volume'][i]
            }
            for i in range(len(data['date']))
        ]
        
        return result
    except Exception as e:
        print(f"下載 {symbol} 數據失敗: {str(e)}")
        return None

def calculate_correlation(index_data, stock_data):
    """計算股票與指數的相關係數（優化版）"""
    try:
        # 使用字典查找優化日期對齊
        stock_dict = {item['date']: item['close'] for item in stock_data}
        
        index_closes = []
        stock_closes = []
        
        for item in index_data:
            date = item['date']
            if date in stock_dict:
                index_closes.append(item['close'])
                stock_closes.append(stock_dict[date])
        
        if len(index_closes) < 30:
            print(f"警告: 數據點不足 ({len(index_closes)} 點)")
            return 0.0
        
        print(f"計算相關性: 使用 {len(index_closes)} 個數據點")
        
        # 計算皮爾森相關係數
        correlation, p_value = pearsonr(index_closes, stock_closes)
        
        print(f"相關係數: {correlation:.4f}, p值: {p_value:.6f}")
        
        return float(correlation)
    except Exception as e:
        print(f"計算相關性失敗: {str(e)}")
        return 0.0

def download_stock_info(symbol):
    """下載股票資訊"""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.info.get('longName', symbol)
    except:
        return symbol

@app.route('/index/<symbol>', methods=['GET'])
def get_index_data(symbol):
    """獲取指數歷史數據（支持自定義日期範圍）"""
    if symbol not in INDICES:
        return jsonify({'error': '無效的指數代碼'}), 400
    
    # 從查詢參數獲取日期範圍
    start_date = request.args.get('start_date', '2010-01-01')
    end_date = request.args.get('end_date', None)
    
    print(f"\n{'='*50}")
    print(f"API 請求: 獲取 {INDICES[symbol]['name']} 歷史數據")
    print(f"日期範圍: {start_date} 至 {end_date or '今天'}")
    print(f"{'='*50}")
    
    data = download_stock_data(symbol, start_date=start_date, end_date=end_date)
    
    if data is None or len(data) == 0:
        return jsonify({'error': '無法獲取數據'}), 500
    
    print(f"返回 {len(data)} 筆數據")
    print(f"數據範圍: {data[0]['date']} 至 {data[-1]['date']}")
    
    return jsonify({
        'symbol': symbol,
        'name': INDICES[symbol]['name'],
        'history': data,
        'data_range': {
            'start': data[0]['date'],
            'end': data[-1]['date'],
            'count': len(data)
        }
    })

@app.route('/correlation/<symbol>', methods=['GET'])
@cache_result(ttl=CACHE_TTL_CORRELATION)
def get_correlation_data(symbol):
    """獲取指數成分股與指數的相關性（優化版：並行下載）"""
    if symbol not in INDICES:
        return jsonify({'error': '無效的指數代碼'}), 400
    
    print(f"\n{'='*50}")
    print(f"API 請求: 計算 {INDICES[symbol]['name']} 相關性")
    print(f"{'='*50}")
    
    # 下載指數數據
    index_data = download_stock_data(symbol)
    if index_data is None or len(index_data) == 0:
        return jsonify({'error': '無法獲取指數數據'}), 500
    
    constituents = INDICES[symbol]['constituents']
    results = []
    
    print(f"\n開始並行下載 {len(constituents)} 個成分股數據...")
    
    # 使用線程池並行下載數據
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有下載任務
        future_to_symbol = {
            executor.submit(download_stock_data, stock_symbol): stock_symbol 
            for stock_symbol in constituents
        }
        
        # 同時下載股票名稱
        future_to_info = {
            executor.submit(download_stock_info, stock_symbol): stock_symbol 
            for stock_symbol in constituents
        }
        
        stock_data_map = {}
        stock_name_map = {}
        
        # 收集股票數據
        for future in as_completed(future_to_symbol):
            stock_symbol = future_to_symbol[future]
            try:
                data = future.result()
                if data:
                    stock_data_map[stock_symbol] = data
                    print(f"✓ 下載完成: {stock_symbol}")
            except Exception as e:
                print(f"✗ 下載失敗: {stock_symbol} - {e}")
        
        # 收集股票名稱
        for future in as_completed(future_to_info):
            stock_symbol = future_to_info[future]
            try:
                name = future.result()
                stock_name_map[stock_symbol] = name
            except:
                stock_name_map[stock_symbol] = stock_symbol
    
    print(f"\n計算相關性...")
    
    # 計算相關性
    for stock_symbol in constituents:
        if stock_symbol not in stock_data_map:
            continue
        
        stock_data = stock_data_map[stock_symbol]
        correlation = calculate_correlation(index_data, stock_data)
        
        results.append({
            'symbol': stock_symbol,
            'name': stock_name_map.get(stock_symbol, stock_symbol),
            'correlation': correlation
        })
        
        print(f"完成 {stock_symbol}: 相關性 = {correlation:.4f}")
    
    # 按相關性絕對值排序
    results.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    print(f"\n{'='*50}")
    print(f"相關性計算完成！共 {len(results)} 個成分股")
    print(f"{'='*50}\n")
    
    return results

@cache_result(ttl=CACHE_TTL_TICKER_LIST)
def get_nasdaq_tickers():
    """獲取所有那斯達克股票代碼"""
    print("開始下載那斯達克股票列表...")
    try:
        # 從 NASDAQ 官方 FTP 下載股票列表
        url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
        
        try:
            df = pd.read_csv(url, sep='|')
            # 過濾掉測試股票和 ETF
            df = df[df['Test Issue'] == 'N']
            df = df[df['ETF'] == 'N']
            
            tickers = df['Symbol'].tolist()
            
            # 移除最後一行（通常是文件創建日期）
            if tickers and not tickers[-1].replace('.', '').replace('-', '').isalnum():
                tickers = tickers[:-1]
            
            print(f"✓ 成功獲取 {len(tickers)} 支那斯達克股票")
            return tickers
        except Exception as e:
            print(f"從 NASDAQ FTP 下載失敗: {e}")
            
            # 備用方案：使用擴展的主要股票列表
            major_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA',
                'AVGO', 'COST', 'NFLX', 'AMD', 'PEP', 'CSCO', 'ADBE', 'CMCSA',
                'INTC', 'TXN', 'QCOM', 'AMGN', 'INTU', 'AMAT', 'HON', 'ISRG',
                'BKNG', 'VRTX', 'ADP', 'GILD', 'SBUX', 'REGN', 'MU', 'ADI',
                'LRCX', 'PYPL', 'MDLZ', 'PANW', 'MELI', 'KLAC', 'SNPS', 'CDNS',
                'MAR', 'ABNB', 'CTAS', 'CRWD', 'CSX', 'NXPI', 'ORLY', 'MRVL',
                'ASML', 'FTNT', 'ADSK', 'MNST', 'DASH', 'WDAY', 'AEP', 'PCAR',
                'CHTR', 'CPRT', 'ROST', 'PAYX', 'ODFL', 'KDP', 'FAST', 'KHC',
                'CTSH', 'EA', 'DXCM', 'VRSK', 'GEHC', 'BKR', 'LULU', 'IDXX',
                'XEL', 'EXC', 'MCHP', 'CCEP', 'CSGP', 'TEAM', 'ZS', 'TTWO',
                'ANSS', 'ON', 'CDW', 'BIIB', 'ILMN', 'GFS', 'WBD', 'FANG',
                'DDOG', 'MDB', 'ZM', 'MRNA', 'ENPH', 'ALGN', 'RIVN', 'LCID',
                'COIN', 'ROKU', 'ZI', 'PINS', 'DOCU', 'SNOW', 'NET', 'CRWD',
                'OKTA', 'SHOP', 'SQ', 'UBER', 'LYFT', 'ABNB', 'SPOT', 'RBLX'
            ]
            print(f"使用備用列表: {len(major_tickers)} 支主要股票")
            return major_tickers
            
    except Exception as e:
        print(f"獲取股票列表錯誤: {e}")
        return []

@cache_result(ttl=CACHE_TTL_STOCK_DATA)
def download_stock_close_only(symbol, start_date='2020-01-01', end_date=None, retry_count=3):
    """下載單支股票的收盤價（僅用於相關性計算，帶重試機制）"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    for attempt in range(retry_count):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 100:  # 至少需要 100 個交易日
                return None
            
            # 只返回日期和收盤價
            return {
                'symbol': symbol,
                'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                'close': hist['Close'].astype(float).tolist()
            }
        except Exception as e:
            if attempt < retry_count - 1:
                # 等待後重試（指數退避）
                time.sleep(0.5 * (2 ** attempt))
                continue
            else:
                # 最後一次嘗試失敗
                return None
    
    return None

def download_batch_with_rate_limit(symbols: List[str], start_date: str, end_date: Optional[str], 
                                   max_workers: int = 15, batch_size: int = 100) -> Dict[str, dict]:
    """分批下載股票數據，帶速率限制"""
    results = {}
    total = len(symbols)
    processed = 0
    
    # 將股票列表分成小批次
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_symbols = symbols[batch_start:batch_end]
        
        print(f"\n處理批次 {batch_start}-{batch_end} / {total}...")
        
        # 並行下載這批股票
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(download_stock_close_only, symbol, start_date, end_date): symbol
                for symbol in batch_symbols
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result(timeout=30)  # 30秒超時
                    if data:
                        results[symbol] = data
                    processed += 1
                    
                    if processed % 50 == 0:
                        print(f"已處理: {processed}/{total} ({processed/total*100:.1f}%)")
                        
                except Exception as e:
                    print(f"處理 {symbol} 失敗: {e}")
                    processed += 1
        
        # 批次間短暫延遲，避免速率限制
        if batch_end < total:
            time.sleep(1)
    
    return results

def calculate_correlation_batch_optimized(index_data: dict, stock_symbols: List[str], 
                                         start_date: str = '2020-01-01', 
                                         end_date: Optional[str] = None,
                                         max_workers: int = 15,
                                         batch_size: int = 100) -> List[Dict]:
    """優化的批次相關性計算"""
    print(f"\n{'='*60}")
    print(f"開始分批下載和計算 {len(stock_symbols)} 支股票的相關性")
    print(f"參數: 批次大小={batch_size}, 最大工作線程={max_workers}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # 準備指數數據
    index_df = pd.DataFrame({
        'date': index_data['dates'],
        'close': index_data['close']
    })
    index_df['date'] = pd.to_datetime(index_df['date'])
    index_df = index_df.set_index('date')
    
    # 第一步：分批下載所有股票數據
    print("\n階段 1: 下載股票數據")
    stock_data_dict = download_batch_with_rate_limit(
        stock_symbols, start_date, end_date, max_workers, batch_size
    )
    
    download_time = time.time() - start_time
    print(f"\n下載完成: {len(stock_data_dict)}/{len(stock_symbols)} 支股票 (耗時 {download_time:.1f}秒)")
    
    # 第二步：計算相關性
    print("\n階段 2: 計算相關性")
    results = []
    successful = 0
    failed = 0
    
    for symbol, stock_data in stock_data_dict.items():
        try:
            # 創建 DataFrame 並對齊日期
            stock_df = pd.DataFrame({
                'date': stock_data['dates'],
                'close': stock_data['close']
            })
            stock_df['date'] = pd.to_datetime(stock_df['date'])
            stock_df = stock_df.set_index('date')
            
            # 合併數據
            merged = index_df.join(stock_df, how='inner', rsuffix='_stock')
            
            if len(merged) < 50:  # 至少需要 50 個共同交易日
                failed += 1
                continue
            
            # 計算相關係數
            correlation, p_value = pearsonr(
                merged['close'].values,
                merged['close_stock'].values
            )
            
            # 獲取股票名稱（使用緩存數據）
            try:
                ticker_info = yf.Ticker(symbol)
                name = ticker_info.info.get('longName', symbol)
            except:
                name = symbol
            
            results.append({
                'symbol': symbol,
                'name': name,
                'correlation': float(correlation),
                'p_value': float(p_value),
                'data_points': len(merged)
            })
            
            successful += 1
            
            if successful % 100 == 0:
                print(f"相關性計算進度: {successful}/{len(stock_data_dict)}")
            
        except Exception as e:
            print(f"計算 {symbol} 相關性失敗: {e}")
            failed += 1
    
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"完成! 成功: {successful}, 失敗: {failed}")
    print(f"總耗時: {total_time:.1f}秒 (下載: {download_time:.1f}秒, 計算: {total_time-download_time:.1f}秒)")
    print(f"平均速度: {len(stock_symbols)/total_time:.1f} 股票/秒")
    print(f"{'='*60}\n")
    
    # 按相關係數絕對值排序
    results.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    return results

@app.route('/nasdaq/download-all', methods=['POST'])
def download_all_nasdaq_stocks():
    """下載所有那斯達克股票的歷史資料（不計算相關性）"""
    print("\n" + "="*50)
    print("API 請求: 下載所有那斯達克股票歷史資料")
    print("="*50)
    
    try:
        # 獲取參數
        data = request.get_json() or {}
        start_date = data.get('start_date', request.args.get('start_date', '2020-01-01'))
        end_date = data.get('end_date', request.args.get('end_date', None))
        
        print(f"參數: start_date={start_date}, end_date={end_date}")
        
        # 獲取所有股票代碼
        tickers = get_nasdaq_tickers()
        
        if not tickers:
            return jsonify({'error': '無法獲取股票列表'}), 500
        
        print(f"共有 {len(tickers)} 支股票需要下載")
        
        # 分批下載所有股票數據
        stock_data_dict = download_batch_with_rate_limit(
            tickers, start_date, end_date,
            max_workers=15,
            batch_size=100
        )
        
        # 統計結果
        successful = len(stock_data_dict)
        failed = len(tickers) - successful
        
        # 統計數據點數
        total_data_points = sum(len(data['close']) for data in stock_data_dict.values())
        
        # 生成摘要
        summary = {
            'total_tickers': len(tickers),
            'successful_downloads': successful,
            'failed_downloads': failed,
            'success_rate': f"{successful/len(tickers)*100:.1f}%",
            'total_data_points': total_data_points,
            'date_range': {
                'start': start_date,
                'end': end_date or datetime.now().strftime('%Y-%m-%d')
            },
            'downloaded_symbols': list(stock_data_dict.keys())[:50]  # 只返回前50個作為示例
        }
        
        print(f"\n下載完成:")
        print(f"  成功: {successful}/{len(tickers)} ({summary['success_rate']})")
        print(f"  失敗: {failed}")
        print(f"  總數據點: {total_data_points:,}")
        
        return jsonify({
            'status': 'success',
            'message': f'成功下載 {successful} 支股票的歷史資料',
            'summary': summary
        })
        
    except Exception as e:
        print(f"錯誤: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/nasdaq/download-status', methods=['GET'])
def get_download_status():
    """獲取已緩存的股票數量"""
    try:
        if not REDIS_AVAILABLE:
            return jsonify({
                'status': 'unavailable',
                'message': 'Redis 緩存不可用'
            })
        
        # 獲取所有股票代碼
        tickers = get_nasdaq_tickers()
        
        # 檢查有多少股票已被緩存
        start_date = request.args.get('start_date', '2020-01-01')
        end_date = request.args.get('end_date', None)
        
        cached_count = 0
        cache_keys = []
        
        for symbol in tickers[:100]:  # 只檢查前100個以提高速度
            cache_key = f"download_stock_close_only:{symbol}:{start_date}:{end_date}"
            if redis_client.exists(cache_key):
                cached_count += 1
                cache_keys.append(symbol)
        
        # 估算總緩存數
        estimated_cached = int(cached_count / 100 * len(tickers))
        
        return jsonify({
            'status': 'success',
            'total_tickers': len(tickers),
            'sampled_tickers': 100,
            'cached_in_sample': cached_count,
            'estimated_total_cached': estimated_cached,
            'cache_percentage': f"{cached_count}%",
            'sample_cached_symbols': cache_keys[:20]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/nasdaq/all-correlation', methods=['GET'])
def get_all_nasdaq_correlation():
    """獲取所有那斯達克股票與指數的相關性"""
    print("\n" + "="*50)
    print("API 請求: 計算所有那斯達克股票相關性")
    print("="*50)
    
    try:
        # 獲取參數
        start_date = request.args.get('start_date', '2020-01-01')
        end_date = request.args.get('end_date', None)
        limit = int(request.args.get('limit', 100))  # 默認返回前 100 名
        min_correlation = float(request.args.get('min_correlation', 0.5))  # 最小相關係數
        
        print(f"參數: start_date={start_date}, end_date={end_date}, limit={limit}, min_correlation={min_correlation}")
        
        # 下載那斯達克指數數據
        print("下載那斯達克指數數據...")
        index_data = download_stock_close_only('^IXIC', start_date, end_date)
        
        if index_data is None:
            return jsonify({'error': '無法獲取指數數據'}), 500
        
        # 獲取所有股票代碼
        tickers = get_nasdaq_tickers()
        
        if not tickers:
            return jsonify({'error': '無法獲取股票列表'}), 500
        
        print(f"共有 {len(tickers)} 支股票需要分析")
        
        # 計算相關性（使用優化的批次處理和緩存）
        cache_key = f"all_correlation_v2:{start_date}:{end_date}:{len(tickers)}"
        
        if REDIS_AVAILABLE:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    print("✓ 使用緩存的相關性結果")
                    results = json.loads(gzip.decompress(cached))
                else:
                    # 使用優化的批次處理
                    results = calculate_correlation_batch_optimized(
                        index_data, tickers, start_date, end_date,
                        max_workers=15,  # 降低並發數以提高穩定性
                        batch_size=100   # 每批100支股票
                    )
                    # 緩存結果
                    compressed = gzip.compress(json.dumps(results).encode())
                    redis_client.setex(cache_key, CACHE_TTL_FULL_CORRELATION, compressed)
            except Exception as e:
                print(f"緩存操作失敗: {e}")
                results = calculate_correlation_batch_optimized(
                    index_data, tickers, start_date, end_date,
                    max_workers=15, batch_size=100
                )
        else:
            results = calculate_correlation_batch_optimized(
                index_data, tickers, start_date, end_date,
                max_workers=15, batch_size=100
            )
        
        # 過濾結果
        filtered_results = [
            r for r in results 
            if abs(r['correlation']) >= min_correlation
        ]
        
        # 限制返回數量
        limited_results = filtered_results[:limit]
        
        return jsonify({
            'total_analyzed': len(tickers),
            'total_with_data': len(results),
            'filtered_count': len(filtered_results),
            'returned_count': len(limited_results),
            'correlations': limited_results,
            'index': {
                'symbol': '^IXIC',
                'name': 'NASDAQ Composite',
                'data_points': len(index_data['close'])
            }
        })
        
    except Exception as e:
        print(f"錯誤: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/nasdaq/tickers', methods=['GET'])
def get_tickers_list():
    """獲取那斯達克股票列表"""
    try:
        tickers = get_nasdaq_tickers()
        return jsonify({
            'count': len(tickers),
            'tickers': tickers
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/indices', methods=['GET'])
def get_all_indices():
    """獲取所有支持的指數"""
    return jsonify([
        {'symbol': symbol, 'name': info['name']}
        for symbol, info in INDICES.items()
    ])

@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'ok',
        'message': 'API is running',
        'cache': 'enabled' if REDIS_AVAILABLE else 'disabled'
    })

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """清除所有緩存"""
    if not REDIS_AVAILABLE:
        return jsonify({'message': 'Redis not available'})
    
    try:
        redis_client.flushdb()
        return jsonify({'message': '緩存已清除'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("美國股市分析系統 - 後端 API (優化版)")
    print("=" * 50)
    print("支持的指數:")
    for symbol, info in INDICES.items():
        print(f"  - {info['name']} ({symbol})")
    print("=" * 50)
    print("優化功能:")
    print("  ✓ Redis 緩存")
    print("  ✓ 並行數據下載")
    print("  ✓ gzip 壓縮")
    print("  ✓ 向量化數據處理")
    print("=" * 50)
    print("數據範圍: 2010-01-01 至今")
    print("=" * 50)
    print("API 啟動於 http://localhost:8000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=8000, debug=False)
