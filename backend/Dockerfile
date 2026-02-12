# 使用 Python 3.11-slim 作為基礎映像
FROM python:3.11-slim

# 設置時區
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 設置工作目錄
WORKDIR /app

# 安裝運行時依賴（包括 cron）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    tzdata \
    cron \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 複製 requirements.txt 並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 設置 crontab
COPY crontab /etc/cron.d/update-indices
RUN chmod 0644 /etc/cron.d/update-indices \
    && crontab /etc/cron.d/update-indices \
    && touch /var/log/cron.log

# 設置啟動腳本權限
RUN chmod +x /app/entrypoint.sh /app/update_indices.py

# 創建數據目錄
RUN mkdir -p /app/data

# 暴露後端端口
EXPOSE 8000

# 使用啟動腳本（同時啟動 Cron 和 Gunicorn）
CMD ["/app/entrypoint.sh"]
