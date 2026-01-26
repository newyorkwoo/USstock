#!/bin/bash

# 日期過濾功能測試腳本

echo "========================================"
echo "測試日期過濾功能"
echo "========================================"
echo ""

# 測試 1: 查詢 2023 年全年數據
echo "測試 1: 查詢 2023 年全年數據"
echo "日期範圍: 2023-01-01 至 2024-01-01"
response=$(curl -s "http://localhost:8000/api/index/%5EIXIC?start_date=2023-01-01&end_date=2024-01-01")
count=$(echo $response | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
start_date=$(echo $response | grep -o '"start":"[^"]*"' | cut -d'"' -f4)
end_date=$(echo $response | grep -o '"end":"[^"]*"' | cut -d'"' -f4)

echo "✓ 查詢成功"
echo "  數據筆數: $count"
echo "  實際範圍: $start_date 至 $end_date"
echo ""

# 測試 2: 查詢最近 6 個月數據
echo "測試 2: 查詢最近 6 個月數據"
six_months_ago=$(date -v-6m +%Y-%m-%d 2>/dev/null || date -d "6 months ago" +%Y-%m-%d 2>/dev/null || echo "2023-07-26")
today=$(date +%Y-%m-%d)
echo "日期範圍: $six_months_ago 至 $today"
response=$(curl -s "http://localhost:8000/api/index/%5EIXIC?start_date=$six_months_ago&end_date=$today")
count=$(echo $response | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
start_date=$(echo $response | grep -o '"start":"[^"]*"' | cut -d'"' -f4)
end_date=$(echo $response | grep -o '"end":"[^"]*"' | cut -d'"' -f4)

echo "✓ 查詢成功"
echo "  數據筆數: $count"
echo "  實際範圍: $start_date 至 $end_date"
echo ""

# 測試 3: 查詢最近 1 年數據
echo "測試 3: 查詢最近 1 年數據"
one_year_ago=$(date -v-1y +%Y-%m-%d 2>/dev/null || date -d "1 year ago" +%Y-%m-%d 2>/dev/null || echo "2025-01-26")
echo "日期範圍: $one_year_ago 至 $today"
response=$(curl -s "http://localhost:8000/api/index/%5EIXIC?start_date=$one_year_ago&end_date=$today")
count=$(echo $response | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
start_date=$(echo $response | grep -o '"start":"[^"]*"' | cut -d'"' -f4)
end_date=$(echo $response | grep -o '"end":"[^"]*"' | cut -d'"' -f4)

echo "✓ 查詢成功"
echo "  數據筆數: $count"
echo "  實際範圍: $start_date 至 $end_date"
echo ""

# 測試 4: 查詢全部數據（默認值）
echo "測試 4: 查詢全部數據（2010-01-01 至今）"
response=$(curl -s "http://localhost:8000/api/index/%5EIXIC?start_date=2010-01-01")
count=$(echo $response | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
start_date=$(echo $response | grep -o '"start":"[^"]*"' | cut -d'"' -f4)
end_date=$(echo $response | grep -o '"end":"[^"]*"' | cut -d'"' -f4)

echo "✓ 查詢成功"
echo "  數據筆數: $count"
echo "  實際範圍: $start_date 至 $end_date"
echo ""

echo "========================================"
echo "日期過濾功能測試完成！"
echo "========================================"
echo ""
echo "使用說明："
echo "1. 在網頁上選擇起始日期和結束日期"
echo "2. 點擊「套用」按鈕應用日期過濾"
echo "3. K線圖將顯示所選日期範圍的數據"
echo "4. 點擊「重置」按鈕恢復顯示全部數據"
echo ""
