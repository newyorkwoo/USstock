# Docker 部署指南

## 快速開始

### 1. 構建並啟動所有服務

```bash
docker-compose up -d --build
```

### 2. 查看運行狀態

```bash
docker-compose ps
```

### 3. 查看日誌

```bash
# 查看所有服務日誌
docker-compose logs -f

# 查看後端日誌
docker-compose logs -f backend

# 查看前端日誌
docker-compose logs -f frontend
```

### 4. 停止服務

```bash
docker-compose down
```

### 5. 停止並刪除所有數據

```bash
docker-compose down -v
```

## 訪問應用

- **前端應用**: http://localhost
- **後端 API**: http://localhost:8000

## 服務說明

### Backend (後端)

- 基於 Python 3.11
- Flask Web 框架
- 端口: 8000
- 提供股票數據 API

### Frontend (前端)

- 基於 Node.js 20
- Vue 3 + Vite
- Nginx 提供靜態文件服務
- 端口: 80
- 自動代理 /api/ 請求到後端

## 常用命令

### 重新構建特定服務

```bash
# 重新構建後端
docker-compose build backend

# 重新構建前端
docker-compose build frontend
```

### 重啟服務

```bash
# 重啟所有服務
docker-compose restart

# 重啟特定服務
docker-compose restart backend
docker-compose restart frontend
```

### 進入容器

```bash
# 進入後端容器
docker-compose exec backend sh

# 進入前端容器
docker-compose exec frontend sh
```

### 清理未使用的 Docker 資源

```bash
# 清理未使用的容器、網絡、映像
docker system prune -a

# 清理未使用的卷
docker volume prune
```

## 開發模式

如果需要在開發模式下運行（代碼變更自動重載）：

```bash
# 使用原有的啟動腳本
./start-backend.sh
./start-frontend.sh
```

## 生產部署建議

1. **環境變量**: 創建 `.env` 文件管理敏感配置
2. **反向代理**: 使用 Nginx 或 Traefik 作為前端反向代理
3. **SSL/TLS**: 配置 HTTPS 證書
4. **監控**: 添加日誌收集和監控系統
5. **備份**: 定期備份重要數據

## 故障排除

### 端口衝突

如果端口 80 或 8000 已被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8080:80" # 將前端改為 8080
  - "8001:8000" # 將後端改為 8001
```

### 構建失敗

1. 確保 Docker 和 Docker Compose 已正確安裝
2. 檢查網絡連接
3. 清理 Docker 緩存後重試：
   ```bash
   docker-compose down
   docker system prune -a
   docker-compose up -d --build
   ```

### 後端健康檢查失敗

後端容器啟動後需要一些時間來安裝依賴和啟動服務，healthcheck 配置了 40 秒的啟動時間。如果仍然失敗，檢查後端日誌：

```bash
docker-compose logs backend
```
