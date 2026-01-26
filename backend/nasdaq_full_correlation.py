"""
那斯達克全部股票相關性分析
下載所有那斯達克股票的歷史收盤價並計算與指數的相關性
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import pearsonr
import redis
import json
import gzip
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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

# 緩存時間設置
CACHE_TTL_TICKER_LIST = 86400 * 7  # 股票列表緩存 7 天
CACHE_TTL_STOCK_DATA = 3600  # 股票數據緩存 1 小時
CACHE_TTL_CORRELATION = 3600  # 相關性數據緩存 1 小時

def cache_result(ttl=3600):
    """緩存裝飾器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not REDIS_AVAILABLE:
                return func(*args, **kwargs)
            
            cache_key = f"{func.__name__}:{':'.join(str(arg) for arg in args)}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    print(f"✓ 緩存命中: {cache_key[:50]}...")
                    return json.loads(gzip.decompress(cached))
            except Exception as e:
                print(f"緩存讀取錯誤: {e}")
            
            result = func(*args, **kwargs)
            
            try:
                if result is not None:
                    compressed = gzip.compress(json.dumps(result).encode())
                    redis_client.setex(cache_key, ttl, compressed)
                    print(f"✓ 緩存保存: {cache_key[:50]}...")
            except Exception as e:
                print(f"緩存保存錯誤: {e}")
            
            return result
        return wrapper
    return decorator

@cache_result(ttl=CACHE_TTL_TICKER_LIST)
def get_nasdaq_tickers():
    """獲取所有那斯達克股票代碼"""
    print("開始下載那斯達克股票列表...")
    try:
        # 使用 pandas 從 Wikipedia 或其他來源獲取
        # 這裡使用 yfinance 的方法獲取
        import requests
        
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
            
            # 備用方案：使用預定義的主要股票列表
            # 這裡列出一些主要的那斯達克股票
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
                'DDOG', 'MDB', 'ZM', 'MRNA', 'ENPH', 'ALGN', 'RIVN', 'LCID'
            ]
            print(f"使用備用列表: {len(major_tickers)} 支主要股票")
            return major_tickers
            
    except Exception as e:
        print(f"獲取股票列表錯誤: {e}")
        return []

@cache_result(ttl=CACHE_TTL_STOCK_DATA)
def download_stock_close_prices(symbol, start_date='2020-01-01', end_date=None):
    """下載單支股票的收盤價"""
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty or len(hist) < 100:  # 至少需要 100 個交易日
            return None
        
        # 只返回收盤價
        return {
            'symbol': symbol,
            'dates': hist.index.strftime('%Y-%m-%d').tolist(),
            'close': hist['Close'].astype(float).tolist()
        }
    except Exception as e:
        print(f"下載 {symbol} 失敗: {e}")
        return None

def calculate_correlation_batch(index_data, stock_symbols, start_date='2020-01-01', end_date=None, max_workers=10):
    """批次計算相關性"""
    print(f"\n開始批次下載 {len(stock_symbols)} 支股票...")
    
    results = []
    successful = 0
    failed = 0
    
    # 準備指數數據
    index_df = pd.DataFrame({
        'date': index_data['dates'],
        'close': index_data['close']
    })
    index_df['date'] = pd.to_datetime(index_df['date'])
    index_df = index_df.set_index('date')
    
    # 並行下載股票數據
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(download_stock_close_prices, symbol, start_date, end_date): symbol
            for symbol in stock_symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                stock_data = future.result()
                
                if stock_data is None:
                    failed += 1
                    continue
                
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
                
                # 獲取股票名稱
                try:
                    ticker = yf.Ticker(symbol)
                    name = ticker.info.get('longName', symbol)
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
                
                if successful % 50 == 0:
                    print(f"進度: {successful}/{len(stock_symbols)} 成功, {failed} 失敗")
                
            except Exception as e:
                failed += 1
                print(f"處理 {symbol} 時發生錯誤: {e}")
    
    print(f"\n完成! 成功: {successful}, 失敗: {failed}")
    
    # 按相關係數排序
    results.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    return results

@app.route('/api/nasdaq/all-correlation', methods=['GET'])
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
        
        print(f"參數: start_date={start_date}, limit={limit}, min_correlation={min_correlation}")
        
        # 下載那斯達克指數數據
        print("下載那斯達克指數數據...")
        index_data = download_stock_close_prices('^IXIC', start_date, end_date)
        
        if index_data is None:
            return jsonify({'error': '無法獲取指數數據'}), 500
        
        # 獲取所有股票代碼
        tickers = get_nasdaq_tickers()
        
        if not tickers:
            return jsonify({'error': '無法獲取股票列表'}), 500
        
        print(f"共有 {len(tickers)} 支股票需要分析")
        
        # 計算相關性（使用緩存）
        cache_key = f"all_correlation:{start_date}:{end_date}:{len(tickers)}"
        
        if REDIS_AVAILABLE:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    print("✓ 使用緩存的相關性結果")
                    results = json.loads(gzip.decompress(cached))
                else:
                    results = calculate_correlation_batch(index_data, tickers, start_date, end_date)
                    # 緩存結果
                    compressed = gzip.compress(json.dumps(results).encode())
                    redis_client.setex(cache_key, CACHE_TTL_CORRELATION, compressed)
            except Exception as e:
                print(f"緩存操作失敗: {e}")
                results = calculate_correlation_batch(index_data, tickers, start_date, end_date)
        else:
            results = calculate_correlation_batch(index_data, tickers, start_date, end_date)
        
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

@app.route('/api/nasdaq/tickers', methods=['GET'])
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

@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'status': 'ok',
        'service': 'nasdaq_full_correlation',
        'cache': 'enabled' if REDIS_AVAILABLE else 'disabled'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
