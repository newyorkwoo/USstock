#!/bin/bash

echo "=================================="
echo "美國股市分析系統 - 前端啟動腳本"
echo "=================================="

cd frontend

# 檢查 Node.js
if ! command -v node &> /dev/null; then
    echo "錯誤: 找不到 Node.js。請先安裝 Node.js 18+"
    exit 1
fi

echo "Node.js 版本: $(node -v)"
echo "npm 版本: $(npm -v)"
echo ""

# 檢查依賴
if [ ! -d "node_modules" ]; then
    echo "安裝依賴..."
    npm install
fi

echo ""
echo "啟動前端服務器..."
echo "正在檢測可用端口..."
echo "按 Ctrl+C 停止服務器"
echo ""

npm run dev
