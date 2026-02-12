#!/usr/bin/env python3
"""
快速更新腳本 — 使用 Yahoo Finance v8 直接 API
繞過 yfinance 函式庫的速率限制，直接更新所有過期的股票數據
"""
import urllib.request
import json
import time
import gzip
import os
import sys
from datetime import datetime, timedelta

def fetch_yahoo_direct(symbol, start_date):
    """Fetch stock data directly from Yahoo Finance API (bypasses yfinance rate limit)"""
    period1 = int(time.mktime(time.strptime(start_date, '%Y-%m-%d')))
    period2 = int(time.time())
    
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}&period2={period2}&interval=1d'
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    
    result = data['chart']['result'][0]
    timestamps = result.get('timestamp', [])
    if not timestamps:
        return [], []
    closes = result['indicators']['quote'][0]['close']
    
    dates = []
    prices = []
    for ts, c in zip(timestamps, closes):
        if c is not None:
            dates.append(time.strftime('%Y-%m-%d', time.localtime(ts)))
            prices.append(round(float(c), 6))
    
    return dates, prices

def update_stock_file(file_path, new_dates, new_closes):
    """Merge new data into existing stock file"""
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    
    existing_set = set(data.get('dates', []))
    dates = data.get('dates', [])
    closes = data.get('close', [])
    
    added = 0
    for d, c in zip(new_dates, new_closes):
        if d not in existing_set:
            dates.append(d)
            closes.append(c)
            added += 1
    
    # Sort
    paired = sorted(zip(dates, closes))
    data['dates'] = [p[0] for p in paired]
    data['close'] = [p[1] for p in paired]
    data['end_date'] = data['dates'][-1]
    data['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    data['data_points'] = len(data['dates'])
    
    with gzip.open(file_path, 'wt', encoding='utf-8') as f:
        json.dump(data, f)
    
    return added

def main():
    # Determine dynamic start date: 5 days ago
    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Update all stocks in nasdaq_stocks and sp500_stocks that are behind
    data_dirs = ['/app/data/nasdaq_stocks', '/app/data/sp500_stocks', '/app/data/stocks']
    
    # Find all unique symbols that need updating
    symbols_to_update = set()
    for data_dir in data_dirs:
        if not os.path.isdir(data_dir):
            continue
        for fname in os.listdir(data_dir):
            if not fname.endswith('.json.gz') or fname.startswith('^'):
                continue
            fpath = os.path.join(data_dir, fname)
            try:
                with gzip.open(fpath, 'rt') as f:
                    d = json.load(f)
                dates = d.get('dates', [])
                if dates:
                    last_dt = datetime.strptime(dates[-1], '%Y-%m-%d')
                    if (datetime.now() - last_dt).days > 1:
                        symbols_to_update.add(fname.replace('.json.gz', ''))
            except:
                pass
    
    print(f'Found {len(symbols_to_update)} stocks needing update (start_date={start_date})')
    
    success = 0
    failed = 0
    
    for i, symbol in enumerate(sorted(symbols_to_update)):
        try:
            new_dates, new_closes = fetch_yahoo_direct(symbol, start_date)
            
            if not new_dates:
                failed += 1
                continue
            
            # Update all dirs that have this stock
            for data_dir in data_dirs:
                fpath = os.path.join(data_dir, f'{symbol}.json.gz')
                if os.path.exists(fpath):
                    update_stock_file(fpath, new_dates, new_closes)
            
            success += 1
            
            if (success + failed) % 50 == 0:
                print(f'  Progress: {success + failed}/{len(symbols_to_update)} (ok:{success} fail:{failed})')
            
            # Rate limit: 0.1s per request
            time.sleep(0.1)
            
        except Exception as e:
            failed += 1
            err = str(e)[:60]
            if 'Too Many' in err or '429' in err:
                print(f'  Rate limited at {symbol}, waiting 60s...')
                time.sleep(60)
    
    print(f'\nDone: {success} updated, {failed} failed out of {len(symbols_to_update)}')

if __name__ == '__main__':
    main()
