#!/usr/bin/env python3
"""計算所有股票與納斯達克綜合指數的相關性（2024-01-01 到 2026-01-26）"""

import gzip
import json
from pathlib import Path
import numpy as np
from datetime import datetime

def load_stock_data(file_path):
    """載入股票數據"""
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None

def filter_date_range(dates, close_prices, start_date, end_date):
    """過濾指定日期範圍的數據"""
    filtered_dates = []
    filtered_prices = []
    
    for date, price in zip(dates, close_prices):
        if start_date <= date <= end_date:
            filtered_dates.append(date)
            filtered_prices.append(price)
    
    return filtered_dates, filtered_prices

def calculate_correlation():
    data_dir = Path('/app/data/stocks')
    
    # 載入納斯達克指數數據
    nasdaq_file = data_dir / '^IXIC.json.gz'
    if not nasdaq_file.exists():
        print("❌ 找不到納斯達克指數數據")
        return
    
    nasdaq_data = load_stock_data(nasdaq_file)
    if not nasdaq_data:
        print("❌ 無法載入納斯達克指數數據")
        return
    
    # 過濾納斯達克數據到指定日期範圍
    nasdaq_dates, nasdaq_prices = filter_date_range(
        nasdaq_data['dates'],
        nasdaq_data.get('close') or nasdaq_data.get('close_prices'),
        '2024-01-01',
        '2026-01-26'
    )
    
    if len(nasdaq_dates) == 0:
        print("❌ 納斯達克數據沒有指定日期範圍的記錄")
        return
    
    print(f"納斯達克綜合指數 (^IXIC)")
    print(f"  日期範圍: {nasdaq_dates[0]} 到 {nasdaq_dates[-1]}")
    print(f"  記錄數: {len(nasdaq_dates)}")
    print(f"  價格範圍: {min(nasdaq_prices):.2f} - {max(nasdaq_prices):.2f}")
    print()
    
    # 計算所有股票的相關性
    correlations = []
    
    stock_files = sorted([f for f in data_dir.glob('*.json.gz') if f.name != '^IXIC.json.gz'])
    print(f"開始計算 {len(stock_files)} 個股票的相關性...\n")
    
    for i, stock_file in enumerate(stock_files, 1):
        symbol = stock_file.stem.replace('.json', '')
        
        # 每 100 個顯示進度
        if i % 100 == 0:
            print(f"已處理 {i}/{len(stock_files)} 個股票...")
        
        stock_data = load_stock_data(stock_file)
        if not stock_data:
            continue
        
        # 過濾股票數據到指定日期範圍
        stock_dates, stock_prices = filter_date_range(
            stock_data['dates'],
            stock_data.get('close') or stock_data.get('close_prices'),
            '2024-01-01',
            '2026-01-26'
        )
        
        if len(stock_dates) < 50:  # 至少需要 50 個數據點
            continue
        
        # 找出共同日期
        common_dates = set(nasdaq_dates) & set(stock_dates)
        if len(common_dates) < 50:
            continue
        
        # 對齊數據
        nasdaq_dict = dict(zip(nasdaq_dates, nasdaq_prices))
        stock_dict = dict(zip(stock_dates, stock_prices))
        
        aligned_nasdaq = []
        aligned_stock = []
        
        for date in sorted(common_dates):
            aligned_nasdaq.append(nasdaq_dict[date])
            aligned_stock.append(stock_dict[date])
        
        # 計算相關係數
        if len(aligned_nasdaq) >= 50:
            correlation = np.corrcoef(aligned_nasdaq, aligned_stock)[0, 1]
            
            correlations.append({
                'symbol': symbol,
                'correlation': correlation,
                'data_points': len(aligned_nasdaq),
                'date_range': f"{min(common_dates)} 到 {max(common_dates)}"
            })
    
    print(f"\n✓ 完成計算 {len(correlations)} 個股票的相關性\n")
    
    # 排序並顯示結果
    correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    print("=" * 80)
    print("與納斯達克綜合指數相關性分析結果 (2024-01-01 至 2026-01-26)")
    print("=" * 80)
    
    # 前 30 名最高正相關
    print("\n【前 30 名最高正相關】")
    print(f"{'排名':<6} {'股票代碼':<12} {'相關係數':<12} {'數據點數':<12}")
    print("-" * 80)
    positive_corr = [c for c in correlations if c['correlation'] > 0]
    for i, item in enumerate(positive_corr[:30], 1):
        print(f"{i:<6} {item['symbol']:<12} {item['correlation']:>10.4f}   {item['data_points']:>8} 點")
    
    # 統計摘要
    print("\n" + "=" * 80)
    print("統計摘要")
    print("=" * 80)
    
    all_corr_values = [c['correlation'] for c in correlations]
    print(f"總計分析股票數: {len(correlations)}")
    print(f"平均相關係數: {np.mean(all_corr_values):.4f}")
    print(f"中位數相關係數: {np.median(all_corr_values):.4f}")
    print(f"標準差: {np.std(all_corr_values):.4f}")
    print(f"最高相關係數: {max(all_corr_values):.4f} ({[c['symbol'] for c in correlations if c['correlation'] == max(all_corr_values)][0]})")
    print(f"最低相關係數: {min(all_corr_values):.4f} ({[c['symbol'] for c in correlations if c['correlation'] == min(all_corr_values)][0]})")
    
    # 分組統計
    high_corr = len([c for c in all_corr_values if c >= 0.8])
    medium_corr = len([c for c in all_corr_values if 0.5 <= c < 0.8])
    low_corr = len([c for c in all_corr_values if 0 <= c < 0.5])
    negative_corr = len([c for c in all_corr_values if c < 0])
    
    print(f"\n相關性分組:")
    print(f"  高度相關 (≥0.8):     {high_corr:>4} 個 ({high_corr/len(all_corr_values)*100:.1f}%)")
    print(f"  中度相關 (0.5-0.8):  {medium_corr:>4} 個 ({medium_corr/len(all_corr_values)*100:.1f}%)")
    print(f"  低度相關 (0-0.5):    {low_corr:>4} 個 ({low_corr/len(all_corr_values)*100:.1f}%)")
    print(f"  負相關 (<0):         {negative_corr:>4} 個 ({negative_corr/len(all_corr_values)*100:.1f}%)")
    
    # 保存完整結果到文件
    output_file = Path('/app/nasdaq_correlation_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(correlations, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ 完整結果已保存至 {output_file}")

if __name__ == '__main__':
    calculate_correlation()
