"""
S&P 500 指數成分股下載器
下載所有 S&P 500 成分股的歷史數據（2010/01/01至今）
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import json
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import urllib.request

# 數據存儲路徑
DATA_DIR = '/app/data/sp500_stocks'
INDEX_DATA_DIR = '/app/data/stocks'  # 指數數據與NASDAQ共用
META_FILE = '/app/data/sp500_meta.json'

def get_sp500_tickers():
    """
    獲取 S&P 500 成分股列表
    從 Wikipedia 獲取最新的成分股列表
    """
    try:
        print("正在從 Wikipedia 獲取 S&P 500 成分股列表...")
        
        # 設置 User-Agent 避免 403 錯誤
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # 從 Wikipedia 讀取 S&P 500 成分股表格
        with urllib.request.urlopen(req) as response:
            tables = pd.read_html(response)
        
        sp500_table = tables[0]
        
        # 獲取股票代碼列
        tickers = sp500_table['Symbol'].tolist()
        
        # 清理股票代碼（移除特殊字符）
        tickers = [ticker.replace('.', '-') for ticker in tickers]
        
        print(f"✓ 成功獲取 {len(tickers)} 支 S&P 500 成分股")
        return tickers
        
    except Exception as e:
        print(f"從 Wikipedia 獲取失敗: {e}")
        
        # 備用方案：使用預定義的主要成分股列表（前100大）
        major_tickers = [
            # 科技股
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA',
            'AVGO', 'ORCL', 'CSCO', 'ADBE', 'CRM', 'ACN', 'AMD', 'INTC',
            'IBM', 'QCOM', 'TXN', 'INTU', 'AMAT', 'ADI', 'NOW', 'PANW',
            
            # 金融股
            'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'SPGI',
            'BLK', 'AXP', 'C', 'SCHW', 'CB', 'MMC', 'PGR', 'AON', 'TFC',
            
            # 醫療保健
            'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE',
            'AMGN', 'BMY', 'ISRG', 'GILD', 'CVS', 'CI', 'ELV', 'MCK',
            
            # 消費品
            'PG', 'COST', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX',
            'PEP', 'KO', 'WMT', 'PM', 'CL', 'MDLZ', 'GIS', 'HSY',
            
            # 工業
            'CAT', 'HON', 'BA', 'UPS', 'RTX', 'LMT', 'GE', 'MMM', 'DE',
            'EMR', 'ETN', 'ITW', 'FDX', 'CSX', 'NSC', 'WM', 'RSG',
            
            # 能源
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'PSX', 'VLO',
            
            # 通訊服務
            'DIS', 'NFLX', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR',
            
            # 公用事業
            'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL',
            
            # 房地產
            'PLD', 'AMT', 'CCI', 'EQIX', 'PSA', 'SPG', 'O', 'WELL',
            
            # 材料
            'LIN', 'APD', 'ECL', 'SHW', 'DD', 'NEM', 'FCX', 'NUE'
        ]
        
        print(f"使用備用列表: {len(major_tickers)} 支主要成分股")
        return major_tickers

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
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist.empty:
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
            
            return {
                'symbol': symbol,
                'name': name,
                'data_points': len(dates),
                'start_date': dates[0] if dates else None,
                'end_date': dates[-1] if dates else None
            }
            
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(2)
            
    return None

def download_index_data(index_symbol='^GSPC', start_date='2010-01-01', end_date=None):
    """
    下載 S&P 500 指數數據
    
    Args:
        index_symbol: 指數代碼
        start_date: 起始日期
        end_date: 結束日期
    """
    try:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n正在下載 S&P 500 指數 ({index_symbol})...")
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
            'name': 'S&P 500',
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

def bulk_download_sp500(start_date='2010-01-01', end_date=None, max_workers=10):
    """
    批次下載所有 S&P 500 成分股
    
    Args:
        start_date: 起始日期
        end_date: 結束日期
        max_workers: 並行下載線程數
    """
    ensure_data_dirs()
    
    # 獲取成分股列表
    tickers = get_sp500_tickers()
    if not tickers:
        print("✗ 無法獲取 S&P 500 成分股列表")
        return None
    
    # 先下載指數數據
    print("=" * 60)
    print("步驟 1: 下載 S&P 500 指數數據")
    print("=" * 60)
    download_index_data('^GSPC', start_date, end_date)
    
    # 下載成分股
    print("\n" + "=" * 60)
    print(f"步驟 2: 下載 {len(tickers)} 支成分股數據")
    print("=" * 60)
    print(f"起始日期: {start_date}")
    print(f"結束日期: {end_date or '今天'}")
    print(f"並行線程: {max_workers}")
    print()
    
    results = []
    successful = 0
    failed = 0
    start_time = time.time()
    
    # 分批下載以避免過載
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"\n處理批次 {i//batch_size + 1}/{(len(tickers)-1)//batch_size + 1} ({len(batch)} 支股票)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(download_stock_data, symbol, start_date, end_date): symbol
                for symbol in batch
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        successful += 1
                        if successful % 10 == 0:
                            print(f"  進度: {successful}/{len(tickers)}")
                    else:
                        failed += 1
                except Exception as e:
                    print(f"處理 {symbol} 時發生錯誤: {e}")
                    failed += 1
        
        # 批次間休息
        if i + batch_size < len(tickers):
            time.sleep(1)
    
    elapsed_time = time.time() - start_time
    
    # 保存元數據
    meta = {
        'total_stocks': len(tickers),
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
    print(f"總計股票: {len(tickers)}")
    print(f"成功下載: {successful}")
    print(f"失敗: {failed}")
    print(f"成功率: {successful/len(tickers)*100:.1f}%")
    print(f"總耗時: {elapsed_time:.2f} 秒")
    print(f"平均每股: {elapsed_time/len(tickers):.2f} 秒")
    print(f"數據目錄: {DATA_DIR}")
    print(f"元數據文件: {META_FILE}")
    print("=" * 60)
    
    return meta

if __name__ == '__main__':
    print("\n")
    print("=" * 60)
    print("S&P 500 成分股數據下載器")
    print("=" * 60)
    print(f"數據範圍: 2010-01-01 至今")
    print("=" * 60)
    print("\n")
    
    # 開始下載
    result = bulk_download_sp500(
        start_date='2010-01-01',
        end_date=None,  # 默認到今天
        max_workers=10  # 10個並行線程
    )
    
    if result:
        print("\n✓ 所有下載任務完成！")
    else:
        print("\n✗ 下載失敗")
