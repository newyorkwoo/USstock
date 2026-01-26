# 快速啟動指南

## 1. 啟動後端（終端 1）

```bash
cd /Users/steven/Documents/myproject/USstock
./start-backend.sh
```

或者手動啟動：
```bash
cd backend
source venv/bin/activate
python app.py
```

等待看到：
```
==================================================
美國股市分析系統 - 後端 API
==================================================
支持的指數:
  - NASDAQ (^IXIC)
  - 道瓊工業指數 (^DJI)
  - S&P 500 (^GSPC)
==================================================
API 啟動於 http://localhost:8000
==================================================
```

## 2. 啟動前端（終端 2）

```bash
cd /Users/steven/Documents/myproject/USstock
./start-frontend.sh
```

或者手動啟動：
```bash
cd frontend
npm run dev
```

前端會自動檢測可用端口（3000-3100），並顯示：
```
✓ 找到可用端口: 3000
✓ Vite 配置已更新，使用端口: 3000

  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
```

## 3. 訪問應用

打開瀏覽器訪問前端顯示的地址（通常是 http://localhost:3000）

## 功能說明

### 切換指數
- 點擊頂部的 "NASDAQ"、"道瓊工業指數" 或 "S&P 500" 標籤
- 系統會自動載入該指數的歷史數據和相關性分析

### K線圖
- **紅色柱**：當日收盤價高於開盤價（上漲）
- **綠色柱**：當日收盤價低於開盤價（下跌）
- **灰色線**：最高價和最低價趨勢線
- 滑鼠懸停可查看詳細信息（開盤、收盤、最高、最低、成交量）

### 相關性分析表格
- 顯示該指數成分股與指數的皮爾森相關係數
- 相關性評級：
  - **高度相關**（紅色標籤）：|r| ≥ 0.8
  - **中度相關**（黃色標籤）：|r| ≥ 0.5
  - **低度相關**（藍色標籤）：|r| ≥ 0.3
  - **弱相關**（灰色標籤）：|r| < 0.3

### 統計信息
- **當前價格**：最新收盤價
- **漲跌幅**：相對前一交易日的漲跌百分比
  - 紅色：上漲
  - 綠色：下跌
- **成交量**：當日成交量（單位：百萬）

## 故障排除

### 後端問題

**端口 8000 被占用**
```bash
# 查找占用進程
lsof -i :8000
# 終止進程
kill -9 <PID>
```

**依賴安裝失敗**
```bash
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**無法獲取 Yahoo Finance 數據**
- 檢查網絡連接
- Yahoo Finance 可能有請求限制，稍後重試
- 確認股票代碼正確

### 前端問題

**找不到可用端口**
- 檢查 3000-3100 端口範圍是否都被占用
- 修改 `frontend/portDetector.js` 中的端口範圍

**無法連接後端**
- 確認後端服務器正在運行（http://localhost:8000/health）
- 檢查防火牆設置
- 確認 CORS 設置正確

**依賴安裝失敗**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 停止服務

在各自的終端中按 `Ctrl+C` 停止前端和後端服務器。

## 開發模式

### 修改後端代碼
後端使用 Flask 的 debug 模式，修改代碼後會自動重載。

### 修改前端代碼
前端使用 Vite 熱更新，修改代碼後瀏覽器會自動刷新。

## 數據說明

- 歷史數據範圍：**2010年1月1日至今**（完整14+年數據）
- 數據來源：Yahoo Finance (yfinance)
- 更新頻率：每次切換指數時重新獲取
- 緩存：無（每次都從 Yahoo Finance 實時獲取）
- 相關性計算：基於收盤價，使用皮爾森相關係數
- 數據對齊：自動對齊交易日期，只使用兩者共同的交易日

## 性能優化建議

1. **首次加載**：首次加載需要下載大量數據，請耐心等待
2. **網絡優化**：建議在良好的網絡環境下使用
3. **瀏覽器**：推薦使用 Chrome 或 Edge 瀏覽器

## 技術棧

- **前端**：Vue 3 + Vite + Tailwind CSS + Chart.js
- **後端**：Flask + yfinance + pandas + scipy
- **數據源**：Yahoo Finance
