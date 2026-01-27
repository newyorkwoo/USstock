#!/usr/bin/env python3
"""
手動執行 S&P 500 成分股數據下載
可在 Docker 容器外或容器內執行
"""
import sys
import os

# 添加 backend 目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sp500_downloader

if __name__ == '__main__':
    print("\n" + "="*60)
    print("手動下載 S&P 500 成分股數據")
    print("="*60)
    print("\n⚠️  注意: S&P 500 有約500支成分股")
    print("預計下載時間: 10-20分鐘（取決於網絡速度）")
    print("\n")
    
    # 執行下載
    result = sp500_downloader.bulk_download_sp500(
        start_date='2010-01-01',
        end_date=None,  # 默認到今天
        max_workers=10  # 10個並行線程
    )
    
    print("\n" + "="*60)
    if result and result['successful'] > 0:
        print("✓ 下載完成！")
        print(f"  成功: {result['successful']}/{result['total_stocks']} 支股票")
        print(f"  成功率: {result['successful']/result['total_stocks']*100:.1f}%")
        print(f"  耗時: {result['elapsed_time_seconds']} 秒")
    else:
        print("✗ 下載失敗，請檢查網絡連接")
    print("="*60 + "\n")
