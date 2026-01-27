"""
道瓊工業指數成分股下載器
下載所有道瓊工業指數成分股的歷史數據（2010/01/01至今）
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import json
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 數據存儲路徑
DATA_DIR = '/app/data/dow_jones_stocks'
INDEX_DATA_DIR = '/app/data/stocks'  # 指數數據與NASDAQ共用
META_FILE = '/app/data/dow_jones_meta.json'

# 道瓊工業指數30支成分股（2024年最新）
DOW_JONES_COMPONENTS = [
    'AAPL',  # Apple Inc.
    'MSFT',  # Microsoft Corporation
    'UNH',   # UnitedHealth Group Incorporated
    'GS',    # Goldman Sachs Group Inc.
    'HD',    # Home Depot Inc.
    'MCD',   # McDonald's Corporation
    'CAT',   # Caterpillar Inc.
    'V',     # Visa Inc.
    'AMGN',  # Amgen Inc.
    'BA',    # Boeing Company
    'TRV',   # Travelers Companies Inc.
    'AXP',   # American Express Company
    'JPM',   # JPMorgan Chase & Co.
    'IBM',   # International Business Machines Corporation
    'HON',   # Honeywell International Inc.
    'AMZN',  # Amazon.com Inc.
    'CVX',   # Chevron Corporation
    'JNJ',   # Johnson & Johnson
    'PG',    # Procter & Gamble Company
    'WMT',   # Walmart Inc.
    'CRM',   # Salesforce Inc.
    'DIS',   # Walt Disney Company
    'NKE',   # Nike Inc.
    'MRK',   # Merck & Co. Inc.
    'KO',    # Coca-Cola Company
    'CSCO',  # Cisco Systems Inc.
    'VZ',    # Verizon Communications Inc.
    'INTC',  # Intel Corporation
    'WBA',   # Walgreens Boots Alliance Inc.
    'DOW'    # Dow Inc.
]

def ensure_data_dirs():
    """確保數據目錄存在"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(INDEX_DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)

def get_stock_file_path(symbol: str) -> str:
    """獲取股票數據文件路徑"""
    return os.path.join(DATA_DIR, f"{symbol}.json.gz")

def download_stock_data(symbol: str, start_date='2010-01-01', end_date=None, retry_count=3):
    """
    下載單支股票的歷史數據
    
    Args:
        symbol: 股票代碼
        start_date: 起始日期
        end_date: 結束日期
        retry_count: 重試次數
    """
    for attempt in range(retry_count):
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            print(f"正在下載 {symbol}... (嘗試 {attempt + 1}/{retry_count})")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
                print(f"  ✗ {symbol} 無數據")
                return None
            
            # 獲取股票名稱
            try:
                info = ticker.info
                name = info.get('longName') or info.get('shortName') or symbol
            except:
                name = symbol
            
            # 準備數據
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            close_prices = hist['Close'].astype(float).tolist()
            
            # 保存數據
            data = {
                'symbol': symbol,
                'name': name,
                'dates': dates,
                'close': close_prices,
                'start_date': start_date,
                'end_date': end_date,
                'download_time': datetime.now().isoformat()
            }
            
            file_path = get_stock_file_path(symbol)
            with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f)
            
            print(f"  ✓ {symbol} ({name}) - {len(dates)} 筆數據")
            return {
                'symbol': symbol,
                'name': name,
                'data_points': len(dates),
                'start_date': dates[0] if dates else None,
                'end_date': dates[-1] if dates else None
            }
            
        except Exception as e:
            print(f"  ✗ {symbol} 下載失敗 (嘗試 {attempt + 1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(2)  # 等待2秒後重試
            
    return None

def download_index_data(index_symbol='^DJI', start_date='2010-01-01', end_date=None):
    """
    下載道瓊工業指數數據
    
    Args:
        index_symbol: 指數代碼
        start_date: 起始日期
        end_date: 結束日期
    """
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n正在下載道瓊工業指數 ({index_symbol})...")
        ticker = yf.Ticker(index_symbol)
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            print(f"✗ {index_symbol} 無數據")
            return False
        
        # 準備數據
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        close_prices = hist['Close'].astype(float).tolist()
        
        # 保存到INDEX_DATA_DIR（與NASDAQ指數共用）
        data = {
            'symbol': index_symbol,
            'name': '道瓊工業指數',
            'dates': dates,
            'close': close_prices,
            'start_date': start_date,
            'end_date': end_date,
            'download_time': datetime.now().isoformat()
        }
        
        file_path = os.path.join(INDEX_DATA_DIR, f"{index_symbol.replace('^', '')}.json.gz")
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f)
        
        print(f"✓ {index_symbol} - {len(dates)} 筆數據")
        return True
        
    except Exception as e:
        print(f"✗ 下載指數失敗: {e}")
        return False

def bulk_download_dow_jones(start_date='2010-01-01', end_date=None, max_workers=5):
    """
    批次下載所有道瓊工業指數成分股
    
    Args:
        start_date: 起始日期
        end_date: 結束日期
        max_workers: 並行下載線程數
    """
    ensure_data_dirs()
    
    # 先下載指數數據
    print("=" * 60)
    print("步驟 1: 下載道瓊工業指數數據")
    print("=" * 60)
    download_index_data('^DJI', start_date, end_date)
    
    # 下載成分股
    print("\n" + "=" * 60)
    print(f"步驟 2: 下載 {len(DOW_JONES_COMPONENTS)} 支成分股數據")
    print("=" * 60)
    print(f"起始日期: {start_date}")
    print(f"結束日期: {end_date or '今天'}")
    print(f"並行線程: {max_workers}")
    print()
    
    results = []
    successful = 0
    failed = 0
    start_time = time.time()
    
    # 並行下載
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(download_stock_data, symbol, start_date, end_date): symbol
            for symbol in DOW_JONES_COMPONENTS
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"處理 {symbol} 時發生錯誤: {e}")
                failed += 1
    
    elapsed_time = time.time() - start_time
    
    # 保存元數據
    meta = {
        'total_stocks': len(DOW_JONES_COMPONENTS),
        'successful': successful,
        'failed': failed,
        'start_date': start_date,
        'end_date': end_date or datetime.now().strftime('%Y-%m-%d'),
        'download_time': datetime.now().isoformat(),
        'elapsed_time_seconds': round(elapsed_time, 2),
        'stocks': results
    }
    
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    # 打印統計
    print("\n" + "=" * 60)
    print("下載完成統計")
    print("=" * 60)
    print(f"總計股票: {len(DOW_JONES_COMPONENTS)}")
    print(f"成功下載: {successful}")
    print(f"失敗: {failed}")
    print(f"總耗時: {elapsed_time:.2f} 秒")
    print(f"平均每股: {elapsed_time/len(DOW_JONES_COMPONENTS):.2f} 秒")
    print(f"數據目錄: {DATA_DIR}")
    print(f"元數據文件: {META_FILE}")
    print("=" * 60)
    
    return meta

if __name__ == '__main__':
    print("\n")
    print("=" * 60)
    print("道瓊工業指數成分股數據下載器")
    print("=" * 60)
    print(f"成分股數量: {len(DOW_JONES_COMPONENTS)}")
    print(f"數據範圍: 2010-01-01 至今")
    print("=" * 60)
    print("\n")
    
    # 開始下載
    result = bulk_download_dow_jones(
        start_date='2010-01-01',
        end_date=None,  # 默認到今天
        max_workers=5   # 5個並行線程
    )
    
    print("\n✓ 所有下載任務完成！")
