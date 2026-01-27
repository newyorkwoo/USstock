from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_compress import Compress
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import pearsonr
from functools import lru_cache
import hashlib
import json

app = Flask(__name__)
CORS(app)
Compress(app)  # 啟用 gzip 壓縮

# 內存緩存
cache = {}

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

def download_stock_data(symbol, start_date='2010-01-01', end_date=None):
    """從 Yahoo Finance 下載股票歷史數據
    
    Args:
        symbol: 股票代碼
        start_date: 開始日期，默認 2010-01-01
        end_date: 結束日期，默認為今天
    """
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 檢查緩存
        cache_key = f"{symbol}_{start_date}_{end_date}"
        if cache_key in cache:
            print(f"✓ 使用緩存: {symbol}")
            return cache[cache_key]
        
        print(f"下載 {symbol} 數據: {start_date} 至 {end_date}")
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            print(f"警告: {symbol} 無數據")
            return None
        
        print(f"成功下載 {symbol} {len(hist)} 筆數據")
        
        # 轉換為所需格式
        data = []
        for index, row in hist.iterrows():
            data.append({
                'date': index.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
        
        # 緩存數據
        cache[cache_key] = data
        
        return data
    except Exception as e:
        print(f"下載 {symbol} 數據失敗: {str(e)}")
        return None

def calculate_correlation(index_data, stock_data):
    """計算股票與指數的相關係數
    
    使用收盤價計算皮爾森相關係數
    只使用日期對齊的數據點
    """
    try:
        # 轉換為 DataFrame 並優化
        index_df = pd.DataFrame(index_data, columns=['date', 'close'])
        stock_df = pd.DataFrame(stock_data, columns=['date', 'close'])
        
        # 確保日期格式正確
        index_df['date'] = pd.to_datetime(index_df['date'])
        stock_df['date'] = pd.to_datetime(stock_df['date'])
        
        # 重命名列
        index_df.rename(columns={'close': 'index_close'}, inplace=True)
        stock_df.rename(columns={'close': 'stock_close'}, inplace=True)
        
        # 合併數據（內連接，只保留共同日期）
        merged = pd.merge(index_df, stock_df, on='date', how='inner')
        
        if len(merged) < 30:  # 至少需要30個數據點
            print(f"警告: 數據點不足 ({len(merged)} 點)")
            return 0.0
        
        print(f"計算相關性: 使用 {len(merged)} 個數據點")
        
        # 使用 numpy 加速計算
        correlation = np.corrcoef(merged['index_close'].values, merged['stock_close'].values)[0, 1]
        
        print(f"相關係數: {correlation:.4f}")
        
        return float(correlation)
    except Exception as e:
        print(f"計算相關性失敗: {str(e)}")
        return 0.0

@app.route('/api/index/<symbol>', methods=['GET'])
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

@app.route('/api/correlation/<symbol>', methods=['GET'])
def get_correlation_data(symbol):
    """獲取指數成分股與指數的相關性（基於2010-至今數據）"""
    if symbol not in INDICES:
        return jsonify({'error': '無效的指數代碼'}), 400
    
    print(f"\n{'='*50}")
    print(f"API 請求: 計算 {INDICES[symbol]['name']} 相關性")
    print(f"{'='*50}")
    
    # 下載指數數據
    index_data = download_stock_data(symbol)
    if index_data is None or len(index_data) == 0:
        return jsonify({'error': '無法獲取指數數據'}), 500
    
    # 計算每個成分股的相關性
    constituents = INDICES[symbol]['constituents']
    results = []
    
    print(f"\n開始計算 {len(constituents)} 個成分股的相關性...")
    
    for i, stock_symbol in enumerate(constituents, 1):
        print(f"\n[{i}/{len(constituents)}] 處理 {stock_symbol}")
        stock_data = download_stock_data(stock_symbol)
        
        if stock_data is None or len(stock_data) == 0:
            print(f"跳過 {stock_symbol}: 無數據")
            continue
        
        correlation = calculate_correlation(index_data, stock_data)
        
        # 獲取股票名稱
        try:
            ticker = yf.Ticker(stock_symbol)
            stock_name = ticker.info.get('longName', stock_symbol)
        except:
            stock_name = stock_symbol
        
        results.append({
            'symbol': stock_symbol,
            'name': stock_name,
            'correlation': correlation
        })
        
        print(f"完成 {stock_symbol}: {stock_name}, 相關性 = {correlation:.4f}")
    
    # 按相關性絕對值排序
    results.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    print(f"\n{'='*50}")
    print(f"相關性計算完成！共 {len(results)} 個成分股")
    print(f"{'='*50}\n")
    
    return jsonify(results)

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
    return jsonify({'status': 'ok', 'message': 'API is running'})

if __name__ == '__main__':
    print("=" * 50)
    print("美國股市分析系統 - 後端 API")
    print("=" * 50)
    print("支持的指數:")
    for symbol, info in INDICES.items():
        print(f"  - {info['name']} ({symbol})")
    print("=" * 50)
    print("數據範圍: 2010-01-01 至今")
    print("相關性分析: 基於收盤價的皮爾森相關係數")
    print("=" * 50)
    print("API 啟動於 http://localhost:8000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=8000, debug=True)
