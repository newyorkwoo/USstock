# 道瓊工業指數功能已添加 ✅

## 更新內容

系統現已支持**道瓊工業指數（Dow Jones Industrial Average, ^DJI）**的相關性分析！

### 新增功能

✅ **30支道瓊成分股數據下載**

- 包含美國最大的30家上市公司
- 歷史數據範圍: 2010年1月1日 至 今天
- 獨立數據存儲，不影響NASDAQ數據

✅ **相關性分析**

- 計算每支成分股與道瓊指數的相關係數
- 支持自定義日期範圍和閾值
- 與NASDAQ分析功能完全一致

✅ **前端UI支持**

- 指數選擇下拉選單已包含「道瓊工業指數」
- K線圖自動顯示道瓊指數走勢
- 支持股票疊加顯示

## 快速開始

### 一鍵設置（推薦）

```bash
./setup_dow_jones.sh
```

### 手動設置

```bash
# 進入後端容器
docker exec -it usstock-backend bash

# 下載數據
python /app/download_dow_jones.py

# 退出容器
exit
```

### 使用方法

1. 打開瀏覽器: http://localhost
2. 選擇「道瓊工業指數」
3. 設置日期範圍和閾值
4. 點擊「分析」

## 技術細節

### 新增文件

- `backend/dow_jones_downloader.py` - 道瓊數據下載器
- `backend/download_dow_jones.py` - 手動下載腳本
- `DOW_JONES_GUIDE.md` - 完整使用指南
- `setup_dow_jones.sh` - 一鍵設置腳本

### 修改文件

- `backend/app_optimized.py`
  - 添加 `INDEX_DATA_DIRS` 映射
  - 修改相關性分析支持多目錄
  - 新增 `/dow-jones/download-all` API
  - 新增 `/dow-jones/download-status` API

- `backend/data_storage.py`
  - 修改 `get_stock_file_path()` 處理特殊字符

### 數據存儲

```
/app/data/
├── stocks/              # NASDAQ數據 (~3000支)
├── dow_jones_stocks/    # 道瓊數據 (30支) ← 新增
└── dow_jones_meta.json  # 下載元數據 ← 新增
```

## API 端點

### 下載道瓊數據

```
POST /dow-jones/download-all
```

### 查詢下載狀態

```
GET /dow-jones/download-status
```

### 相關性分析

```
POST /storage/correlation-analysis
Body: { "index_symbol": "^DJI", "threshold": 0.7 }
```

## 測試結果

✅ **下載測試**

- 成功下載: 29/30 支股票
- 耗時: ~5秒
- 數據點: 每支4040筆（2010-2026）

✅ **相關性分析測試**

- 分析股票: 29支
- 閾值: 0.7
- 結果: 19支高相關股票
- 最高相關性: AXP (0.968)

## 完整文檔

詳細使用指南請查看: [DOW_JONES_GUIDE.md](./DOW_JONES_GUIDE.md)

## 常見問題

**Q: 為什麼WBA沒有數據？**
A: Walgreens Boots Alliance可能已退市或代碼變更，Yahoo Finance無法找到該股票數據。

**Q: 如何更新數據？**
A: 重新運行下載腳本即可覆蓋更新。

**Q: 能否分析其他指數？**
A: 目前支持NASDAQ和道瓊，S&P 500計劃中。

---

**更新日期**: 2026-01-27
**版本**: 1.0.0
