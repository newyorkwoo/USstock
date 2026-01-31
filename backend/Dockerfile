# 使用 Python 3.11-slim 作為基礎映像
FROM python:3.11-slim

# 設置時區
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 設置工作目錄
WORKDIR /app

# 安裝運行時依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 複製 requirements.txt 並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建數據目錄
RUN mkdir -p /app/data

# 暴露後端端口
EXPOSE 8000

# 使用 Gunicorn 啟動（生產環境）
CMD ["gunicorn", "--config", "gunicorn_config.py", "app_optimized:app"]
