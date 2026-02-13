#!/usr/bin/env python3
"""
美國三大股市股票數據自動更新腳本

每次啟動時從 Yahoo Finance 強制更新（--force）：
1. 三大指數（NASDAQ, DJI, S&P 500）
2. S&P 500 所有成分股
3. DJI 道璩 30 成分股
4. NASDAQ 所有個股
5. 其他孤兒股票
6. 同步所有數據目錄

用法:
  python update_indices.py --force    # 啟動時強制更新所有股票
  python update_indices.py            # 定時任務增量更新

支援 Yahoo Finance 直接 API 作為 yfinance 限速的後備方案
"""

import yfinance as yf
import json
import gzip
from datetime import datetime, timedelta
import sys
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import shutil
import time

# 數據存儲目錄
DATA_DIR = '/app/data/stocks'
NASDAQ_DIR = '/app/data/nasdaq_stocks'
SP500_DIR = '/app/data/sp500_stocks'
DJI_DIR = '/app/data/dji_stocks'
# 最新市場交易日（由步驟1更新指數後設定，作為個股更新的基準日期）
LATEST_MARKET_DATE = None
# 強制更新模式（啟動時使用 --force，跳過 up-to-date 檢查）
FORCE_UPDATE = False
# ============================================================
#  Yahoo Finance 直接 API（yfinance 限速後備方案）
# ============================================================

def fetch_yahoo_direct(symbol, start_date):
    """使用 Yahoo Finance v8 chart API 直接取得數據（繞過 yfinance 限速）"""
    period1 = int(time.mktime(time.strptime(start_date, '%Y-%m-%d')))
    period2 = int(time.time())

    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}&period2={period2}&interval=1d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    result = data['chart']['result'][0]
    timestamps = result.get('timestamp', [])
    if not timestamps:
        return [], []
    closes = result['indicators']['quote'][0]['close']

    dates, prices = [], []
    for ts, c in zip(timestamps, closes):
        if c is not None:
            dates.append(time.strftime('%Y-%m-%d', time.localtime(ts)))
            prices.append(round(float(c), 6))
    return dates, prices


# ============================================================
#  步驟 1: 更新三大指數
# ============================================================

def update_index(symbol, name):
    """更新單一指數數據（先嘗試 yfinance，失敗則使用直接 API）"""
    try:
        print(f'\n正在更新 {name} ({symbol})...', flush=True)

        dates, close_prices = None, None

        # 方法 1: yfinance
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start='2010-01-01')
            if not hist.empty:
                dates = hist.index.strftime('%Y-%m-%d').tolist()
                close_prices = hist['Close'].astype(float).tolist()
        except Exception as e:
            print(f'  yfinance 失敗 ({e}), 嘗試直接 API...', flush=True)

        # 方法 2: 直接 API（如果 yfinance 失敗）
        if not dates:
            try:
                dates, close_prices = fetch_yahoo_direct(symbol, '2010-01-01')
            except Exception as e2:
                print(f'  直接 API 也失敗: {e2}', flush=True)
                return False

        if not dates:
            print(f'❌ {name}: 無法獲取數據', flush=True)
            return False

        # 嘗試獲取名稱
        full_name = name
        try:
            info = yf.Ticker(symbol).info
            full_name = info.get('longName') or info.get('shortName') or name
        except:
            pass

        data = {
            'symbol': symbol,
            'name': full_name,
            'dates': dates,
            'close': close_prices,
            'start_date': '2010-01-01',
            'end_date': dates[-1],
            'download_time': datetime.now().isoformat()
        }

        file_path = os.path.join(DATA_DIR, f'{symbol}.json.gz')
        os.makedirs(DATA_DIR, exist_ok=True)
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f)

        print(f'✓ {name}: 成功更新 {len(dates)} 筆數據, 最後日期: {dates[-1]}', flush=True)
        return True

    except Exception as e:
        print(f'❌ {name}: 更新失敗 - {e}', flush=True)
        return False


# ============================================================
#  步驟 2 & 3: 增量更新個股
# ============================================================

def _update_single_stock(file_path, use_direct_api=False):
    """增量更新單支股票數據"""
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        symbol = data.get('symbol', os.path.basename(file_path).replace('.json.gz', ''))
        dates = data.get('dates', [])
        if not dates:
            return symbol, False, 'no dates'

        last_date = dates[-1]

        # 強制更新模式：跳過所有 up-to-date 檢查，強制嘗試拉取最新數據
        global FORCE_UPDATE, LATEST_MARKET_DATE
        if not FORCE_UPDATE:
            # 增量模式：使用指數基準日期判斷
            if LATEST_MARKET_DATE and last_date >= LATEST_MARKET_DATE:
                return symbol, True, 'already up-to-date'
            if not LATEST_MARKET_DATE:
                last_dt_check = datetime.strptime(last_date, '%Y-%m-%d')
                if (datetime.now() - last_dt_check).days <= 1:
                    return symbol, True, 'already up-to-date'

        last_dt = datetime.strptime(last_date, '%Y-%m-%d')

        # 從最後日期前一天開始（確保銜接）
        start = (last_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        new_dates, new_close = None, None

        if use_direct_api:
            # 直接使用 Yahoo v8 API
            try:
                new_dates, new_close = fetch_yahoo_direct(symbol, start)
            except:
                pass
        else:
            # 先嘗試 yfinance
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start)
                if not hist.empty:
                    new_dates = hist.index.strftime('%Y-%m-%d').tolist()
                    new_close = hist['Close'].astype(float).tolist()
            except Exception as e:
                err_msg = str(e)
                if 'Too Many' in err_msg or 'Rate' in err_msg:
                    return symbol, False, 'RATE_LIMITED'

            # yfinance 失敗 → 後備直接 API
            if not new_dates:
                try:
                    new_dates, new_close = fetch_yahoo_direct(symbol, start)
                except:
                    pass

        if not new_dates:
            return symbol, False, 'no new data'

        # 合併：去重並追加
        existing_set = set(dates)
        old_close = data.get('close', [])
        added = 0
        for i, d in enumerate(new_dates):
            if d not in existing_set:
                dates.append(d)
                old_close.append(new_close[i])
                added += 1

        if added == 0:
            return symbol, True, 'already up-to-date'

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


def _batch_update_stocks(data_dir, label, max_workers=5, batch_size=50):
    """批量增量更新指定目錄中的所有股票（帶速率控制 + 限速後備）"""
    if not os.path.isdir(data_dir):
        print(f'⚠ {data_dir} 目錄不存在，跳過', flush=True)
        return True

    files = [f for f in glob.glob(os.path.join(data_dir, '*.json.gz'))
             if not os.path.basename(f).startswith('^')]
    total = len(files)
    if total == 0:
        print(f'⚠ 無 {label} 股票數據需要更新', flush=True)
        return True

    print(f'開始增量更新 {total} 支 {label} 股票...', flush=True)

    success, failed, skipped = 0, 0, 0
    rate_limited_count = 0
    use_direct_api = False          # 連續限速後切換到直接 API
    start_time = time.time()

    for batch_start in range(0, total, batch_size):
        # 如果連續遇到限速，切換策略
        if rate_limited_count >= 3 and not use_direct_api:
            print(f'  ⚠ yfinance 持續限速，切換到 Yahoo 直接 API...', flush=True)
            use_direct_api = True

        batch_files = files[batch_start:batch_start + batch_size]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_update_single_stock, f, use_direct_api): f
                       for f in batch_files}
            for future in as_completed(futures):
                sym, ok, msg = future.result()
                if ok:
                    if 'up-to-date' in str(msg):
                        skipped += 1
                    else:
                        success += 1
                        rate_limited_count = 0   # 重置計數
                else:
                    if msg == 'RATE_LIMITED':
                        rate_limited_count += 1
                    failed += 1

        done = success + failed + skipped
        if done % 200 == 0 or batch_start + batch_size >= total:
            elapsed = time.time() - start_time
            mode = '直接API' if use_direct_api else 'yfinance'
            print(f'  進度: {done}/{total} (更新:{success} 跳過:{skipped} 失敗:{failed}) [{mode}] {elapsed:.0f}s', flush=True)

        # 批次間暫停
        if batch_start + batch_size < total:
            pause = 0.5 if use_direct_api else 2
            time.sleep(pause)

    elapsed = time.time() - start_time
    print(f'✓ {label} 股票更新完成: 更新 {success}, 跳過 {skipped}, 失敗 {failed} (共 {elapsed:.0f}s)', flush=True)
    return True


def update_sp500_stocks():
    """增量更新 S&P 500 成分股"""
    return _batch_update_stocks(SP500_DIR, 'S&P 500', max_workers=5, batch_size=50)


def update_nasdaq_stocks():
    """增量更新 NASDAQ 股票"""
    return _batch_update_stocks(NASDAQ_DIR, 'NASDAQ', max_workers=5, batch_size=50)


# ============================================================
#  DJI 道璩 30 成分股
# ============================================================

DJI_COMPONENTS = [
    'AAPL', 'AMGN', 'AMZN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO',
    'CVX', 'DIS', 'GS', 'HD', 'HON', 'IBM', 'JNJ', 'JPM',
    'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'NVDA', 'PG',
    'SHW', 'TRV', 'UNH', 'V', 'VZ', 'WMT'
]


def _download_new_stock(symbol, data_dir, start_date='2010-01-01'):
    """下載一支新股票的完整歷史數據（若本地已有則跳過）"""
    file_path = os.path.join(data_dir, f'{symbol}.json.gz')
    if os.path.exists(file_path):
        return symbol, True, 'exists'

    try:
        dates, close_prices = None, None
        # yfinance
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date)
            if not hist.empty:
                dates = hist.index.strftime('%Y-%m-%d').tolist()
                close_prices = hist['Close'].astype(float).tolist()
        except:
            pass
        # 後備 API
        if not dates:
            try:
                dates, close_prices = fetch_yahoo_direct(symbol, start_date)
            except:
                pass
        if not dates:
            return symbol, False, 'no data'

        name = symbol
        try:
            info = yf.Ticker(symbol).info
            name = info.get('longName') or info.get('shortName') or symbol
        except:
            pass

        data = {
            'symbol': symbol,
            'name': name,
            'dates': dates,
            'close': close_prices,
            'start_date': start_date,
            'end_date': dates[-1],
            'download_time': datetime.now().isoformat(),
            'data_points': len(dates)
        }
        os.makedirs(data_dir, exist_ok=True)
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f)
        return symbol, True, dates[-1]
    except Exception as e:
        return symbol, False, str(e)[:60]


def download_dji_components():
    """下載 / 更新 DJI 道璩 30 成分股"""
    os.makedirs(DJI_DIR, exist_ok=True)

    # 步驟 A: 下載本地尚未存在的成分股
    new_count = 0
    for sym in DJI_COMPONENTS:
        fp = os.path.join(DJI_DIR, f'{sym}.json.gz')
        if not os.path.exists(fp):
            sym_r, ok, msg = _download_new_stock(sym, DJI_DIR)
            if ok and msg != 'exists':
                new_count += 1
                print(f'  ✓ 新下載 {sym}: {msg}', flush=True)
            elif not ok:
                print(f'  ✗ {sym}: {msg}', flush=True)
    if new_count:
        print(f'  新下載 {new_count} 支 DJI 成分股', flush=True)

    # 步驟 B: 增量更新所有已有的 DJI 成分股
    return _batch_update_stocks(DJI_DIR, 'DJI 道璩成分股', max_workers=5, batch_size=30)


def update_orphan_stocks():
    """更新 stocks/ 目錄中不在 nasdaq_stocks/ 或 sp500_stocks/ 的孤兒股票"""
    if not os.path.isdir(DATA_DIR):
        print(f'⚠ {DATA_DIR} 目錄不存在，跳過', flush=True)
        return True

    nasdaq_files = set(os.path.basename(f) for f in glob.glob(os.path.join(NASDAQ_DIR, '*.json.gz')))
    sp500_files = set(os.path.basename(f) for f in glob.glob(os.path.join(SP500_DIR, '*.json.gz')))
    dji_files = set(os.path.basename(f) for f in glob.glob(os.path.join(DJI_DIR, '*.json.gz')))
    all_stocks_files = glob.glob(os.path.join(DATA_DIR, '*.json.gz'))

    # 找出只存在於 stocks/ 的孤兒檔案（排除指數和已被其他目錄管理的股票）
    orphan_files = [f for f in all_stocks_files
                    if os.path.basename(f) not in nasdaq_files
                    and os.path.basename(f) not in sp500_files
                    and os.path.basename(f) not in dji_files
                    and not os.path.basename(f).startswith('^')]

    if not orphan_files:
        print('⚠ 無孤兒股票需要更新', flush=True)
        return True

    print(f'找到 {len(orphan_files)} 支孤兒股票（僅存於 stocks/ 目錄）', flush=True)
    return _batch_update_stocks_files(orphan_files, '孤兒股票', max_workers=5, batch_size=50)


def _batch_update_stocks_files(files, label, max_workers=5, batch_size=50):
    """批量增量更新指定檔案列表中的所有股票（帶速率控制 + 限速後備）"""
    total = len(files)
    if total == 0:
        print(f'⚠ 無 {label} 股票數據需要更新', flush=True)
        return True

    print(f'開始增量更新 {total} 支 {label} 股票...', flush=True)

    success, failed, skipped = 0, 0, 0
    rate_limited_count = 0
    use_direct_api = False
    start_time = time.time()

    for batch_start in range(0, total, batch_size):
        if rate_limited_count >= 3 and not use_direct_api:
            print(f'  ⚠ yfinance 持續限速，切換到 Yahoo 直接 API...', flush=True)
            use_direct_api = True

        batch_files = files[batch_start:batch_start + batch_size]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_update_single_stock, f, use_direct_api): f
                       for f in batch_files}
            for future in as_completed(futures):
                sym, ok, msg = future.result()
                if ok:
                    if 'up-to-date' in str(msg):
                        skipped += 1
                    else:
                        success += 1
                        rate_limited_count = 0
                else:
                    if msg == 'RATE_LIMITED':
                        rate_limited_count += 1
                    failed += 1

        done = success + failed + skipped
        if done % 200 == 0 or batch_start + batch_size >= total:
            elapsed = time.time() - start_time
            mode = '直接API' if use_direct_api else 'yfinance'
            print(f'  進度: {done}/{total} (更新:{success} 跳過:{skipped} 失敗:{failed}) [{mode}] {elapsed:.0f}s', flush=True)

        if batch_start + batch_size < total:
            pause = 0.5 if use_direct_api else 2
            time.sleep(pause)

    elapsed = time.time() - start_time
    print(f'✓ {label} 股票更新完成: 更新 {success}, 跳過 {skipped}, 失敗 {failed} (共 {elapsed:.0f}s)', flush=True)
    return True


# ============================================================
#  步驟 6: 同步數據目錄
# ============================================================

def sync_data_directories():
    """同步各數據目錄，確保 /app/data/stocks/ 擁有最新數據"""
    source_dirs = [NASDAQ_DIR, SP500_DIR, DJI_DIR]
    os.makedirs(DATA_DIR, exist_ok=True)

    synced = 0
    for src_dir in source_dirs:
        if not os.path.isdir(src_dir):
            continue
        for src_file in glob.glob(os.path.join(src_dir, '*.json.gz')):
            filename = os.path.basename(src_file)
            dst_file = os.path.join(DATA_DIR, filename)
            if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                shutil.copy2(src_file, dst_file)
                synced += 1

    print(f'✓ 數據目錄同步完成: {synced} 個檔案已更新', flush=True)
    return True


# ============================================================
#  主程式
# ============================================================

def main():
    """主函數 — 依序執行 6 個更新步驟"""
    global FORCE_UPDATE

    # 解析命令列參數
    if '--force' in sys.argv:
        FORCE_UPDATE = True

    mode_str = '強制更新模式 (啟動時)' if FORCE_UPDATE else '增量更新模式 (定時任務)'
    print('=' * 60, flush=True)
    print(f'美國三大股市股票數據更新程序 【{mode_str}】', flush=True)
    print(f'執行時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', flush=True)
    print('=' * 60, flush=True)

    all_success = True

    # 步驟 1: 更新三大指數
    print('\n【步驟 1/6】更新三大指數', flush=True)
    print('-' * 60, flush=True)

    indices = [
        ('^IXIC', 'NASDAQ Composite'),
        ('^DJI', 'Dow Jones Industrial Average'),
        ('^GSPC', 'S&P 500')
    ]
    idx_ok = 0
    for symbol, name in indices:
        if update_index(symbol, name):
            idx_ok += 1
    print(f'\n指數更新完成: {idx_ok}/{len(indices)} 個成功', flush=True)
    if idx_ok < len(indices):
        all_success = False

    # 從已更新的指數數據中取得最新市場交易日作為基準
    global LATEST_MARKET_DATE
    for idx_symbol in ['^IXIC', '^GSPC', '^DJI']:
        idx_file = os.path.join(DATA_DIR, f'{idx_symbol}.json.gz')
        try:
            with gzip.open(idx_file, 'rt', encoding='utf-8') as f:
                idx_data = json.load(f)
            idx_dates = idx_data.get('dates', [])
            if idx_dates:
                if not LATEST_MARKET_DATE or idx_dates[-1] > LATEST_MARKET_DATE:
                    LATEST_MARKET_DATE = idx_dates[-1]
        except:
            pass
    if LATEST_MARKET_DATE:
        print(f'基準市場交易日: {LATEST_MARKET_DATE}', flush=True)
    else:
        print('⚠ 無法取得指數日期作為基準，將使用時間差判斷', flush=True)

    # 步驟 2: 更新 S&P 500 成分股
    print('\n【步驟 2/6】更新 S&P 500 所有成分股', flush=True)
    print('-' * 60, flush=True)
    if not update_sp500_stocks():
        all_success = False

    # 步驟 3: 更新 DJI 道璩 30 成分股
    print('\n【步驟 3/6】更新 DJI 道璩 30 成分股', flush=True)
    print('-' * 60, flush=True)
    if not download_dji_components():
        all_success = False

    # 步驟 4: 更新 NASDAQ 所有個股
    print('\n【步驟 4/6】更新 NASDAQ 所有個股', flush=True)
    print('-' * 60, flush=True)
    if not update_nasdaq_stocks():
        all_success = False

    # 步驟 5: 更新孤兒股票（僅存於 stocks/ 目錄）
    print('\n【步驟 5/6】更新 stocks/ 目錄中的其他股票', flush=True)
    print('-' * 60, flush=True)
    if not update_orphan_stocks():
        all_success = False

    # 步驟 6: 同步數據目錄
    print('\n【步驟 6/6】同步數據目錄', flush=True)
    print('-' * 60, flush=True)
    sync_data_directories()

    # 最終統計
    print('\n' + '=' * 60, flush=True)
    total_outdated = 0
    for d in [DATA_DIR, NASDAQ_DIR, SP500_DIR, DJI_DIR]:
        if os.path.isdir(d):
            for f in glob.glob(os.path.join(d, '*.json.gz')):
                if os.path.basename(f).startswith('^'):
                    continue
                try:
                    with gzip.open(f, 'rt', encoding='utf-8') as fh:
                        data = json.load(fh)
                    dates = data.get('dates', [])
                    if dates and dates[-1] < (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'):
                        total_outdated += 1
                except:
                    pass
    if total_outdated > 0:
        print(f'⚠ 仍有 {total_outdated} 支股票數據超過4天未更新（可能已下市或無交易）', flush=True)

    if all_success:
        print('✓ 所有數據更新成功！', flush=True)
    else:
        print('⚠ 部分數據更新失敗，請查看日誌', flush=True)
    print('=' * 60, flush=True)

    return 0 if all_success else 1


if __name__ == '__main__':
    sys.exit(main())
