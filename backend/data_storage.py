"""
本地數據存儲管理模組
- 將股票歷史數據持久化到本地文件
- 支持增量更新
- 自動管理數據版本
"""

import os
import json
import gzip
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf

# 數據存儲路徑
DATA_DIR = '/app/data/stocks'
META_FILE = '/app/data/meta.json'

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

def ensure_data_dir():
    """確保數據目錄存在"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)

def get_stock_file_path(symbol: str) -> str:
    """獲取股票數據文件路徑"""
    return os.path.join(DATA_DIR, f"{symbol}.json.gz")

def save_stock_data(symbol: str, dates: List[str], close_prices: List[float], 
                    start_date: str, end_date: str) -> bool:
    """
    保存股票數據到本地文件
    
    Args:
        symbol: 股票代碼
        dates: 日期列表
        close_prices: 收盤價列表
        start_date: 起始日期
        end_date: 結束日期
    
    Returns:
        是否保存成功
    """
    try:
        ensure_data_dir()
        
        data = {
            'symbol': symbol,
            'dates': dates,
            'close': close_prices,
            'start_date': start_date,
            'end_date': end_date,
            'last_updated': datetime.now().isoformat(),
            'data_points': len(dates)
        }
        
        file_path = get_stock_file_path(symbol)
        
        # 使用 gzip 壓縮保存
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f)
        
        return True
    except Exception as e:
        print(f"保存 {symbol} 數據失敗: {e}")
        return False

def load_stock_data(symbol: str) -> Optional[Dict]:
    """
    從本地文件加載股票數據
    
    Args:
        symbol: 股票代碼
    
    Returns:
        股票數據字典，如果不存在則返回 None
    """
    try:
        file_path = get_stock_file_path(symbol)
        
        if not os.path.exists(file_path):
            return None
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        print(f"加載 {symbol} 數據失敗: {e}")
        return None

def get_last_date(symbol: str) -> Optional[str]:
    """
    獲取股票數據的最後日期
    
    Args:
        symbol: 股票代碼
    
    Returns:
        最後日期，如果不存在則返回 None
    """
    data = load_stock_data(symbol)
    if data and data.get('dates'):
        return data['dates'][-1]
    return None

def needs_update(symbol: str, target_date: str = None) -> Tuple[bool, Optional[str]]:
    """
    檢查股票數據是否需要更新
    
    Args:
        symbol: 股票代碼
        target_date: 目標日期（默認為今天）
    
    Returns:
        (是否需要更新, 最後日期)
    """
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    last_date = get_last_date(symbol)
    
    if last_date is None:
        # 沒有本地數據，需要完整下載
        return True, None
    
    # 如果最後日期小於目標日期，需要增量更新
    needs_update = last_date < target_date
    return needs_update, last_date

def download_and_save_stock(symbol: str, start_date: str = '2010-01-01', 
                            end_date: str = None) -> bool:
    """
    下載並保存股票數據（完整下載）
    
    Args:
        symbol: 股票代碼
        start_date: 起始日期
        end_date: 結束日期
    
    Returns:
        是否成功
    """
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 下載數據
        stock = yf.Ticker(symbol)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty or len(hist) < 100:
            return False
        
        # 提取日期和收盤價
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        close_prices = hist['Close'].tolist()
        
        # 保存到本地
        return save_stock_data(symbol, dates, close_prices, start_date, end_date)
    
    except Exception as e:
        print(f"下載 {symbol} 失敗: {e}")
        return False

def update_stock_incremental(symbol: str, end_date: str = None) -> bool:
    """
    增量更新股票數據
    
    Args:
        symbol: 股票代碼
        end_date: 結束日期
    
    Returns:
        是否成功
    """
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 檢查是否需要更新
        need_update, last_date = needs_update(symbol, end_date)
        
        if not need_update:
            return True  # 已經是最新
        
        if last_date is None:
            # 沒有本地數據，執行完整下載
            return download_and_save_stock(symbol, '2010-01-01', end_date)
        
        # 加載現有數據
        old_data = load_stock_data(symbol)
        if old_data is None:
            return download_and_save_stock(symbol, '2010-01-01', end_date)
        
        # 計算增量更新的起始日期（最後日期的下一天）
        last_datetime = datetime.strptime(last_date, '%Y-%m-%d')
        update_start = (last_datetime + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 下載新數據
        stock = yf.Ticker(symbol)
        new_hist = stock.history(start=update_start, end=end_date)
        
        if new_hist.empty:
            # 沒有新數據
            return True
        
        # 合併數據
        new_dates = new_hist.index.strftime('%Y-%m-%d').tolist()
        new_close_prices = new_hist['Close'].tolist()
        
        combined_dates = old_data['dates'] + new_dates
        combined_close = old_data['close'] + new_close_prices
        
        # 保存合併後的數據
        return save_stock_data(symbol, combined_dates, combined_close, 
                              old_data['start_date'], end_date)
    
    except Exception as e:
        print(f"增量更新 {symbol} 失敗: {e}")
        return False

def save_metadata(metadata: Dict):
    """保存元數據"""
    try:
        ensure_data_dir()
        with open(META_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"保存元數據失敗: {e}")

def load_metadata() -> Dict:
    """加載元數據"""
    try:
        if os.path.exists(META_FILE):
            with open(META_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加載元數據失敗: {e}")
    
    return {
        'last_full_download': None,
        'last_update': None,
        'total_stocks': 0,
        'start_date': '2010-01-01'
    }

def get_storage_stats() -> Dict:
    """獲取存儲統計信息"""
    try:
        ensure_data_dir()
        
        files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json.gz')]
        total_size = sum(os.path.getsize(os.path.join(DATA_DIR, f)) for f in files)
        
        metadata = load_metadata()
        
        return {
            'total_stocks': len(files),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'data_directory': DATA_DIR,
            'last_full_download': metadata.get('last_full_download'),
            'last_update': metadata.get('last_update'),
            'start_date': metadata.get('start_date', '2010-01-01')
        }
    except Exception as e:
        return {
            'error': str(e)
        }

def bulk_download_to_local(symbols: List[str], start_date: str = '2010-01-01',
                           end_date: str = None) -> Dict:
    """
    批量下載股票數據到本地
    
    Args:
        symbols: 股票代碼列表
        start_date: 起始日期
        end_date: 結束日期
    
    Returns:
        下載統計
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    success_count = 0
    fail_count = 0
    total_data_points = 0
    
    for i, symbol in enumerate(symbols):
        try:
            if download_and_save_stock(symbol, start_date, end_date):
                success_count += 1
                data = load_stock_data(symbol)
                if data:
                    total_data_points += data.get('data_points', 0)
            else:
                fail_count += 1
            
            # 每100支顯示進度
            if (i + 1) % 100 == 0:
                print(f"批量下載進度: {i + 1}/{len(symbols)}")
        
        except Exception as e:
            print(f"下載 {symbol} 時發生錯誤: {e}")
            fail_count += 1
    
    # 更新元數據
    metadata = load_metadata()
    metadata['last_full_download'] = datetime.now().isoformat()
    metadata['last_update'] = datetime.now().isoformat()
    metadata['total_stocks'] = success_count
    metadata['start_date'] = start_date
    save_metadata(metadata)
    
    return {
        'total': len(symbols),
        'success': success_count,
        'failed': fail_count,
        'success_rate': f"{success_count / len(symbols) * 100:.1f}%",
        'total_data_points': total_data_points,
        'date_range': {
            'start': start_date,
            'end': end_date
        }
    }

def bulk_update_incremental(symbols: List[str], end_date: str = None) -> Dict:
    """
    批量增量更新股票數據
    
    Args:
        symbols: 股票代碼列表
        end_date: 結束日期
    
    Returns:
        更新統計
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    updated_count = 0
    skipped_count = 0
    fail_count = 0
    new_data_points = 0
    
    for i, symbol in enumerate(symbols):
        try:
            need_update, last_date = needs_update(symbol, end_date)
            
            if not need_update:
                skipped_count += 1
                continue
            
            old_data = load_stock_data(symbol)
            old_points = old_data.get('data_points', 0) if old_data else 0
            
            if update_stock_incremental(symbol, end_date):
                updated_count += 1
                new_data = load_stock_data(symbol)
                if new_data:
                    new_data_points += (new_data.get('data_points', 0) - old_points)
            else:
                fail_count += 1
            
            # 每100支顯示進度
            if (i + 1) % 100 == 0:
                print(f"增量更新進度: {i + 1}/{len(symbols)}")
        
        except Exception as e:
            print(f"更新 {symbol} 時發生錯誤: {e}")
            fail_count += 1
    
    # 更新元數據
    metadata = load_metadata()
    metadata['last_update'] = datetime.now().isoformat()
    save_metadata(metadata)
    
    return {
        'total': len(symbols),
        'updated': updated_count,
        'skipped': skipped_count,
        'failed': fail_count,
        'new_data_points': new_data_points,
        'end_date': end_date
    }
