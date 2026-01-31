#!/bin/bash

# 美國股市分析系統啟動腳本
# 時區: UTC+8 (Asia/Taipei)
# 功能: 自動更新三大指數及所屬股票的歷史數據後啟動服務

set -e

echo "============================================================"
echo "美國股市分析系統啟動中..."
echo "時區: UTC+8 (Asia/Taipei)"
echo "當前時間: $(TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================"
echo ""

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未運行，請先啟動 Docker"
    exit 1
fi

# 啟動 Docker Compose 服務
echo "步驟 1: 啟動 Docker 服務..."
docker-compose up -d

# 等待後端服務健康檢查通過
echo ""
echo "步驟 2: 等待後端服務啟動..."
for i in {1..30}; do
    if docker exec usstock-backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ 後端服務已就緒"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 後端服務啟動超時"
        exit 1
    fi
    sleep 1
done

# 更新 NASDAQ 指數數據
echo ""
echo "步驟 3: 更新 NASDAQ 指數數據..."
docker exec usstock-backend python -c "
import yfinance as yf
import json
import gzip
from datetime import datetime
import pytz

tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tz)

ticker = yf.Ticker('^IXIC')
hist = ticker.history(start='2010-01-01', end=now.strftime('%Y-%m-%d'))

dates = hist.index.strftime('%Y-%m-%d').tolist()
close_prices = hist['Close'].tolist()

data = {
    'symbol': '^IXIC',
    'name': 'NASDAQ Composite',
    'dates': dates,
    'close': close_prices,
    'start_date': dates[0],
    'end_date': dates[-1],
    'download_time': now.isoformat()
}

with gzip.open('/app/data/stocks/^IXIC.json.gz', 'wt') as f:
    json.dump(data, f)

print(f'✓ NASDAQ: {dates[0]} ~ {dates[-1]} ({len(dates)} 筆)')
"

# 更新道瓊工業指數數據
echo ""
echo "步驟 4: 更新道瓊工業指數數據..."
docker exec usstock-backend python -c "
import yfinance as yf
import json
import gzip
from datetime import datetime
import pytz

tz = pytz.timezone('Asia/Taipei')
now = datetime.now(tz)

ticker = yf.Ticker('^DJI')
hist = ticker.history(start='2010-01-01', end=now.strftime('%Y-%m-%d'))

dates = hist.index.strftime('%Y-%m-%d').tolist()
close_prices = hist['Close'].tolist()

data = {
    'symbol': '^DJI',
    'name': 'Dow Jones Industrial Average',
    'dates': dates,
    'close': close_prices,
    'start_date': dates[0],
    'end_date': dates[-1],
    'download_time': now.isoformat()
}

with gzip.open('/app/data/stocks/DJI.json.gz', 'wt') as f:
    json.dump(data, f)

print(f'✓ 道瓊工業指數: {dates[0]} ~ {dates[-1]} ({len(dates)} 筆)')
"

# 更新 S&P 500 指數及成分股數據
echo ""
echo "步驟 5: 更新 S&P 500 指數及成分股數據..."
docker exec usstock-backend python sp500_downloader.py --incremental 2>&1 | grep -E "✓|成功|總計|數據範圍" || true

# 清除 Redis 緩存
echo ""
echo "步驟 6: 清除緩存..."
docker exec usstock-redis redis-cli FLUSHALL > /dev/null
echo "✓ 緩存已清除"

# 重啟後端以確保使用最新數據
echo ""
echo "步驟 7: 重啟後端服務..."
docker-compose restart backend > /dev/null
sleep 3

# 等待後端重新啟動
for i in {1..10}; do
    if docker exec usstock-backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ 後端服務已重啟"
        break
    fi
    sleep 1
done

echo ""
echo "============================================================"
echo "✓ 系統啟動完成！"
echo ""
echo "訪問地址: http://localhost"
echo "後端 API: http://localhost:8000"
echo ""
echo "數據已更新到: $(TZ=Asia/Taipei date '+%Y-%m-%d')"
echo "============================================================"
