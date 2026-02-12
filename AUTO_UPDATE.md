# 自動更新功能說明

## 📅 自動更新機制

本系統已實現完整的股票數據自動更新功能，無需手動干預即可保持數據最新。

### ⚙️ 更新內容

系統會自動更新以下數據：

1. **三大指數** (3支)
   - NASDAQ Composite (^IXIC)
   - Dow Jones Industrial Average (^DJI)
   - S&P 500 (^GSPC)

2. **S&P 500 成分股** (503支)
   - 包含所有 S&P 500 指數成分股的歷史數據
   - 從 2010-01-01 至最新交易日

### ⏰ 更新時機

1. **容器啟動時** - 每次啟動容器會立即執行一次完整數據更新
2. **定時更新** - 每天自動執行兩次：
   - 早上 09:00 (台北時間) - 美股開盤前更新
   - 晚上 23:00 (台北時間) - 美股收盤後更新

### 🔧 相關文件

- `backend/update_indices.py` - 自動更新主腳本（指數+成分股）
- `backend/sp500_downloader.py` - S&P 500 成分股下載器
- `backend/crontab` - Cron 定時任務配置
- `backend/entrypoint.sh` - 容器啟動腳本
- `backend/Dockerfile` - 包含 Cron 服務配置

## 📊 使用方式

### 查看當前數據狀態

```bash
# 查看三大指數數據
docker exec usstock-backend python -c "
import json, gzip
for symbol in ['^IXIC', '^DJI', '^GSPC']:
    with gzip.open(f'/app/data/stocks/{symbol}.json.gz', 'rt') as f:
        data = json.load(f)
        print(f'{data[\"name\"]}: {data[\"end_date\"]} ({len(data[\"dates\"])} 筆)')
"

# 查看 S&P 500 成分股統計
docker exec usstock-backend cat /app/data/sp500_meta.json
```

### 查看更新日誌

```bash
docker exec usstock-backend cat /var/log/update_indices.log
```

### 手動觸發完整更新

如果需要立即更新所有數據（指數+成分股）：

```bash
docker exec usstock-backend python /app/update_indices.py
```

### 僅更新成分股

如果只需要更新 S&P 500 成分股：

```bash
docker exec usstock-backend python /app/sp500_downloader.py --incremental
```

### 查看 Cron 配置

```bash
docker exec usstock-backend crontab -l
```

### 查看 Cron 運行狀態

```bash
docker exec usstock-backend service cron status
```

## 🔍 故障排除

### 檢查更新是否正常執行

1. 查看容器日誌：

   ```bash
   docker-compose logs backend | grep "更新"
   ```

2. 查看更新日誌文件：

   ```bash
   docker exec usstock-backend tail -50 /var/log/update_indices.log
   ```

3. 驗證 Cron 服務：
   ```bash
   docker exec usstock-backend service cron status
   ```

### 如果自動更新失敗

1. 重啟容器：

   ```bash
   docker-compose restart backend
   ```

2. 手動執行更新：

   ```bash
   docker exec usstock-backend python /app/update_indices.py
   ```

3. 查看詳細錯誤信息：
   ```bash
   docker-compose logs backend --tail=100
   ```

## 📝 技術細節

### 更新流程

**階段一：更新三大指數**

1. 連接 Yahoo Finance API
2. 下載從 2010-01-01 至今的歷史數據
3. 處理並壓縮數據（使用 gzip）
4. 保存到 `/app/data/stocks/` 目錄
5. 記錄更新時間和狀態

**階段二：更新 S&P 500 成分股**

1. 從 Wikipedia 獲取最新成分股列表（503支）
2. 使用多線程並行下載股票數據（10個線程）
3. 每支股票下載完整歷史數據（2010-01-01至今）
4. 壓縮並保存到 `/app/data/sp500_stocks/` 目錄
5. 生成元數據文件 `/app/data/sp500_meta.json`

**更新時間估計**

- 三大指數：約 5-10 秒
- S&P 500 成分股：約 50-70 秒
- 總計：約 1-2 分鐘

### 數據存儲格式

**指數數據格式** (`/app/data/stocks/`)：

```json
{
  "symbol": "^IXIC",
  "name": "NASDAQ Composite",
  "dates": ["2010-01-04", "2010-01-05", ...],
  "close": [2308.42, 2317.17, ...],
  "start_date": "2010-01-01",
  "end_date": "2026-02-11",
  "download_time": "2026-02-12T11:13:15.123456"
}
```

**成分股數據格式** (`/app/data/sp500_stocks/`)：

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "dates": ["2010-01-04", "2010-01-05", ...],
  "close": [30.57, 30.95, ...],
  "start_date": "2010-01-04",
  "end_date": "2026-02-12",
  "download_time": "2026-02-12T11:20:45.123456"
}
```

**元數據格式** (`/app/data/sp500_meta.json`)：

```json
{
  "total_stocks": 503,
  "successful": 503,
  "failed": 0,
  "start_date": "2010-01-01",
  "end_date": "2026-02-12",
  "download_time": "2026-02-12T11:20:50.214992",
  "elapsed_time_seconds": 58.07,
  "stocks": [...]
}
```

### Cron 配置

```cron
# 每天台北時間 09:00 更新
0 9 * * * cd /app && /usr/local/bin/python /app/update_indices.py >> /var/log/update_indices.log 2>&1

# 每天台北時間 23:00 更新
0 23 * * * cd /app && /usr/local/bin/python /app/update_indices.py >> /var/log/update_indices.log 2>&1
```

## 🎯 優勢

1. **自動化** - 無需手動更新數據
2. **可靠性** - 雙重更新機制（啟動時 + 定時）
3. **監控** - 完整的日誌記錄
4. **彈性** - 支持手動觸發更新
5. **時區感知** - 使用台北時間（UTC+8）

## 🚀 未來改進

- [ ] 添加更新失敗通知
- [ ] 支持更多股票指數
- [ ] 增量更新優化（只更新缺失的日期）
- [ ] 數據備份機制
- [ ] 更新狀態儀表板
