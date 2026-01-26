#!/bin/bash

echo "=================================="
echo "美國股市分析系統 - 後端啟動腳本"
echo "=================================="

cd backend

# 檢查 Python 環境
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "錯誤: 找不到 Python。請先安裝 Python 3.8+"
    exit 1
fi

echo "使用 Python: $PYTHON_CMD"
echo ""

# 創建或激活虛擬環境
if [ ! -d "venv" ]; then
    echo "創建虛擬環境..."
    $PYTHON_CMD -m venv venv
fi

echo "激活虛擬環境..."
source venv/bin/activate

# 檢查依賴
echo "檢查依賴..."
pip install -r requirements.txt

echo ""
echo "啟動後端服務器..."
echo "API 地址: http://localhost:8000"
echo "按 Ctrl+C 停止服務器"
echo ""

python app.py
