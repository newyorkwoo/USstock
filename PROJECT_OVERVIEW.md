# 美國股市分析系統 - 專案總覽

## 📊 專案簡介

這是一個全功能的美國股市分析系統，專注於三大指數（NASDAQ、道瓊工業指數、S&P 500）的分析。
系統使用 Vue 3 + Vite 作為前端框架，Python Flask 作為後端 API，從 Yahoo Finance 獲取實時股市數據。

## ✨ 核心功能

### 1. 三大指數監控
- **NASDAQ** (^IXIC) - 納斯達克綜合指數
- **道瓊工業指數** (^DJI) - Dow Jones Industrial Average  
- **S&P 500** (^GSPC) - 標準普爾 500 指數

### 2. K線圖視覺化
- 紅色 K 線：收盤上漲
- 綠色 K 線：收盤下跌
- 顯示開盤、收盤、最高、最低價及成交量
- 互動式圖表，滑鼠懸停顯示詳細數據

### 3. 相關性分析
- 計算各指數成分股與該指數的皮爾森相關係數
- 自動分級（高度、中度、低度、弱相關）
- 按相關性強度排序顯示

### 4. 動態端口檢測
- 前端啟動時自動掃描 3000-3100 範圍內的可用端口
- 避免端口衝突問題

## 🏗️ 技術架構

```
┌─────────────────────────────────────────────┐
│           前端 (Port 3000+)                  │
│  Vue 3 + Vite + Tailwind CSS + Chart.js     │
│  - 動態端口檢測                              │
│  - 響應式 UI                                 │
│  - K線圖組件                                 │
│  - 相關性分析表格                            │
└─────────────────┬───────────────────────────┘
                  │ HTTP/REST API
                  │ (Axios)
┌─────────────────▼───────────────────────────┐
│           後端 (Port 8000)                   │
│          Python Flask + CORS                 │
│  - RESTful API                               │
│  - 數據處理 (pandas, numpy)                 │
│  - 相關性計算 (scipy)                       │
└─────────────────┬───────────────────────────┘
                  │
                  │ yfinance
                  │
┌─────────────────▼───────────────────────────┐
│            Yahoo Finance                     │
│  - 歷史股價數據                              │
│  - 實時行情                                  │
│  - 6個月歷史數據                             │
└─────────────────────────────────────────────┘
```

## 📁 專案結構

```
USstock/
├── frontend/                     # 前端專案
│   ├── src/
│   │   ├── components/          # Vue 組件
│   │   │   ├── KLineChart.vue          # K線圖表組件
│   │   │   └── CorrelationTable.vue    # 相關性表格組件
│   │   ├── utils/
│   │   │   └── api.js                  # API 請求封裝
│   │   ├── App.vue                     # 主應用組件
│   │   ├── main.js                     # Vue 入口
│   │   └── style.css                   # 全局樣式
│   ├── index.html
│   ├── portDetector.js          # 動態端口檢測
│   ├── vite.config.js           # Vite 配置
│   ├── tailwind.config.js       # Tailwind 配置
│   ├── postcss.config.js        # PostCSS 配置
│   └── package.json             # 前端依賴
│
├── backend/                      # 後端專案
│   ├── app.py                   # Flask 主應用
│   ├── requirements.txt         # Python 依賴
│   └── venv/                    # Python 虛擬環境
│
├── start-backend.sh             # 後端啟動腳本
├── start-frontend.sh            # 前端啟動腳本
├── README.md                    # 完整說明文檔
├── QUICKSTART.md                # 快速啟動指南
└── .gitignore                   # Git 忽略文件
```

## 🚀 快速開始

### 前置要求
- Node.js 18+
- Python 3.8+
- npm 或 yarn

### 1. 啟動後端
```bash
cd /Users/steven/Documents/myproject/USstock
./start-backend.sh
```

### 2. 啟動前端（新終端）
```bash
cd /Users/steven/Documents/myproject/USstock
./start-frontend.sh
```

### 3. 訪問應用
瀏覽器打開: http://localhost:3000 (或顯示的其他端口)

詳細說明請參考 [QUICKSTART.md](./QUICKSTART.md)

## 🔌 API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/index/<symbol>` | 獲取指數歷史數據 |
| GET | `/api/correlation/<symbol>` | 獲取相關性分析 |
| GET | `/api/indices` | 獲取所有支持的指數 |
| GET | `/health` | 健康檢查 |

### 示例請求

```bash
# 獲取 NASDAQ 歷史數據
curl http://localhost:8000/api/index/^IXIC

# 獲取 S&P 500 相關性分析
curl http://localhost:8000/api/correlation/^GSPC
```

## 📊 數據說明

### 歷史數據
- **時間範圍**: 近 6 個月
- **數據點**: 每日開盤、收盤、最高、最低、成交量
- **更新頻率**: 實時從 Yahoo Finance 獲取

### 相關性分析
- **計算方法**: 皮爾森相關係數 (Pearson Correlation)
- **範圍**: -1 到 1
  - 1: 完全正相關
  - 0: 無相關
  - -1: 完全負相關
- **評級標準**:
  - |r| ≥ 0.8: 高度相關
  - |r| ≥ 0.5: 中度相關
  - |r| ≥ 0.3: 低度相關
  - |r| < 0.3: 弱相關

## 🎨 UI 設計

### 配色方案
- **上漲紅色**: #ef4444 (bull-red)
- **下跌綠色**: #22c55e (bear-green)
- **主色調**: 藍色系
- **背景**: 淺灰色 (#f3f4f6)

### 響應式設計
- 支持桌面、平板、手機等多種設備
- Tailwind CSS 實現響應式布局

## 🛠️ 開發指南

### 修改成分股
編輯 `backend/app.py` 中的 `INDICES` 字典：

```python
INDICES = {
    '^IXIC': {
        'name': 'NASDAQ',
        'constituents': ['AAPL', 'MSFT', 'GOOGL', ...]
    }
}
```

### 調整歷史數據時間
修改 `backend/app.py` 中的 `download_stock_data` 函數：

```python
def download_stock_data(symbol, period='1y'):  # 改為 1 年
```

### 自定義端口範圍
修改 `frontend/portDetector.js`：

```javascript
const port = await findAvailablePort(5000, 5100);  // 5000-5100
```

## 📦 依賴清單

### 前端
- vue@^3.4.15
- vite@^5.0.11
- tailwindcss@^3.4.1
- axios@^1.6.5
- chart.js@^4.4.1
- vue-chartjs@^5.3.0

### 後端
- flask>=3.0.0
- flask-cors>=4.0.0
- yfinance>=0.2.35
- pandas>=2.2.0
- numpy>=1.26.0
- scipy>=1.12.0

## 🐛 問題排除

### 常見問題

1. **端口被占用**
   - 後端：修改 `app.py` 中的端口號
   - 前端：自動檢測會找到可用端口

2. **無法獲取數據**
   - 檢查網絡連接
   - Yahoo Finance 可能有頻率限制
   - 確認股票代碼正確

3. **圖表不顯示**
   - 檢查瀏覽器控制台錯誤
   - 確認後端 API 正常響應
   - 清除瀏覽器緩存

4. **依賴安裝失敗**
   - Python: 使用虛擬環境
   - Node.js: 刪除 node_modules 重新安裝

## 🔒 安全性

- 使用 CORS 控制跨域訪問
- 不存儲敏感數據
- 僅提供讀取功能，無寫入操作
- 建議在內網環境使用

## 📝 版本歷史

### v1.0.0 (2026-01-26)
- ✅ 初始版本發布
- ✅ 三大指數 K 線圖
- ✅ 相關性分析
- ✅ 動態端口檢測
- ✅ 響應式 UI
- ✅ Yahoo Finance 數據集成

## 📄 授權

MIT License

## 👥 貢獻

歡迎提交 Issue 和 Pull Request！

## 📮 聯繫方式

如有問題或建議，請通過以下方式聯繫：
- GitHub Issues
- Email: (待補充)

---

**Made with ❤️ for US Stock Market Analysis**
