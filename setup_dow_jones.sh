#!/bin/bash

echo "============================================================"
echo "道瓊工業指數 - 快速啟動指南"
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
echo "開始下載道瓊工業指數成分股數據"
echo "============================================================"
echo ""
echo "這將下載30支道瓊工業指數成分股從2010年至今的歷史數據"
echo "預計耗時: 2-3分鐘"
echo ""
read -p "是否繼續? (Y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "正在下載數據..."
docker exec usstock-backend python /app/download_dow_jones.py

echo ""
echo "============================================================"
echo "驗證下載結果"
echo "============================================================"
echo ""

# 檢查數據文件
file_count=$(docker exec usstock-backend ls /app/data/dow_jones_stocks/ 2>/dev/null | grep -c "\.json\.gz$")

if [ $file_count -gt 0 ]; then
    echo "✓ 成功下載 $file_count 支股票數據"
    echo ""
    
    # 顯示元數據
    echo "下載統計:"
    docker exec usstock-backend cat /app/data/dow_jones_meta.json 2>/dev/null | \
        python3 -c "import sys, json; meta=json.load(sys.stdin); print(f\"  總計: {meta['total_stocks']} 支\"); print(f\"  成功: {meta['successful']} 支\"); print(f\"  失敗: {meta['failed']} 支\"); print(f\"  耗時: {meta['elapsed_time_seconds']} 秒\")"
    
    echo ""
    echo "============================================================"
    echo "✓ 道瓊工業指數數據已準備就緒！"
    echo "============================================================"
    echo ""
    echo "後續步驟:"
    echo "  1. 打開瀏覽器訪問: http://localhost"
    echo "  2. 在指數選擇下拉選單中選擇「道瓊工業指數」"
    echo "  3. 設置日期範圍（開始: 2010-01-01，結束: 昨天）"
    echo "  4. 設置相關性閾值（建議: 0.7 或 0.8）"
    echo "  5. 點擊「分析」按鈕"
    echo "  6. 查看K線圖和相關性結果"
    echo "  7. 點擊任意股票可在K線圖上疊加顯示"
    echo ""
    echo "更多信息請查看: DOW_JONES_GUIDE.md"
    echo "============================================================"
else
    echo "❌ 數據下載失敗或不完整"
    echo ""
    echo "故障排除:"
    echo "  1. 檢查網絡連接"
    echo "  2. 查看容器日誌: docker logs usstock-backend"
    echo "  3. 手動重試: docker exec usstock-backend python /app/download_dow_jones.py"
    echo "  4. 查看詳細指南: DOW_JONES_GUIDE.md"
    exit 1
fi
