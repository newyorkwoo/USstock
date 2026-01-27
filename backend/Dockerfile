# 使用 Python 3.11-slim 作為基礎映像
FROM python:3.11-slim as builder

# 設置工作目錄
WORKDIR /app

# 安裝編譯依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝依賴到本地
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 最終階段
FROM python:3.11-slim

WORKDIR /app

# 安裝運行時依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 從 builder 複製已安裝的 Python 包
COPY --from=builder /root/.local /root/.local

# 確保 Python 能找到包
ENV PATH=/root/.local/bin:$PATH

# 複製應用程式代碼
COPY . .

# 創建非 root 用戶和數據目錄
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app
USER appuser

# 暴露後端端口
EXPOSE 8000

# 使用 Gunicorn 啟動（生產環境）
CMD ["gunicorn", "--config", "gunicorn_config.py", "app_optimized:app"]
