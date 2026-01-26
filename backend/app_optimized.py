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

@app.route('/api/index/<symbol>', methods=['GET'])
def get_index_data(symbol):
    """獲取指數歷史數據（2010-至今）"""
    if symbol not in INDICES:
        return jsonify({'error': '無效的指數代碼'}), 400
    
    print(f"\n{'='*50}")
    print(f"API 請求: 獲取 {INDICES[symbol]['name']} 歷史數據")
    print(f"{'='*50}")
    
    data = download_stock_data(symbol)
    
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

@app.route('/api/correlation/<symbol>', methods=['GET'])
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

@app.route('/api/indices', methods=['GET'])
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

@app.route('/api/cache/clear', methods=['POST'])
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
