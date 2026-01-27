#!/usr/bin/env python3
"""檢查所有股票資料的完整性和格式一致性"""

import gzip
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def check_data_integrity():
    data_dir = Path('/app/data/stocks')
    if not data_dir.exists():
        print("❌ 資料目錄不存在")
        return
    
    files = sorted(data_dir.glob('*.json.gz'))
    print(f"總共 {len(files)} 個股票文件\n")
    
    # 統計資料
    structures = defaultdict(list)
    corrupted_files = []
    date_ranges = []
    record_counts = defaultdict(int)
    
    print("=== 檢查所有文件 ===")
    for i, file in enumerate(files, 1):
        symbol = file.stem.replace('.json', '')
        
        try:
            with gzip.open(file, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            # 記錄結構
            keys = tuple(sorted(data.keys()))
            structures[keys].append(symbol)
            
            # 檢查必要欄位
            if 'close' in data:
                record_count = len(data['close'])
                record_counts[record_count] += 1
                
                if 'start_date' in data and 'end_date' in data:
                    date_ranges.append({
                        'symbol': symbol,
                        'start': data['start_date'],
                        'end': data['end_date'],
                        'records': record_count
                    })
            
            # 每處理 100 個顯示進度
            if i % 100 == 0:
                print(f"已檢查 {i}/{len(files)} 個文件...")
                
        except Exception as e:
            corrupted_files.append({
                'symbol': symbol,
                'error': str(e)
            })
            print(f"❌ {symbol}: {e}")
    
    print(f"\n✓ 完成檢查 {len(files)} 個文件\n")
    
    # 顯示結果
    print("=" * 60)
    print("=== 資料結構分析 ===")
    for i, (keys, symbols) in enumerate(structures.items(), 1):
        print(f"\n結構類型 {i} ({len(symbols)} 個文件):")
        print(f"   欄位: {list(keys)}")
        print(f"   範例: {', '.join(symbols[:5])}")
    
    if corrupted_files:
        print(f"\n\n{'=' * 60}")
        print(f"=== ❌ 損壞的文件 ({len(corrupted_files)} 個) ===")
        for item in corrupted_files:
            print(f"   {item['symbol']}: {item['error']}")
    else:
        print(f"\n\n✓ 沒有損壞的文件")
    
    print(f"\n\n{'=' * 60}")
    print("=== 資料記錄數分布 ===")
    sorted_counts = sorted(record_counts.items(), key=lambda x: x[1], reverse=True)
    for count, num_files in sorted_counts[:10]:
        print(f"   {count} 筆記錄: {num_files} 個文件")
    
    if date_ranges:
        print(f"\n\n{'=' * 60}")
        print("=== 日期範圍統計 ===")
        
        # 找出最早和最晚的日期
        earliest = min(date_ranges, key=lambda x: x['start'])
        latest = max(date_ranges, key=lambda x: x['end'])
        
        print(f"   最早開始日期: {earliest['start']} ({earliest['symbol']})")
        print(f"   最晚結束日期: {latest['end']} ({latest['symbol']})")
        
        # 找出記錄最少和最多的
        min_records = min(date_ranges, key=lambda x: x['records'])
        max_records = max(date_ranges, key=lambda x: x['records'])
        
        print(f"\n   最少記錄: {min_records['records']} 筆 ({min_records['symbol']})")
        print(f"   最多記錄: {max_records['records']} 筆 ({max_records['symbol']})")
        
        # 檢查資料是否最新
        print(f"\n   資料更新檢查:")
        today = datetime.now().strftime('%Y-%m-%d')
        outdated = [x for x in date_ranges if x['end'] < '2026-01-20']
        
        if outdated:
            print(f"   ⚠️  {len(outdated)} 個文件資料可能過舊")
            print(f"   範例: {', '.join([x['symbol'] for x in outdated[:5]])}")
        else:
            print(f"   ✓ 所有文件資料都是最新的")

if __name__ == '__main__':
    check_data_integrity()
