#!/bin/bash

# 本地數據存儲初始化腳本
# 將2010-01-01至今的所有那斯達克股票歷史資料存放在本地

echo "=================================================="
echo "本地數據存儲初始化"
echo "=================================================="

# 等待服務啟動
echo "等待後端服務啟動..."
sleep 15

# 檢查後端是否就緒
max_retries=10
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ 後端服務已就緒"
        break
    fi
    retry_count=$((retry_count + 1))
    echo "等待後端服務... ($retry_count/$max_retries)"
    sleep 3
done

if [ $retry_count -eq $max_retries ]; then
    echo "✗ 後端服務啟動失敗"
    exit 1
fi

echo ""
echo "=================================================="
echo "開始下載所有股票歷史資料到本地存儲"
echo "=================================================="
echo "日期範圍: 2010-01-01 至今"
echo "預計耗時: 30-60分鐘（首次）"
echo ""
echo "此過程會將所有數據持久化保存到本地："
echo "  • Docker卷: usstock-stock-data"
echo "  • 容器路徑: /app/data"
echo "  • 數據格式: gzip壓縮的JSON"
echo ""
echo "完成後，未來啟動只需增量更新最新數據（約1-2分鐘）"
echo "=================================================="
echo ""

START_TIME=$(date +%s)

# 執行完整下載
curl -X POST "http://localhost:8000/storage/download-all-to-local" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2010-01-01"}' \
  -o /tmp/local-download-result.json \
  --max-time 7200 \
  -w "\n"

EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "=================================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ 下載完成！耗時: ${MINUTES}分${SECONDS}秒"
    echo ""
    
    # 解析結果
    if command -v jq &> /dev/null; then
        echo "下載統計："
        cat /tmp/local-download-result.json | jq -r '.summary | "總股票數: \(.total)\n成功下載: \(.success)\n成功率: \(.success_rate)\n總數據點: \(.total_data_points)\n日期範圍: \(.date_range.start) 至 \(.date_range.end)"'
    else
        echo "結果："
        cat /tmp/local-download-result.json
    fi
    
    echo ""
    echo "=================================================="
    echo "本地數據存儲已建立！"
    echo "=================================================="
    echo ""
    echo "數據已永久保存，即使容器重啟數據也不會丟失"
    echo ""
    echo "未來啟動時使用增量更新腳本："
    echo "  ./update-local-data.sh"
    echo ""
    echo "這將只下載最新的交易日數據（通常1-2分鐘）"
    echo "=================================================="
else
    echo "✗ 下載失敗 (錯誤碼: $EXIT_CODE)"
    echo "  請查看日誌: docker-compose logs backend"
fi

echo "=================================================="

# 清理臨時文件
rm -f /tmp/local-download-result.json

exit $EXIT_CODE
