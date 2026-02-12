#!/bin/bash

# 美國股市分析系統啟動腳本
# 時區: UTC+8 (Asia/Taipei)
# 功能: 啟動服務並自動更新數據（通過容器內的自動更新機制）

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
echo "（容器啟動時將自動執行數據更新）"
docker-compose up -d

# 等待後端服務健康檢查通過
echo ""
echo "步驟 2: 等待後端服務啟動及數據更新..."
echo "（首次啟動可能需要較長時間進行數據更新）"
for i in {1..60}; do
    if docker exec usstock-backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ 後端服務已就緒"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ 後端服務啟動超時"
        echo "您可以通過以下命令查看日誌："
        echo "  docker-compose logs backend"
        exit 1
    fi
    # 每10秒顯示一次進度
    if [ $((i % 10)) -eq 0 ]; then
        echo "  等待中... ($i/60)"
    fi
    sleep 1
done

# 檢查數據更新狀態
echo ""
echo "步驟 3: 檢查數據狀態..."
docker exec usstock-backend python -c "
import json, gzip, os
from datetime import datetime

indices = ['^IXIC', '^DJI', '^GSPC']
names = ['NASDAQ', '道瓊工業指數', 'S&P 500']

print('當前數據狀態:')
for symbol, name in zip(indices, names):
    file_path = f'/app/data/stocks/{symbol}.json.gz'
    if os.path.exists(file_path):
        with gzip.open(file_path, 'rt') as f:
            data = json.load(f)
            print(f'  ✓ {name}: {data[\"end_date\"]} ({len(data[\"dates\"])} 筆)')
    else:
        print(f'  ⚠ {name}: 數據文件不存在')
" || echo "  ⚠ 無法檢查數據狀態"

# 顯示 Cron 定時任務配置
echo ""
echo "步驟 4: 檢查定時更新配置..."
docker exec usstock-backend crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "  ⚠ Cron 配置可能未正確加載"

echo ""
echo "============================================================"
echo "✓ 系統啟動完成！"
echo ""
echo "訪問地址: http://localhost"
echo "後端 API: http://localhost:8000"
echo ""
echo "自動更新時間:"
echo "  • 每天早上 09:00 (台北時間) - 美股開盤前"
echo "  • 每天晚上 23:00 (台北時間) - 美股收盤後"
echo ""
echo "查看更新日誌:"
echo "  docker exec usstock-backend cat /var/log/update_indices.log"
echo ""
echo "手動觸發更新:"
echo "  docker exec usstock-backend python /app/update_indices.py"
echo "============================================================"
