#!/usr/bin/env python3
"""重新下載損壞的股票資料"""

import sys
import os
sys.path.insert(0, '/app')

from data_storage import download_and_save_stock

# 需要重新下載的股票代碼
corrupted_symbols = [
    'CVGW', 'DAKT', 'DHIL', 'DMLP', 'NVDA_new',
    'NWS', 'OAKUU', 'OCFC', 'ORRF', 'OVLY',
    'PFBC', 'QVCGA', 'RUSHA', 'SHEN'
]

print(f"=== 重新下載 {len(corrupted_symbols)} 個損壞的股票資料 ===\n")

success_count = 0
failed_count = 0

for symbol in corrupted_symbols:
    try:
        print(f"下載 {symbol}...", end=' ')
        download_and_save_stock(symbol, '2010-01-01', '2026-01-27')
        print("✓")
        success_count += 1
    except Exception as e:
        print(f"✗ {e}")
        failed_count += 1

print(f"\n{'=' * 60}")
print(f"=== 下載完成 ===")
print(f"   成功: {success_count} 個")
print(f"   失敗: {failed_count} 個")
