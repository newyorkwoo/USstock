#!/usr/bin/env python3
"""
自動更新股票指數及成分股數據腳本
每天自動從 Yahoo Finance 更新：
1. 三大指數（NASDAQ, DJI, S&P 500）
2. S&P 500 成分股（503支）
3. NASDAQ 已有本地數據的股票（增量更新）
4. 同步所有數據目錄
"""

import yfinance as yf
import json
import gzip
from datetime import datetime, timedelta
import sys
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import shutil
import time

# 數據存儲目錄
DATA_DIR = '/app/data/stocks'

def update_index(symbol, name):
    """更新單一指數數據"""
    try:
        print(f'\n正在更新 {name} ({symbol})...', flush=True)
        
        # 下載歷史數據（從2010年至今）
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start='2010-01-01')
        
        if hist.empty:
            print(f'❌ {name}: 無法獲取數據', flush=True)
            return False
        
        # 獲取完整名稱
        try:
            info = ticker.info
            full_name = info.get('longName') or info.get('shortName') or symbol
        except:
            full_name = symbol
        
        # 準備數據
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        close_prices = hist['Close'].astype(float).tolist()
        
        data = {
            'symbol': symbol,
            'name': full_name,
            'dates': dates,
            'close': close_prices,
            'start_date': '2010-01-01',
            'end_date': dates[-1],
            'download_time': datetime.now().isoformat()
        }
        
        # 保存數據
        file_path = os.path.join(DATA_DIR, f'{symbol}.json.gz')
        os.makedirs(DATA_DIR, exist_ok=True)
        
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f)
        
        print(f'✓ {name}: 成功更新 {len(dates)} 筆數據, 最後日期: {dates[-1]}', flush=True)
        return True
        
    except Exception as e:
        print(f'❌ {name}: 更新失敗 - {e}', flush=True)
        return False

def sync_data_directories():
    """同步各數據目錄，確保 /app/data/stocks/ 擁有最新數據"""
    source_dirs = [
        '/app/data/nasdaq_stocks',
        '/app/data/sp500_stocks',
    ]
    target_dir = '/app/data/stocks'
    os.makedirs(target_dir, exist_ok=True)
    
    synced = 0
    for src_dir in source_dirs:
        if not os.path.isdir(src_dir):
            continue
        for src_file in glob.glob(os.path.join(src_dir, '*.json.gz')):
            filename = os.path.basename(src_file)
            dst_file = os.path.join(target_dir, filename)
            if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                shutil.copy2(src_file, dst_file)
                synced += 1
    
    print(f'✓ 數據目錄同步完成: {synced} 個檔案已更新', flush=True)
    return True


def _update_single_stock(file_path):
    """增量更新單支股票數據"""
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        
        symbol = data.get('symbol', os.path.basename(file_path).replace('.json.gz', ''))
        dates = data.get('dates', [])
        if not dates:
            return symbol, False, 'no dates'
        
        last_date = dates[-1]
        # 只更新距離最新數據超過 1 天的股票
        last_dt = datetime.strptime(last_date, '%Y-%m-%d')
        if (datetime.now() - last_dt).days <= 1:
            return symbol, True, 'already up-to-date'
        
        # 從最後日期的前一天開始下載（確保連續）
        start = (last_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start)
        
        if hist.empty:
            return symbol, False, 'no new data'
        
        new_dates = hist.index.strftime('%Y-%m-%d').tolist()
        new_close = hist['Close'].astype(float).tolist()
        
        # 合併：去重並追加新數據
        existing_set = set(dates)
        old_close = data.get('close', [])
        
        for i, d in enumerate(new_dates):
            if d not in existing_set:
                dates.append(d)
                old_close.append(new_close[i])
        
        # 排序
        paired = sorted(zip(dates, old_close))
        data['dates'] = [p[0] for p in paired]
        data['close'] = [p[1] for p in paired]
        data['end_date'] = data['dates'][-1]
        data['last_updated'] = datetime.now().isoformat()
        data['data_points'] = len(data['dates'])
        
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f)
        
        return symbol, True, data['dates'][-1]
    except Exception as e:
        err_msg = str(e)[:80]
        if 'RateLimit' in err_msg or 'Too Many' in err_msg:
            return os.path.basename(file_path), False, 'RATE_LIMITED'
        return os.path.basename(file_path), False, err_msg


def update_nasdaq_stocks():
    """增量更新 /app/data/nasdaq_stocks/ 中所有已有的股票數據（帶速率控制）"""
    nasdaq_dir = '/app/data/nasdaq_stocks'
    if not os.path.isdir(nasdaq_dir):
        print('⚠ nasdaq_stocks 目錄不存在，跳過', flush=True)
        return True
    
    files = glob.glob(os.path.join(nasdaq_dir, '*.json.gz'))
    # 排除指數文件
    files = [f for f in files if not os.path.basename(f).startswith('^')]
    total = len(files)
    
    if total == 0:
        print('⚠ 無 NASDAQ 股票數據需要更新', flush=True)
        return True
    
    print(f'開始增量更新 {total} 支 NASDAQ 股票...', flush=True)
    
    success = 0
    failed = 0
    skipped = 0
    rate_limited = False
    start_time = time.time()
    
    # 分批處理，每批 50 支，批次間暫停以避免速率限制
    batch_size = 50
    for batch_start in range(0, total, batch_size):
        if rate_limited:
            # 遇到速率限制，等待 30 秒後重試
            print(f'  ⚠ 偵測到速率限制，等待 30 秒...', flush=True)
            time.sleep(30)
            rate_limited = False
        
        batch_files = files[batch_start:batch_start + batch_size]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_update_single_stock, f): f for f in batch_files}
            for future in as_completed(futures):
                sym, ok, msg = future.result()
                if ok:
                    if 'up-to-date' in msg:
                        skipped += 1
                    else:
                        success += 1
                else:
                    if msg == 'RATE_LIMITED':
                        rate_limited = True
                    failed += 1
        
        done = success + failed + skipped
        if done % 200 == 0 or batch_start + batch_size >= total:
            elapsed = time.time() - start_time
            print(f'  進度: {done}/{total} (更新:{success} 跳過:{skipped} 失敗:{failed}) {elapsed:.0f}s', flush=True)
        
        # 批次間短暫暫停（2秒）避免觸發速率限制
        if batch_start + batch_size < total:
            time.sleep(2)
    
    elapsed = time.time() - start_time
    print(f'✓ NASDAQ 股票更新完成: 更新 {success}, 跳過 {skipped}, 失敗 {failed} (共 {elapsed:.0f}s)', flush=True)
    return True  # 不因個股失敗阻斷整體流程

def update_sp500_stocks():
    """更新 S&P 500 成分股數據"""
    try:
        print('\n' + '=' * 60, flush=True)
        print('開始更新 S&P 500 成分股數據...', flush=True)
        print('=' * 60, flush=True)
        
        # 執行 sp500_downloader.py（增量更新模式）
        result = subprocess.run(
            ['python', '/app/sp500_downloader.py', '--incremental'],
            capture_output=True,
            text=True,
            timeout=600  # 10分鐘超時
        )
        
        if result.returncode == 0:
            # 提取關鍵信息
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if '✓' in line or '成功' in line or '總計' in line or '成功率' in line:
                    print(line, flush=True)
            print('✓ S&P 500 成分股更新完成', flush=True)
            return True
        else:
            print(f'❌ S&P 500 成分股更新失敗', flush=True)
            if result.stderr:
                print(f'錯誤信息: {result.stderr[:200]}', flush=True)
            return False
            
    except subprocess.TimeoutExpired:
        print('❌ S&P 500 成分股更新超時（超過10分鐘）', flush=True)
        return False
    except Exception as e:
        print(f'❌ S&P 500 成分股更新失敗 - {e}', flush=True)
        return False

def main():
    """主函數"""
    print('=' * 60, flush=True)
    print('股票數據自動更新程序', flush=True)
    print(f'執行時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', flush=True)
    print('=' * 60, flush=True)
    
    all_success = True
    
    # 步驟 1: 更新三大指數
    print('\n【步驟 1/4】更新三大指數', flush=True)
    print('-' * 60, flush=True)
    
    indices = [
        ('^IXIC', 'NASDAQ Composite'),
        ('^DJI', 'Dow Jones Industrial Average'),
        ('^GSPC', 'S&P 500')
    ]
    
    success_count = 0
    for symbol, name in indices:
        if update_index(symbol, name):
            success_count += 1
    
    print('\n' + '-' * 60, flush=True)
    print(f'指數更新完成: {success_count}/{len(indices)} 個成功', flush=True)
    
    if success_count < len(indices):
        all_success = False
    
    # 步驟 2: 更新 S&P 500 成分股
    print('\n【步驟 2/4】更新 S&P 500 成分股', flush=True)
    print('-' * 60, flush=True)
    
    if not update_sp500_stocks():
        all_success = False
    
    # 步驟 3: 增量更新 NASDAQ 股票
    print('\n【步驟 3/4】增量更新 NASDAQ 股票', flush=True)
    print('-' * 60, flush=True)
    
    if not update_nasdaq_stocks():
        all_success = False
    
    # 步驟 4: 同步數據目錄
    print('\n【步驟 4/4】同步數據目錄', flush=True)
    print('-' * 60, flush=True)
    
    sync_data_directories()
    
    # 最終結果
    print('\n' + '=' * 60, flush=True)
    if all_success:
        print('✓ 所有數據更新成功！', flush=True)
    else:
        print('⚠ 部分數據更新失敗，請查看日誌', flush=True)
    print('=' * 60, flush=True)
    
    return 0 if all_success else 1

if __name__ == '__main__':
    sys.exit(main())
