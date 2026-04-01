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

# 啟動 cron 服務
echo "啟動 Cron 定時任務..."
cron

# 顯示 cron 配置
echo "Cron 定時配置:"
crontab -l

# 先啟動 Gunicorn（背景執行），讓 API 立即可用
echo "啟動 Gunicorn 服務..."
gunicorn --config gunicorn_config.py app_optimized:app &
GUNICORN_PID=$!

# 等待 Gunicorn 啟動完成
echo "等待 API 服務就緒..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ API 服務已就緒"
    break
  fi
  sleep 1
done

# 在背景執行數據更新，不阻塞 API 服務
echo "在背景更新美國三大股市所有個股歷史數據..."
(python /app/update_indices.py --force && echo "✓ 數據更新完成" || echo "✗ 初始更新失敗，將在下次 cron 執行時重試") &

# 等待 Gunicorn 主進程
wait $GUNICORN_PID
