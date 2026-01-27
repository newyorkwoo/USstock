#!/usr/bin/env python3
"""批量修復損壞的 gzip 文件"""

import gzip
import json
from pathlib import Path
import subprocess
import sys

def fix_corrupted_files():
    data_dir = Path('/app/data/stocks')
    files = sorted(data_dir.glob('*.json.gz'))
    
    corrupted_files = []
    
    print("=== 檢測損壞的文件 ===\n")
    
    # 第一步：找出所有損壞的文件
    for file in files:
        try:
            with gzip.open(file, 'rt', encoding='utf-8') as f:
                json.load(f)
        except Exception as e:
            corrupted_files.append(file)
    
    print(f"發現 {len(corrupted_files)} 個損壞的文件\n")
    
    if not corrupted_files:
        print("✓ 沒有損壞的文件")
        return
    
    # 第二步：嘗試修復每個文件
    fixed_count = 0
    failed_count = 0
    
    print("=== 開始修復 ===\n")
    
    for file in corrupted_files:
        symbol = file.stem.replace('.json', '')
        
        try:
            # 嘗試用 gunzip 解壓（忽略錯誤）
            result = subprocess.run(
                ['gunzip', '-c', str(file)],
                capture_output=True,
                text=False,  # 使用 bytes
                timeout=10
            )
            
            if result.returncode == 0 or result.stdout:
                # 嘗試解析 JSON
                try:
                    data = json.loads(result.stdout.decode('utf-8'))
                    
                    # 重新壓縮
                    temp_file = file.with_suffix('.tmp.gz')
                    with gzip.open(temp_file, 'wt', encoding='utf-8') as f:
                        json.dump(data, f)
                    
                    # 驗證新文件
                    with gzip.open(temp_file, 'rt', encoding='utf-8') as f:
                        json.load(f)
                    
                    # 備份原文件
                    backup_file = file.with_suffix('.backup.gz')
                    file.rename(backup_file)
                    
                    # 替換為修復的文件
                    temp_file.rename(file)
                    
                    fixed_count += 1
                    print(f"✓ {symbol}: 已修復")
                    
                except Exception as e:
                    failed_count += 1
                    print(f"✗ {symbol}: JSON 解析失敗 - {e}")
            else:
                failed_count += 1
                print(f"✗ {symbol}: 無法解壓")
                
        except subprocess.TimeoutExpired:
            failed_count += 1
            print(f"✗ {symbol}: 超時")
        except Exception as e:
            failed_count += 1
            print(f"✗ {symbol}: {e}")
    
    print(f"\n{'=' * 60}")
    print(f"=== 修復完成 ===")
    print(f"   成功: {fixed_count} 個")
    print(f"   失敗: {failed_count} 個")
    print(f"   總計: {len(corrupted_files)} 個")
    
    # 如果有失敗的，列出需要重新下載的股票代碼
    if failed_count > 0:
        print(f"\n{'=' * 60}")
        print("=== 需要重新下載的股票 ===")
        
        for file in corrupted_files:
            try:
                with gzip.open(file, 'rt', encoding='utf-8') as f:
                    json.load(f)
            except:
                symbol = file.stem.replace('.json', '')
                print(f"   {symbol}")

if __name__ == '__main__':
    fix_corrupted_files()
