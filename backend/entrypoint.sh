#!/bin/bash
# 容器啟動腳本 - 同時啟動 Gunicorn 和 Cron

set -e

echo "==============================================="
echo "容器啟動中..."
echo "當前時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "==============================================="

# 創建日誌目錄
mkdir -p /var/log
touch /var/log/update_indices.log
chmod 666 /var/log/update_indices.log

# 啟動時執行一次數據更新
echo "執行初始數據更新..."
python /app/update_indices.py || echo "初始更新失敗，將在下次 cron 執行時重試"

# 啟動 cron 服務
echo "啟動 Cron 定時任務..."
cron

# 顯示 cron 配置
echo "Cron 定時配置:"
crontab -l

# 啟動 Gunicorn
echo "啟動 Gunicorn 服務..."
exec gunicorn --config gunicorn_config.py app_optimized:app
