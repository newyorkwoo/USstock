#!/usr/bin/env python3
"""
手動執行道瓊工業指數成分股數據下載
可在 Docker 容器外或容器內執行
"""
import sys
import os

# 添加 backend 目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dow_jones_downloader

if __name__ == '__main__':
    print("\n" + "="*60)
    print("手動下載道瓊工業指數成分股數據")
    print("="*60)
    
    # 執行下載
    result = dow_jones_downloader.bulk_download_dow_jones(
        start_date='2010-01-01',
        end_date=None,  # 默認到今天
        max_workers=5   # 5個並行線程
    )
    
    print("\n" + "="*60)
    if result['successful'] > 0:
        print("✓ 下載完成！")
        print(f"  成功: {result['successful']}/{result['total_stocks']} 支股票")
        print(f"  耗時: {result['elapsed_time_seconds']} 秒")
    else:
        print("✗ 下載失敗，請檢查網絡連接")
    print("="*60 + "\n")
