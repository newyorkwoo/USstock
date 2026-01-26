#!/bin/bash

# 增量更新本地存儲的股票數據
# 只下載最後日期之後的新數據

echo "=================================================="
echo "增量更新本地股票數據"
echo "=================================================="

# 等待服務啟動（如果剛啟動）
sleep 5

# 檢查後端是否就緒
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "等待後端服務啟動..."
    sleep 10
    
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✗ 後端服務未就緒"
        exit 1
    fi
fi

echo "✓ 後端服務已就緒"
echo ""

# 檢查本地存儲狀態
echo "檢查本地存儲狀態..."
STATS=$(curl -s "http://localhost:8000/storage/stats")

if command -v jq &> /dev/null; then
    TOTAL_STOCKS=$(echo $STATS | jq -r '.stats.total_stocks')
    LAST_UPDATE=$(echo $STATS | jq -r '.stats.last_update')
    
    if [ "$TOTAL_STOCKS" == "null" ] || [ "$TOTAL_STOCKS" == "0" ]; then
        echo ""
        echo "⚠️  本地存儲尚未初始化"
        echo ""
        echo "請先運行初始化腳本："
        echo "  ./init-local-storage.sh"
        echo ""
        exit 1
    fi
    
    echo "  已存儲: $TOTAL_STOCKS 支股票"
    echo "  上次更新: $LAST_UPDATE"
else
    echo $STATS
fi

echo ""
echo "開始增量更新..."
echo "只下載自上次更新以來的新數據"
echo "預計耗時: 1-3 分鐘"
echo ""

START_TIME=$(date +%s)

# 執行增量更新
curl -X POST "http://localhost:8000/storage/update-incremental" \
  -H "Content-Type: application/json" \
  -d '{}' \
  -o /tmp/update-result.json \
  --max-time 600 \
  -w "\n"

EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=================================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ 更新完成！耗時: ${DURATION}秒"
    echo ""
    
    # 解析結果
    if command -v jq &> /dev/null; then
        echo "更新統計："
        cat /tmp/update-result.json | jq -r '.summary | "總股票數: \(.total)\n已更新: \(.updated)\n已跳過: \(.skipped) (已是最新)\n失敗: \(.failed)\n新增數據點: \(.new_data_points)"'
    else
        echo "結果："
        cat /tmp/update-result.json
    fi
    
    echo ""
    echo "✓ 本地數據已更新至最新！"
else
    echo "✗ 更新失敗 (錯誤碼: $EXIT_CODE)"
    echo "  請查看日誌: docker-compose logs backend"
fi

echo "=================================================="

# 清理臨時文件
rm -f /tmp/update-result.json

exit $EXIT_CODE
