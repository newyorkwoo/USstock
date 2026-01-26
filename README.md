# 美國股市分析系統

一個完整的美國股市分析專案，提供 NASDAQ、道瓊工業指數、S&P 500 三大指數的 K 線圖展示與成分股相關性分析。

## 技術架構

### 前端
- **框架**: Vite + Vue 3 (JavaScript)
- **樣式**: Tailwind CSS
- **圖表**: Chart.js + vue-chartjs
- **HTTP 客戶端**: Axios
- **特色**: 動態端口檢測（自動尋找可用端口 3000-3100）

### 後端
- **框架**: Flask (Python)
- **數據來源**: Yahoo Finance (yfinance)
- **數據分析**: pandas, numpy, scipy
- **跨域**: Flask-CORS

## 功能特點

### 1. 三大指數分類
- **NASDAQ** (^IXIC): 納斯達克綜合指數
- **道瓊工業指數** (^DJI): Dow Jones Industrial Average
- **S&P 500** (^GSPC): 標準普爾 500 指數

### 2. K 線圖展示
- 紅色 K 線：收盤價上漲
- 綠色 K 線：收盤價下跌
- 顯示開盤、收盤、最高、最低價格
- 顯示成交量信息

### 3. 相關性分析
- 計算各指數成分股與該指數的皮爾森相關係數
- 相關性評級：
  - 高度相關：|r| ≥ 0.8
  - 中度相關：|r| ≥ 0.5
  - 低度相關：|r| ≥ 0.3
  - 弱相關：|r| < 0.3

### 4. 歷史數據
- 從 Yahoo Finance 下載 **2010年1月1日至今** 的完整歷史數據
- 基於收盤價計算相關性
- 自動對齊交易日期
- 只使用共同交易日的數據點進行分析

## 安裝與啟動

### 後端啟動

```bash
cd backend

# 安裝依賴
pip install -r requirements.txt

# 或使用 pip3
pip3 install -r requirements.txt

# 啟動後端服務器 (Port 8000)
python app.py
# 或
python3 app.py
```

### 前端啟動

```bash
cd frontend

# 安裝依賴
npm install

# 啟動開發服務器（自動檢測可用端口）
npm run dev

# 構建生產版本
npm run build

# 預覽生產版本
npm run preview
```

## API 端點

### 獲取指數歷史數據
```
GET /api/index/<symbol>
```
參數：
- `symbol`: 指數代碼 (^IXIC, ^DJI, ^GSPC)

返回：
```json
{
  "symbol": "^IXIC",
  "name": "NASDAQ",
  "history": [
    {
      "date": "2024-01-01",
      "open": 15000.0,
      "high": 15100.0,
      "low": 14900.0,
      "close": 15050.0,
      "volume": 1000000000
    }
  ]
}
```

### 獲取相關性分析
```
GET /api/correlation/<symbol>
```
參數：
- `symbol`: 指數代碼 (^IXIC, ^DJI, ^GSPC)

返回：
```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "correlation": 0.85
  }
]
```

### 獲取所有指數
```
GET /api/indices
```

### 健康檢查
```
GET /health
```

## 目錄結構

```
USstock/
├── frontend/                 # 前端項目
│   ├── src/
│   │   ├── components/       # Vue 組件
│   │   │   ├── KLineChart.vue        # K線圖組件
│   │   │   └── CorrelationTable.vue  # 相關性表格組件
│   │   ├── utils/           # 工具函數
│   │   │   └── api.js       # API 調用
│   │   ├── App.vue          # 主應用組件
│   │   ├── main.js          # 入口文件
│   │   └── style.css        # 全局樣式
│   ├── public/              # 靜態資源
│   ├── index.html           # HTML 模板
│   ├── portDetector.js      # 動態端口檢測
│   ├── vite.config.js       # Vite 配置
│   ├── tailwind.config.js   # Tailwind 配置
│   ├── postcss.config.js    # PostCSS 配置
│   └── package.json         # 項目配置
│
├── backend/                  # 後端項目
│   ├── app.py               # Flask 應用
│   └── requirements.txt     # Python 依賴
│
└── README.md                # 本文件
```

## 使用流程

1. **啟動後端**：首先啟動 Python 後端服務器（Port 8000）
2. **啟動前端**：然後啟動 Vue 前端應用（自動檢測可用端口）
3. **訪問應用**：瀏覽器打開前端提示的 URL
4. **選擇指數**：點擊頂部標籤切換不同指數
5. **查看分析**：查看 K 線圖和相關性分析結果

## 注意事項

1. **網絡連接**：需要互聯網連接以從 Yahoo Finance 下載數據
2. **首次加載**：首次加載可能需要較長時間，因為需要下載大量歷史數據
3. **API 限制**：Yahoo Finance 可能有請求頻率限制，請適度使用
4. **端口占用**：
   - 後端固定使用 8000 端口
   - 前端自動檢測 3000-3100 範圍內的可用端口

## 開發建議

- 修改成分股列表：編輯 `backend/app.py` 中的 `INDICES` 配置
- 調整歷史數據時間範圍：修改 `download_stock_data` 函數中的 `start_date` 參數（默認 2010-01-01）
- 自定義圖表樣式：編輯 `frontend/src/components/KLineChart.vue`
- 修改相關性閾值：編輯 `frontend/src/components/CorrelationTable.vue`

## 技術支持

如有問題，請檢查：
1. Python 和 Node.js 版本是否符合要求
2. 所有依賴是否正確安裝
3. 端口 8000 是否被占用
4. 網絡連接是否正常

## License

MIT
