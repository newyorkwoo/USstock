#!/bin/bash

# 監控本地存儲下載進度

echo "===================================================="
echo "本地存儲下載進度監控"
echo "===================================================="
echo ""

while true; do
    clear
    echo "===================================================="
    echo "本地存儲下載進度監控 - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "===================================================="
    echo ""
    
    # 檢查後端健康狀態
    if ! curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
        echo "❌ 後端服務未就緒"
        sleep 5
        continue
    fi
    
    echo "✓ 後端服務正常運行"
    echo ""
    
    # 查看已下載的文件數
    FILE_COUNT=$(docker exec usstock-backend sh -c "ls -1 /app/data/stocks 2>/dev/null | wc -l" 2>/dev/null | tr -d ' ')
    echo "已下載文件數: $FILE_COUNT"
    
    # 查看數據目錄大小
    DIR_SIZE=$(docker exec usstock-backend sh -c "du -sh /app/data/stocks 2>/dev/null | cut -f1" 2>/dev/null)
    echo "數據目錄大小: ${DIR_SIZE:-0}"
    
    echo ""
    echo "===================================================="
    echo "最近日誌 (按 Ctrl+C 停止監控):"
    echo "===================================================="
    docker logs usstock-backend 2>&1 | grep -E "(下載|成功|失敗|完成|進度)" | tail -10
    
    sleep 10
done
