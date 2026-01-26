#!/bin/bash

# 自動下載那斯達克股票歷史資料腳本
# 在專案啟動後自動執行，預先下載最新數據到緩存

echo "=================================================="
echo "自動下載那斯達克股票歷史資料"
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

# 計算日期範圍（最近2年）
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    START_DATE=$(date -v-2y +%Y-%m-%d)
    END_DATE=$(date +%Y-%m-%d)
else
    # Linux
    START_DATE=$(date -d '2 years ago' +%Y-%m-%d)
    END_DATE=$(date +%Y-%m-%d)
fi

echo ""
echo "開始下載股票資料..."
echo "日期範圍: $START_DATE 至 $END_DATE"
echo "預計耗時: 3-5 分鐘"
echo ""

# 執行下載
START_TIME=$(date +%s)

curl -X POST "http://localhost:8000/nasdaq/download-all" \
  -H "Content-Type: application/json" \
  -d "{\"start_date\": \"$START_DATE\", \"end_date\": \"$END_DATE\"}" \
  -o /tmp/download-result.json \
  --max-time 600 \
  -w "\n"

EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=================================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ 下載完成！耗時: ${DURATION}秒"
    echo ""
    
    # 解析結果
    if command -v jq &> /dev/null; then
        echo "下載統計："
        cat /tmp/download-result.json | jq -r '.summary | "總股票數: \(.total_tickers)\n成功下載: \(.successful_downloads)\n成功率: \(.success_rate)\n數據點總數: \(.total_data_points)"'
    else
        echo "結果："
        cat /tmp/download-result.json
    fi
    
    echo ""
    echo "✓ 系統已準備就緒，可以開始使用！"
    echo "  訪問: http://localhost"
else
    echo "✗ 下載失敗 (錯誤碼: $EXIT_CODE)"
    echo "  請查看日誌: docker-compose logs backend"
fi

echo "=================================================="

# 清理臨時文件
rm -f /tmp/download-result.json

exit $EXIT_CODE
