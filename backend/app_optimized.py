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
import os
from typing import List, Dict, Optional, Tuple

import data_storage  # 導入本地數據存儲模組
app = Flask(__name__)
CORS(app)

# 數據更新標誌（確保只更新一次）
DATA_UPDATE_DONE = False
DATA_UPDATE_LOCK = threading.Lock()

def ensure_data_updated():
    """確保數據已更新到最新（線程安全，只執行一次）"""
    global DATA_UPDATE_DONE
    
    with DATA_UPDATE_LOCK:
        if DATA_UPDATE_DONE:
            return
        
        try:
            print("\n" + "=" * 60)
            print("🔄 正在檢查並更新數據到最新...")
            print("=" * 60)
            
            # 獲取所有那斯達克股票代碼
            nasdaq_tickers = data_storage.get_nasdaq_tickers()
            
            # 獲取統計資訊
            stats = data_storage.get_storage_stats()
            
            if stats.get('total_stocks', 0) > 0:
                print(f"📊 本地已有 {stats['total_stocks']} 支股票數據")
                print("⏩ 執行增量更新，只下載最新數據...")
                
                # 執行增量更新
                result = data_storage.bulk_update_incremental(
                    symbols=nasdaq_tickers,
                    end_date=None  # None 表示更新到今天
                )
                
                updated = result.get('updated', 0)
                skipped = result.get('skipped', 0)
                print(f"✅ 更新完成！更新了 {updated} 支股票，跳過 {skipped} 支")
            else:
                print("📥 本地無數據，將下載所有歷史數據...")
                print("⏳ 這可能需要幾分鐘，請稍候...")
                
                # 執行完整下載
                result = data_storage.bulk_download_to_local(
                    symbols=nasdaq_tickers
                )
                
                print(f"✅ 下載完成！共 {result.get('successful', 0)} 支股票")
            
            DATA_UPDATE_DONE = True
            print("=" * 60 + "\n")
            
        except Exception as e:
            print(f"⚠️  數據更新警告: {str(e)}")
            print("🔧 API 將使用現有數據繼續運行")
            print("=" * 60 + "\n")
            DATA_UPDATE_DONE = True  # 即使失敗也標記為完成，避免重複嘗試

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

# 指數對應的股票數據目錄
INDEX_DATA_DIRS = {
    '^IXIC': '/app/data/stocks',          # NASDAQ 股票數據目錄
    '^DJI': '/app/data/dow_jones_stocks', # 道瓊工業指數股票數據目錄
    '^GSPC': '/app/data/sp500_stocks'     # S&P 500 股票數據目錄
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

# 在第一個請求前確保數據已更新
@app.before_request
def before_first_request():
    """在第一個請求前執行數據更新"""
    ensure_data_updated()

@app.route('/index/<symbol>', methods=['GET'])
def get_index_data(symbol):
    """獲取指數歷史數據（支持自定義日期範圍，優先從本地讀取）"""
    if symbol not in INDICES:
        return jsonify({'error': '無效的指數代碼'}), 400
    
    # 從查詢參數獲取日期範圍
    start_date = request.args.get('start_date', '2010-01-01')
    end_date = request.args.get('end_date', None)
    
    print(f"\n{'='*50}")
    print(f"API 請求: 獲取 {INDICES[symbol]['name']} 歷史數據")
    print(f"日期範圍: {start_date} 至 {end_date or '今天'}")
    print(f"{'='*50}")
    
    # 優先從本地檔案讀取
    print(f"嘗試從本地檔案讀取 {symbol} ...")
    local_data = data_storage.load_stock_data(symbol)
    print(f"本地檔案讀取結果: {local_data is not None}")
    
    if local_data:
        print(f"本地數據鍵: {list(local_data.keys())}")
        print(f"dates 欄位: {local_data.get('dates') is not None}, {len(local_data.get('dates', [])) if local_data.get('dates') else 0} 筆")
        print(f"close 欄位: {local_data.get('close') is not None}, {len(local_data.get('close', [])) if local_data.get('close') else 0} 筆")
    
    if local_data and local_data.get('dates') and local_data.get('close'):
        # 根據日期範圍過濾數據
        dates = local_data['dates']
        close_prices = local_data['close']
        
        # 找到日期範圍內的索引
        start_idx = 0
        end_idx = len(dates)
        
        for i, date in enumerate(dates):
            if date >= start_date:
                start_idx = i
                break
        
        if end_date:
            for i in range(len(dates) - 1, -1, -1):
                if dates[i] <= end_date:
                    end_idx = i + 1
                    break
        
        # 過濾後的數據
        filtered_dates = dates[start_idx:end_idx]
        filtered_closes = close_prices[start_idx:end_idx]
        
        if filtered_dates:
            # 轉換為 API 格式
            data = [
                {
                    'date': filtered_dates[i],
                    'close': filtered_closes[i],
                    # 這些欄位在本地數據中可能不存在，使用 close 作為替代
                    'open': filtered_closes[i],
                    'high': filtered_closes[i],
                    'low': filtered_closes[i],
                    'volume': 0
                }
                for i in range(len(filtered_dates))
            ]
            
            print(f"✓ 從本地檔案讀取 {len(data)} 筆數據")
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
    
    # 如果本地沒有數據，回退到下載
    print("⚠️  本地無數據，從 Yahoo Finance 下載...")
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
@app.route('/storage/download-all-to-local', methods=['POST'])
def download_all_to_local():
    """下載所有那斯達克股票歷史資料到本地存儲"""
    try:
        # 獲取那斯達克股票列表
        print("正在獲取那斯達克股票列表...")
        nasdaq_tickers = data_storage.get_nasdaq_tickers()
        
        start_date = request.json.get('start_date', '2010-01-01') if request.json else '2010-01-01'
        end_date = request.json.get('end_date', None) if request.json else None
        
        print(f"開始下載 {len(nasdaq_tickers)} 支股票的歷史資料 (從 {start_date})")
        
        # 執行批量下載
        result = data_storage.bulk_download_to_local(
            symbols=nasdaq_tickers,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"下載錯誤: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/storage/update-incremental', methods=['POST'])
def update_incremental():
    """增量更新本地存儲的股票資料（只下載新數據）"""
    try:
        # 獲取那斯達克股票列表
        nasdaq_tickers = data_storage.get_nasdaq_tickers()
        
        end_date = request.json.get('end_date', None) if request.json else None
        
        print(f"開始增量更新 {len(nasdaq_tickers)} 支股票")
        
        # 執行批量增量更新
        result = data_storage.bulk_update_incremental(
            symbols=nasdaq_tickers,
            end_date=end_date
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"更新錯誤: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/storage/stats', methods=['GET'])
def get_storage_stats():
    """獲取本地存儲統計資訊"""
    try:
        stats = data_storage.get_storage_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/storage/load/<symbol>', methods=['GET'])
def load_stock_data_from_local(symbol):
    """從本地存儲載入指定股票的歷史資料"""
    try:
        data = data_storage.load_stock_data(symbol)
        if data is None:
            return jsonify({'error': f'找不到股票 {symbol} 的資料'}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/storage/stock/<symbol>', methods=['GET'])
def get_stock_from_local(symbol):
    """從本地存儲獲取單個股票數據（支持多個數據源）"""
    try:
        start_date = request.args.get('start_date', '2010-01-01')
        end_date = request.args.get('end_date', None)
        
        print(f"從本地獲取股票數據: {symbol}, 日期區間: {start_date} 至 {end_date or '今日'}")
        
        # 嘗試從多個目錄加載股票數據
        stock_data = None
        tried_dirs = []
        
        # 先嘗試從所有可能的目錄加載
        possible_dirs = [
            '/app/data/stocks',          # NASDAQ
            '/app/data/dow_jones_stocks', # 道瓊工業指數
            '/app/data/sp500_stocks'     # S&P 500
        ]
        
        for data_dir in possible_dirs:
            tried_dirs.append(data_dir)
            file_path = os.path.join(data_dir, f"{symbol}.json.gz")
            if os.path.exists(file_path):
                print(f"  ✓ 在 {data_dir} 找到 {symbol}")
                try:
                    import gzip
                    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                        stock_data = json.load(f)
                    break
                except Exception as e:
                    print(f"  ✗ 從 {file_path} 加載失敗: {e}")
                    continue
        
        if not stock_data:
            print(f"  ✗ 在以下目錄中都找不到 {symbol}: {tried_dirs}")
            return jsonify({
                'error': f'找不到股票 {symbol} 的數據',
                'tried_dirs': tried_dirs
            }), 404
        
        # 支援兩種格式：'close' (新格式) 和 'close_prices' (舊格式)
        close_data = stock_data.get('close') or stock_data.get('close_prices')
        if not close_data:
            return jsonify({'error': f'股票 {symbol} 數據格式錯誤'}), 500
        
        # 過濾日期範圍
        filtered_data = []
        for i in range(len(stock_data['dates'])):
            date = stock_data['dates'][i]
            if date >= start_date and (end_date is None or date <= end_date):
                filtered_data.append({
                    'date': date,
                    'close': close_data[i]
                })
        
        if len(filtered_data) == 0:
            return jsonify({'error': '指定日期範圍內沒有數據'}), 404
        
        return jsonify({
            'symbol': symbol,
            'name': stock_data.get('name', symbol),
            'data': filtered_data,
            'data_range': {
                'start': filtered_data[0]['date'],
                'end': filtered_data[-1]['date'],
                'trading_days': len(filtered_data)
            }
        })
    
    except Exception as e:
        print(f"獲取股票數據失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/storage/correlation-analysis', methods=['POST'])
def analyze_correlation_from_local():
    """使用本地存儲數據分析相關性（只保留相關性 > 0.8 的股票）"""
    try:
        # 獲取請求參數
        index_symbol = request.json.get('index_symbol', '^IXIC')
        threshold = request.json.get('threshold', 0.8)
        start_date = request.json.get('start_date', '2010-01-01')
        end_date = request.json.get('end_date', None)
        
        print(f"\n{'='*50}")
        print(f"本地數據相關性分析")
        print(f"指數: {INDICES.get(index_symbol, {}).get('name', index_symbol)}")
        print(f"日期區間: {start_date} 至 {end_date or '今日'}")
        print(f"相關性閾值: > {threshold}")
        print(f"{'='*50}\n")
        
        # 1. 從本地存儲載入指數數據（使用指定的日期區間）
        print(f"正在從本地存儲載入指數數據 {index_symbol}...")
        index_stock_data = data_storage.load_stock_data(index_symbol)
        
        if not index_stock_data or 'dates' not in index_stock_data:
            return jsonify({'error': '無法獲取指數數據，請確保已下載到本地'}), 500
        
        # 支援兩種格式：'close' (新格式) 和 'close_prices' (舊格式)
        index_close_data = index_stock_data.get('close') or index_stock_data.get('close_prices')
        if not index_close_data:
            return jsonify({'error': '指數數據格式錯誤'}), 500
        
        # 轉換指數數據為日期-收盤價字典，並過濾到指定日期區間
        index_close_dict = {}
        for i in range(len(index_stock_data['dates'])):
            date = index_stock_data['dates'][i]
            # 只保留在指定日期區間內的數據
            if date >= start_date and (end_date is None or date <= end_date):
                index_close_dict[date] = index_close_data[i]
        
        index_dates = sorted(index_close_dict.keys())
        
        # 檢查是否有數據
        if len(index_dates) == 0:
            return jsonify({'error': f'在指定的日期區間 ({start_date} ~ {end_date}) 內沒有找到指數數據'}), 400
        
        # 確保日期在指定區間內
        index_dates_set = set(index_dates)
        
        print(f"✓ 指數數據: {len(index_dates)} 個交易日")
        print(f"  日期範圍: {index_dates[0]} 至 {index_dates[-1]}\n")
        
        # 2. 根據指數選擇對應的股票數據目錄
        print("正在掃描本地存儲的股票...")
        stocks_dir = INDEX_DATA_DIRS.get(index_symbol, '/app/data/stocks')
        
        if not os.path.exists(stocks_dir):
            return jsonify({
                'error': f'本地數據目錄不存在: {stocks_dir}',
                'message': f'請先執行 {INDICES[index_symbol]["name"]} 的數據下載'
            }), 404
        
        stock_files = [f for f in os.listdir(stocks_dir) if f.endswith('.json.gz')]
        print(f"✓ 從 {stocks_dir} 找到 {len(stock_files)} 支股票\n")
        
        if len(stock_files) == 0:
            return jsonify({
                'message': '本地存儲為空，請先執行初始化下載',
                'correlations': [],
                'total_analyzed': 0,
                'high_correlation_count': 0
            })
        
        # 3. 並行計算相關性
        print("開始並行計算相關性...")
        results = []
        analyzed_count = 0
        
        def load_stock_from_dir(symbol, stocks_dir):
            """從指定目錄加載股票數據"""
            import gzip
            file_path = os.path.join(stocks_dir, f"{symbol}.json.gz")
            try:
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"從 {file_path} 加載失敗: {e}")
                return None
        
        def analyze_stock(stock_file):
            nonlocal analyzed_count
            symbol = stock_file.replace('.json.gz', '')
            
            # 跳過指數本身
            if symbol == index_symbol:
                return None
            
            # 跳過 NVDA_fixed (重複數據)
            if symbol == 'NVDA_fixed':
                return None
            
            try:
                # 從指定目錄加載股票數據
                stock_data = load_stock_from_dir(symbol, stocks_dir)
                if not stock_data or 'dates' not in stock_data:
                    analyzed_count += 1  # 計數加載失敗的股票
                    return None
                
                # 支援兩種格式：'close' (新格式) 和 'close_prices' (舊格式)
                close_data = stock_data.get('close') or stock_data.get('close_prices')
                if not close_data:
                    analyzed_count += 1  # 計數無收盤價數據的股票
                    return None
                
                # 創建股票的日期-收盤價字典，並過濾到指定日期區間
                stock_close_dict = {}
                for i in range(len(stock_data['dates'])):
                    date = stock_data['dates'][i]
                    # 只保留在指定日期區間內的數據
                    if date >= start_date and (end_date is None or date <= end_date):
                        stock_close_dict[date] = close_data[i]
                
                # 找出與指數共同的交易日（已經在指定區間內）
                common_dates = sorted(index_dates_set & set(stock_close_dict.keys()))
                
                if len(common_dates) < 30:  # 至少需要30個交易日
                    analyzed_count += 1  # 計數交易日不足的股票
                    return None
                
                # 提取共同日期的收盤價
                index_closes = [index_close_dict[date] for date in common_dates]
                stock_closes = [stock_close_dict[date] for date in common_dates]
                
                # 計算相關性
                correlation, p_value = pearsonr(index_closes, stock_closes)
                
                analyzed_count += 1
                if analyzed_count % 100 == 0:
                    print(f"已分析 {analyzed_count}/{len(stock_files)} 支股票...")
                
                # 只返回相關性大於閾值的股票
                if correlation > threshold:
                    # 獲取股票名稱
                    try:
                        ticker = yf.Ticker(symbol)
                        name = ticker.info.get('longName', symbol)
                    except:
                        name = symbol
                    
                    return {
                        'symbol': symbol,
                        'name': name,
                        'correlation': float(correlation),
                        'data_points': len(common_dates)
                    }
                
                return None
                
            except Exception as e:
                print(f"分析 {symbol} 失敗: {e}")
                return None
        
        # 使用線程池並行處理
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(analyze_stock, stock_file) for stock_file in stock_files]
            
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)
        
        # 按相關性排序
        results.sort(key=lambda x: x['correlation'], reverse=True)
        
        print(f"\n{'='*50}")
        print(f"相關性分析完成！")
        print(f"日期區間: {start_date} 至 {end_date or '今日'}")
        print(f"總分析股票數: {analyzed_count}")
        print(f"高相關性股票數 (>{threshold}): {len(results)}")
        print(f"{'='*50}\n")
        
        return jsonify({
            'correlations': results,
            'total_analyzed': analyzed_count,
            'high_correlation_count': len(results),
            'threshold': threshold,
            'index_symbol': index_symbol,
            'index_name': INDICES.get(index_symbol, {}).get('name', index_symbol),
            'start_date': start_date,
            'end_date': end_date or datetime.now().strftime('%Y-%m-%d'),
            'date_range': {
                'start': index_dates[0] if index_dates else start_date,
                'end': index_dates[-1] if index_dates else end_date,
                'trading_days': len(index_dates)
            }
        })
        
    except Exception as e:
        print(f"相關性分析錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ===== 道瓊工業指數專用端點 =====

@app.route('/dow-jones/download-all', methods=['POST'])
def download_dow_jones_stocks():
    """下載道瓊工業指數30支成分股的歷史資料到本地存儲"""
    try:
        import dow_jones_downloader
        
        start_date = request.json.get('start_date', '2010-01-01') if request.json else '2010-01-01'
        end_date = request.json.get('end_date', None) if request.json else None
        max_workers = request.json.get('max_workers', 5) if request.json else 5
        
        print(f"\n開始下載道瓊工業指數成分股歷史資料")
        print(f"起始日期: {start_date}")
        print(f"結束日期: {end_date or '今天'}")
        print(f"並行線程: {max_workers}")
        
        # 執行批量下載
        result = dow_jones_downloader.bulk_download_dow_jones(
            start_date=start_date,
            end_date=end_date,
            max_workers=max_workers
        )
        
        return jsonify({
            'success': True,
            'message': f'成功下載 {result["successful"]}/{result["total_stocks"]} 支股票',
            'total_stocks': result['total_stocks'],
            'successful': result['successful'],
            'failed': result['failed'],
            'elapsed_time_seconds': result['elapsed_time_seconds'],
            'data_dir': '/app/data/dow_jones_stocks'
        })
        
    except Exception as e:
        print(f"下載道瓊工業指數股票失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/dow-jones/download-status', methods=['GET'])
def get_dow_jones_download_status():
    """獲取道瓊工業指數數據下載狀態"""
    try:
        import os
        import json
        
        data_dir = '/app/data/dow_jones_stocks'
        meta_file = '/app/data/dow_jones_meta.json'
        
        # 檢查數據目錄
        if not os.path.exists(data_dir):
            return jsonify({
                'downloaded': False,
                'message': '尚未下載道瓊工業指數成分股數據'
            })
        
        # 統計已下載的股票數量
        stock_files = [f for f in os.listdir(data_dir) if f.endswith('.json.gz')]
        
        # 讀取元數據
        meta = None
        if os.path.exists(meta_file):
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        
        return jsonify({
            'downloaded': True,
            'total_files': len(stock_files),
            'data_dir': data_dir,
            'meta': meta
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== S&P 500 專用端點 =====

@app.route('/sp500/download-all', methods=['POST'])
def download_sp500_stocks():
    """下載 S&P 500 成分股的歷史資料到本地存儲"""
    try:
        import sp500_downloader
        
        start_date = request.json.get('start_date', '2010-01-01') if request.json else '2010-01-01'
        end_date = request.json.get('end_date', None) if request.json else None
        max_workers = request.json.get('max_workers', 10) if request.json else 10
        
        print(f"\n開始下載 S&P 500 成分股歷史資料")
        print(f"起始日期: {start_date}")
        print(f"結束日期: {end_date or '今天'}")
        print(f"並行線程: {max_workers}")
        
        # 執行批量下載
        result = sp500_downloader.bulk_download_sp500(
            start_date=start_date,
            end_date=end_date,
            max_workers=max_workers
        )
        
        if not result:
            return jsonify({'error': '下載失敗'}), 500
        
        return jsonify({
            'success': True,
            'message': f'成功下載 {result["successful"]}/{result["total_stocks"]} 支股票',
            'total_stocks': result['total_stocks'],
            'successful': result['successful'],
            'failed': result['failed'],
            'success_rate': round(result['successful']/result['total_stocks']*100, 1),
            'elapsed_time_seconds': result['elapsed_time_seconds'],
            'data_dir': '/app/data/sp500_stocks'
        })
        
    except Exception as e:
        print(f"下載 S&P 500 股票失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/sp500/download-status', methods=['GET'])
def get_sp500_download_status():
    """獲取 S&P 500 數據下載狀態"""
    try:
        import os
        import json
        
        data_dir = '/app/data/sp500_stocks'
        meta_file = '/app/data/sp500_meta.json'
        
        # 檢查數據目錄
        if not os.path.exists(data_dir):
            return jsonify({
                'downloaded': False,
                'message': '尚未下載 S&P 500 成分股數據'
            })
        
        # 統計已下載的股票數量
        stock_files = [f for f in os.listdir(data_dir) if f.endswith('.json.gz')]
        
        # 讀取元數據
        meta = None
        if os.path.exists(meta_file):
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        
        return jsonify({
            'downloaded': True,
            'total_files': len(stock_files),
            'data_dir': data_dir,
            'meta': meta
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/storage/drawdown-periods', methods=['POST'])
def get_drawdown_periods():
    """
    計算並返回指數的波段下跌區間
    當跌幅超過指定閾值時標記為重要下跌區間
    """
    try:
        data = request.get_json()
        index_symbol = data.get('index_symbol', '^IXIC')
        threshold = float(data.get('threshold', 0.15))  # 默認15%
        
        print(f"\n計算波段下跌區間: {index_symbol}, 閾值: {threshold*100}%")
        
        # 從本地存儲加載指數數據
        stock_data = data_storage.load_stock_data(index_symbol)
        
        # 如果本地沒有，嘗試從 yfinance 獲取
        if not stock_data:
            print(f"本地沒有 {index_symbol} 數據，嘗試從 yfinance 獲取...")
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*16)  # 獲取16年數據
            
            ticker = yf.Ticker(index_symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                return jsonify({'error': f'無法獲取 {index_symbol} 的數據'}), 404
            
            # 轉換為標準格式
            stock_data = {
                'symbol': index_symbol,
                'data': [
                    {
                        'date': date.strftime('%Y-%m-%d'),
                        'close': float(row['Close'])
                    }
                    for date, row in hist.iterrows()
                ]
            }
            print(f"成功從 yfinance 獲取 {len(stock_data['data'])} 筆數據")
        
        # 轉換為DataFrame - 兼容兩種格式
        if 'data' in stock_data and stock_data['data']:
            # 新格式: {data: [{date, close}, ...]}
            df = pd.DataFrame(stock_data['data'])
        elif 'dates' in stock_data and 'close' in stock_data:
            # 舊格式: {dates: [...], close: [...]}
            df = pd.DataFrame({
                'date': stock_data['dates'],
                'close': stock_data['close']
            })
        else:
            return jsonify({'error': f'{index_symbol} 數據格式錯誤'}), 400
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df['close'] = df['close'].astype(float)
        
        # 計算波段高點和下跌區間（優化算法：只追踪重要的下跌）
        drawdown_periods = []
        
        # 方法：追踪running maximum，當從高點下跌超過閾值時標記
        # 但允許在創新高之前就標記下跌區間（不要求必須恢復到峰值）
        running_max = df['close'].iloc[0]
        running_max_date = df['date'].iloc[0]
        running_max_idx = 0
        
        for idx in range(len(df)):
            current_price = df['close'].iloc[idx]
            current_date = df['date'].iloc[idx]
            
            # 如果創新高，更新running maximum
            if current_price > running_max:
                running_max = current_price
                running_max_date = current_date
                running_max_idx = idx
            else:
                # 計算從running max的跌幅
                drawdown_pct = (running_max - current_price) / running_max
                
                # 如果跌幅超過閾值，檢查是否應該創建新區間
                if drawdown_pct >= threshold:
                    # 從running_max到當前找最低點
                    segment = df.iloc[running_max_idx:idx+1]
                    trough_idx = segment['close'].idxmin()
                    trough_price = segment.loc[trough_idx, 'close']
                    trough_date = segment.loc[trough_idx, 'date']
                    
                    actual_drawdown = (running_max - trough_price) / running_max
                    
                    # 檢查是否已經記錄過這個峰值的下跌
                    already_recorded = False
                    for existing in drawdown_periods:
                        if existing['peak_date'] == running_max_date.strftime('%Y-%m-%d'):
                            # 如果新的谷底更低，更新記錄
                            if trough_price < existing['trough_price']:
                                existing['trough_date'] = trough_date.strftime('%Y-%m-%d')
                                existing['trough_price'] = float(trough_price)
                                existing['drawdown_pct'] = float(actual_drawdown)
                                existing['duration_days'] = int((trough_date - running_max_date).days)
                            already_recorded = True
                            break
                    
                    # 如果還沒記錄，創建新記錄
                    if not already_recorded:
                        # 嘗試找恢復日期
                        future_data = df.iloc[idx+1:]
                        recovery_date = None
                        recovery_price = None
                        
                        for future_idx in future_data.index:
                            if df.loc[future_idx, 'close'] >= running_max:
                                recovery_date = df.loc[future_idx, 'date']
                                recovery_price = df.loc[future_idx, 'close']
                                break
                        
                        drawdown_periods.append({
                            'peak_date': running_max_date.strftime('%Y-%m-%d'),
                            'peak_price': float(running_max),
                            'trough_date': trough_date.strftime('%Y-%m-%d'),
                            'trough_price': float(trough_price),
                            'drawdown_pct': float(actual_drawdown),
                            'recovery_date': recovery_date.strftime('%Y-%m-%d') if recovery_date else None,
                            'recovery_price': float(recovery_price) if recovery_price else None,
                            'duration_days': int((trough_date - running_max_date).days)
                        })
        
        # 按峰值日期排序
        drawdown_periods.sort(key=lambda x: x['peak_date'])
        
        print(f"找到 {len(drawdown_periods)} 個超過 {threshold*100}% 的下跌區間")
        
        return jsonify({
            'drawdown_periods': drawdown_periods,
            'total_periods': len(drawdown_periods),
            'threshold': threshold,
            'index_symbol': index_symbol
        })
        
    except Exception as e:
        print(f"計算波段下跌錯誤: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def startup_update_data():
    """啟動時自動更新數據到最新"""
    try:
        print("\n" + "=" * 50)
        print("正在檢查並更新數據到最新...")
        print("=" * 50)
        
        # 獲取所有那斯達克股票代碼
        nasdaq_tickers = data_storage.get_nasdaq_tickers()
        
        # 獲取統計資訊，確認是否需要更新
        stats = data_storage.get_storage_stats()
        
        if stats.get('total_stocks', 0) > 0:
            print(f"本地已有 {stats['total_stocks']} 支股票數據")
            print("執行增量更新，只下載最新數據...")
            
            # 執行增量更新
            result = data_storage.bulk_update_incremental(
                symbols=nasdaq_tickers,
                end_date=None  # None 表示更新到今天
            )
            
            print(f"✓ 更新完成！更新了 {result.get('updated', 0)} 支股票")
        else:
            print("本地無數據，將下載所有歷史數據...")
            print("這可能需要幾分鐘，請稍候...")
            
            # 執行完整下載
            result = data_storage.bulk_download_to_local(
                symbols=nasdaq_tickers
            )
            
            print(f"✓ 下載完成！共 {result.get('successful', 0)} 支股票")
        
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"⚠ 數據更新警告: {str(e)}")
        print("API 將使用現有數據繼續運行")
        print("=" * 50 + "\n")

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
    print("  ✓ 啟動時自動更新數據")
    print("=" * 50)
    print("數據範圍: 2010-01-01 至今")
    print("=" * 50)
    print("API 啟動於 http://localhost:8000")
    print("=" * 50)
    
    # 啟動時更新數據
    startup_update_data()
    
    app.run(host='0.0.0.0', port=8000, debug=False)
