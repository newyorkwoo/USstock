#!/bin/bash

echo "============================================================"
echo "S&P 500 - 快速啟動指南"
echo "============================================================"
echo ""

# 檢查 Docker 是否運行
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker 未運行，請先啟動 Docker"
    exit 1
fi

echo "✓ Docker 正在運行"
echo ""

# 檢查容器是否運行
if ! docker ps | grep -q usstock-backend; then
    echo "啟動 Docker 容器..."
    cd "$(dirname "$0")"
    docker-compose up -d
    echo "✓ 容器已啟動"
    sleep 3
else
    echo "✓ 容器已在運行"
fi

echo ""
echo "============================================================"
echo "開始下載 S&P 500 成分股數據"
echo "============================================================"
echo ""
echo "⚠️  重要提示:"
echo "  - S&P 500 包含約500支成分股"
echo "  - 預計下載時間: 10-20分鐘"
echo "  - 數據量約: 20-30MB (壓縮後)"
echo ""
read -p "是否繼續下載? (Y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "正在下載數據（請耐心等待）..."
echo "提示: 可以打開另一個終端運行以下命令查看進度:"
echo "  docker logs -f usstock-backend"
echo ""

# 開始計時
START_TIME=$(date +%s)

docker exec usstock-backend python /app/download_sp500.py

# 計算耗時
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "============================================================"
echo "驗證下載結果"
echo "============================================================"
echo ""

# 檢查數據文件
file_count=$(docker exec usstock-backend ls /app/data/sp500_stocks/ 2>/dev/null | grep -c "\.json\.gz$")

if [ $file_count -gt 0 ]; then
    echo "✓ 成功下載 $file_count 支股票數據"
    echo "✓ 總耗時: ${MINUTES}分${SECONDS}秒"
    echo ""
    
    # 顯示元數據
    echo "下載統計:"
    docker exec usstock-backend cat /app/data/sp500_meta.json 2>/dev/null | \
        python3 -c "import sys, json; meta=json.load(sys.stdin); print(f\"  總計: {meta['total_stocks']} 支\"); print(f\"  成功: {meta['successful']} 支\"); print(f\"  失敗: {meta['failed']} 支\"); print(f\"  成功率: {meta['successful']/meta['total_stocks']*100:.1f}%\"); print(f\"  下載耗時: {meta['elapsed_time_seconds']:.1f} 秒\")" 2>/dev/null || echo "  (元數據讀取失敗)"
    
    echo ""
    echo "============================================================"
    echo "✓ S&P 500 數據已準備就緒！"
    echo "============================================================"
    echo ""
    echo "後續步驟:"
    echo "  1. 打開瀏覽器訪問: http://localhost"
    echo "  2. 在指數選擇下拉選單中選擇「S&P 500」"
    echo "  3. 設置日期範圍（開始: 2010-01-01，結束: 昨天）"
    echo "  4. 設置相關性閾值（建議: 0.7 或 0.8）"
    echo "  5. 點擊「分析」按鈕"
    echo "  6. 查看K線圖和相關性結果"
    echo "  7. 點擊任意股票可在K線圖上疊加顯示"
    echo ""
    echo "數據存儲位置: /app/data/sp500_stocks/"
    echo "============================================================"
else
    echo "❌ 數據下載失敗或不完整"
    echo ""
    echo "故障排除:"
    echo "  1. 檢查網絡連接"
    echo "  2. 查看容器日誌: docker logs usstock-backend"
    echo "  3. 手動重試: docker exec usstock-backend python /app/download_sp500.py"
    echo "  4. 檢查是否被 Yahoo Finance API 限流（需要等待後重試）"
    exit 1
fi
