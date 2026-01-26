# Gunicorn 配置文件

import multiprocessing

# 綁定地址和端口
bind = "0.0.0.0:8000"

# Worker 配置
workers = multiprocessing.cpu_count() * 2 + 1  # 推薦的 worker 數量
worker_class = "gthread"  # 使用線程 worker
threads = 4  # 每個 worker 的線程數

# 超時設置
timeout = 120  # 請求超時時間（秒）
graceful_timeout = 30  # 優雅關閉超時時間（秒）
keepalive = 5  # Keep-Alive 連接保持時間（秒）

# 日誌配置
accesslog = "-"  # 訪問日誌輸出到 stdout
errorlog = "-"   # 錯誤日誌輸出到 stderr
loglevel = "info"

# 進程命名
proc_name = "usstock-api"

# 預加載應用
preload_app = True

# 最大請求數（防止內存洩漏）
max_requests = 1000
max_requests_jitter = 50

# 優雅重啟
reload = False

# Worker 臨時目錄
worker_tmp_dir = "/dev/shm"

print(f"Gunicorn 配置: {workers} workers, {threads} threads per worker")
