# 美國股市分析系統

一個完整的美國股市分析專案，提供 NASDAQ、道瓊工業指數、S&P 500 三大指數的 K 線圖展示與成分股相關性分析。

## 🚀 快速開始

### 一鍵啟動（推薦）

```bash
# 自動更新三大指數及所屬股票的歷史數據後啟動系統
./startup.sh
```

此腳本會自動執行以下操作：

1. 啟動 Docker 服務（Redis、後端、前端）
2. 更新 NASDAQ 指數數據
3. 更新道瓊工業指數數據
4. 更新 S&P 500 指數及 503 支成分股數據
5. 清除 Redis 緩存並重啟後端服務

**系統時區**: UTC+8 (Asia/Taipei)

### 手動啟動

```bash
# 啟動所有服務
docker-compose up -d

# 訪問應用
open http://localhost
```

## 📊 功能特點

### 1. 三大指數分析

- **NASDAQ** (^IXIC): 納斯達克綜合指數
- **道瓊工業指數** (^DJI): Dow Jones Industrial Average
- **S&P 500** (^GSPC): 標準普爾 500 指數

### 2. K 線圖展示

- 完整的 OHLC（開盤、最高、最低、收盤）數據可視化
- 歷史數據範圍：2010-01-01 至今
- 自定義日期範圍篩選（2010/01/01 - 今天）
- 自動標註 15% 以上跌幅區域

### 3. 相關性分析

- 計算成分股與指數的皮爾森相關係數
- 可調整相關性閥值（預設 0.9）
- 顯示高度相關的股票列表

### 4. 性能優化

- ⚡ Redis 緩存系統
- 🚀 Gunicorn 多進程處理
- 🔄 並行數據下載
- 📦 Gzip 壓縮傳輸

## 🛠️ 技術架構

### 前端

- **框架**: Vue 3 + Vite
- **UI**: Tailwind CSS
- **圖表**: Chart.js
- **部署**: Nginx

### 後端

- **框架**: Flask + Gunicorn
- **數據源**: Yahoo Finance (yfinance)
- **分析**: pandas, numpy, scipy
- **緩存**: Redis

### 基礎設施

- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **時區**: Asia/Taipei (UTC+8)

## 📂 專案結構

```
USstock/
├── frontend/              # Vue 3 前端應用
│   ├── src/
│   │   ├── components/   # Vue 組件
│   │   ├── utils/        # API 工具
│   │   └── views/        # 頁面視圖
│   └── nginx.conf        # Nginx 配置
├── backend/              # Flask 後端應用
│   ├── app_optimized.py  # 主應用程式
│   ├── data_storage.py   # 數據存儲模組
│   ├── sp500_downloader.py  # S&P 500 下載器
│   └── gunicorn_config.py   # Gunicorn 配置
├── docker-compose.yml    # Docker Compose 配置
├── startup.sh            # 一鍵啟動腳本
└── README.md
```

## 🔧 環境需求

- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM（推薦）
- 10GB+ 磁碟空間

## 📝 使用說明

### 日期篩選

- 開始日期：2010/01/01（最早）
- 結束日期：今天（最晚）
- 修改日期後會自動重新載入數據

### 相關性分析

- 選擇指數後點擊「分析」按鈕
- 調整相關性閥值（0.0 - 1.0）
- 查看符合條件的高度相關股票

### 數據更新

系統啟動時會自動更新所有數據，也可以手動重新執行：

```bash
./startup.sh
```

## 🚀 訪問地址

- 前端應用: http://localhost
- 後端 API: http://localhost:8000
- Redis: localhost:6379

## 📄 授權

MIT License

## 👨‍💻 作者

Steven - 美國股市分析系統
