# 道瓊工業指數相關性分析使用指南

## 概述

本系統現已支持道瓊工業指數（Dow Jones Industrial Average, ^DJI）的相關性分析，與NASDAQ分析功能完全相同。

## 功能特點

- **30支成分股**: 道瓊工業指數包含30支美國最大的上市公司股票
- **歷史數據**: 從2010年1月1日至今的完整數據
- **相關性分析**: 計算每支成分股與指數的相關係數
- **獨立存儲**: 道瓊數據與NASDAQ數據分開存儲

## 道瓊工業指數30支成分股

```
AAPL  - Apple Inc.
MSFT  - Microsoft Corporation
UNH   - UnitedHealth Group
GS    - Goldman Sachs Group
HD    - Home Depot
MCD   - McDonald's Corporation
CAT   - Caterpillar Inc.
V     - Visa Inc.
AMGN  - Amgen Inc.
BA    - Boeing Company
TRV   - Travelers Companies
AXP   - American Express
JPM   - JPMorgan Chase & Co.
IBM   - IBM
HON   - Honeywell International
AMZN  - Amazon.com
CVX   - Chevron Corporation
JNJ   - Johnson & Johnson
PG    - Procter & Gamble
WMT   - Walmart
CRM   - Salesforce
DIS   - Walt Disney Company
NKE   - Nike
MRK   - Merck & Co.
KO    - Coca-Cola Company
CSCO  - Cisco Systems
VZ    - Verizon Communications
INTC  - Intel Corporation
WBA   - Walgreens Boots Alliance
DOW   - Dow Inc.
```

## 使用步驟

### 方法一：使用 Docker 容器（推薦）

1. **進入後端容器**
   ```bash
   docker exec -it usstock-backend-1 bash
   ```

2. **執行下載腳本**
   ```bash
   cd /app
   python download_dow_jones.py
   ```

3. **等待下載完成**
   - 下載30支股票，從2010年至今
   - 預計耗時：1-3分鐘（取決於網絡速度）

4. **驗證下載結果**
   ```bash
   ls -lh /app/data/dow_jones_stocks/
   # 應該看到30個 .json.gz 文件
   
   cat /app/data/dow_jones_meta.json
   # 查看下載統計信息
   ```

### 方法二：使用 API 端點

在前端或使用 curl 調用：

```bash
# 下載道瓊工業指數成分股數據
curl -X POST http://localhost:8000/dow-jones/download-all \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2010-01-01",
    "end_date": null,
    "max_workers": 5
  }'

# 查看下載狀態
curl http://localhost:8000/dow-jones/download-status
```

### 方法三：在容器外手動執行

1. **進入 backend 目錄**
   ```bash
   cd backend
   ```

2. **創建 Python 虛擬環境（如果還沒有）**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或 venv\Scripts\activate  # Windows
   ```

3. **安裝依賴**
   ```bash
   pip install -r requirements.txt
   ```

4. **執行下載**
   ```bash
   python download_dow_jones.py
   ```

## 數據存儲結構

```
/app/data/
├── stocks/                      # NASDAQ股票數據目錄
│   ├── AAPL.json.gz
│   ├── MSFT.json.gz
│   └── ...
├── dow_jones_stocks/            # 道瓊成分股數據目錄（新增）
│   ├── AAPL.json.gz
│   ├── GS.json.gz
│   ├── JPM.json.gz
│   └── ...
├── DJI.json.gz                  # 道瓊指數數據
└── dow_jones_meta.json          # 下載元數據
```

## 前端使用

下載完成後，在前端界面：

1. **選擇指數**: 在下拉選單中選擇「道瓊工業指數」
2. **設置日期範圍**: 
   - 開始日期：最早2010-01-01
   - 結束日期：最晚到昨天
3. **設置相關性閾值**: 例如 0.7 或 0.8
4. **點擊「分析」按鈕**: 系統會自動使用道瓊數據目錄進行分析
5. **查看結果**: 
   - K線圖顯示道瓊指數走勢
   - 相關性表格顯示與指數高度相關的成分股
   - 點擊任意股票可在K線圖上疊加顯示

## API 端點

### 1. 下載道瓊成分股數據
```
POST /dow-jones/download-all
Content-Type: application/json

{
  "start_date": "2010-01-01",  // 可選，默認2010-01-01
  "end_date": null,             // 可選，默認今天
  "max_workers": 5              // 可選，並行線程數
}
```

### 2. 查詢下載狀態
```
GET /dow-jones/download-status
```

### 3. 相關性分析（使用已有端點）
```
POST /storage/correlation-analysis
Content-Type: application/json

{
  "index_symbol": "^DJI",      // 指定道瓊指數
  "threshold": 0.7,             // 相關性閾值
  "start_date": "2020-01-01",
  "end_date": "2024-12-31"
}
```

## 系統架構說明

### 指數數據目錄映射

系統會根據選擇的指數自動使用對應的數據目錄：

```python
INDEX_DATA_DIRS = {
    '^IXIC': '/app/data/stocks',          # NASDAQ
    '^DJI': '/app/data/dow_jones_stocks', # 道瓊
    '^GSPC': '/app/data/stocks'           # S&P 500
}
```

### 數據過濾

相關性分析時會自動過濾：
- 指數本身（^DJI 不會出現在結果中）
- 重複數據（如 NVDA_fixed）

## 故障排除

### 問題1: 提示「本地數據目錄不存在」

**原因**: 尚未下載道瓊數據

**解決方案**: 執行下載腳本
```bash
docker exec -it usstock-backend-1 python /app/download_dow_jones.py
```

### 問題2: 下載失敗或超時

**原因**: 網絡連接問題或 Yahoo Finance API 限流

**解決方案**: 
1. 檢查網絡連接
2. 等待幾分鐘後重試
3. 減少並行線程數：`max_workers=2`

### 問題3: 相關性結果為空

**原因**: 
- 數據尚未下載
- 相關性閾值設置過高
- 日期範圍沒有共同交易日

**解決方案**:
1. 確認數據已下載：`curl http://localhost:8000/dow-jones/download-status`
2. 降低閾值（例如從0.9降到0.7）
3. 擴大日期範圍

### 問題4: 某些股票數據缺失

**原因**: 個別股票可能在 Yahoo Finance 上暫時無法訪問

**解決方案**: 重新運行下載腳本，系統會自動重試失敗的股票

## 性能優化

- **並行下載**: 默認5個線程同時下載，可根據網絡情況調整
- **數據壓縮**: 使用 gzip 壓縮，節省80%存儲空間
- **增量更新**: 後續只需更新新數據，不需重新下載全部歷史

## 數據更新

### 定期更新建議

建議每天或每週執行一次增量更新：

```bash
# 進入容器
docker exec -it usstock-backend-1 bash

# 執行更新（將來可以添加增量更新功能）
python download_dow_jones.py
```

## 注意事項

1. **數據來源**: 所有數據來自 Yahoo Finance，免費但有速率限制
2. **交易日**: 只包含實際交易日的數據，跳過週末和節假日
3. **數據延遲**: 當日數據可能有15-20分鐘延遲
4. **存儲空間**: 30支股票從2010年至今約需30-50MB（壓縮後）
5. **下載時間**: 首次下載約2-3分鐘，取決於網絡速度

## 與 NASDAQ 功能對比

| 功能 | NASDAQ | 道瓊工業指數 |
|-----|--------|------------|
| 股票數量 | ~3000支 | 30支成分股 |
| 數據目錄 | `/app/data/stocks` | `/app/data/dow_jones_stocks` |
| 下載時間 | 30-60分鐘 | 2-3分鐘 |
| 存儲空間 | 2-3GB | 30-50MB |
| 相關性分析 | ✓ | ✓ |
| K線圖顯示 | ✓ | ✓ |
| 股票疊加 | ✓ | ✓ |

## 後續開發計劃

- [ ] 增量更新功能
- [ ] 定時自動更新
- [ ] S&P 500 支持
- [ ] 數據導出功能
- [ ] 歷史相關性趨勢分析

## 技術支持

如有問題，請查看：
1. 系統日誌：`docker logs usstock-backend-1`
2. 數據目錄：`docker exec usstock-backend-1 ls -lh /app/data/`
3. 後端控制台輸出

---

**最後更新**: 2026年1月27日
**版本**: 1.0.0
