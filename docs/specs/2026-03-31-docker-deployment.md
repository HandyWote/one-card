# Docker Compose 部署方案

**日期**: 2026-03-31
**状态**: 已确认

---

## 一、技术选型

| 项目 | 选型 |
|------|------|
| 网络模式 | bridge（服务名访问） |
| 数据持久化 | volume 挂载 |
| 环境变量 | .env 文件（本地）/ compose 内写死（Docker） |
| 构建方式 | docker-compose 自动构建 |

---

## 二、目录结构

```
one-card/
├── docker-compose.yml       # Docker Compose 配置
├── .env                     # 环境变量（本地开发用）
├── .env.example             # 环境变量模板
├── Dockerfile.server        # 后端服务 Dockerfile
├── Dockerfile.issuer        # 发卡端 Dockerfile
├── Dockerfile.terminal      # 消费终端 Dockerfile
└── data/                    # 数据持久化目录
    └── onecard.db           # SQLite 数据库（运行时生成）
```

---

## 三、Docker Compose 配置

### 3.1 docker-compose.yml

```yaml
services:
  # 后端服务
  server:
    build:
      context: .
      dockerfile: Dockerfile.server
    container_name: onecard-server
    ports:
      - "8080:8080"
    environment:
      - CARD_HMAC_KEY=${CARD_HMAC_KEY:-default-secret-key-change-in-production}
      - DB_PATH=/data/onecard.db
      - PORT=8080
      - LOG_LEVEL=info
    volumes:
      - ./data:/data
    networks:
      - onecard-net
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/api/stats"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # 发卡端
  issuer:
    build:
      context: .
      dockerfile: Dockerfile.issuer
    container_name: onecard-issuer
    ports:
      - "3001:3001"
    environment:
      - SERVER_URL=http://onecard-server:8080
      - CARD_HMAC_KEY=${CARD_HMAC_KEY:-default-secret-key-change-in-production}
      - PORT=3001
      - LOG_LEVEL=info
    networks:
      - onecard-net
    depends_on:
      server:
        condition: service_healthy
    restart: unless-stopped

  # 消费终端
  terminal:
    build:
      context: .
      dockerfile: Dockerfile.terminal
    container_name: onecard-terminal
    ports:
      - "3002:3002"
    environment:
      - SERVER_URL=http://onecard-server:8080
      - CARD_HMAC_KEY=${CARD_HMAC_KEY:-default-secret-key-change-in-production}
      - PORT=3002
      - LOG_LEVEL=info
    networks:
      - onecard-net
    depends_on:
      server:
        condition: service_healthy
    restart: unless-stopped

networks:
  onecard-net:
    driver: bridge

volumes:
  onecard-data:
    driver: local
```

---

## 四、环境变量配置

### 4.1 .env 文件

```bash
# HMAC密钥（生产环境请修改）
CARD_HMAC_KEY=your-secret-key-here-please-change-in-production

# 可选：端口映射
SERVER_PORT=8080
ISSUER_PORT=3001
TERMINAL_PORT=3002
```

### 4.2 .env.example

```bash
# HMAC密钥（必填，生产环境请使用强密钥）
CARD_HMAC_KEY=

# 可选配置
SERVER_PORT=8080
ISSUER_PORT=3001
TERMINAL_PORT=3002
```

---

## 五、Dockerfile

### 5.1 Dockerfile.server

```dockerfile
# 构建阶段
FROM golang:1.23-alpine AS builder

# 安装必要工具
RUN apk add --no-cache git

WORKDIR /app

# 复制依赖文件
COPY go.mod go.sum ./
RUN go mod download

# 复制源码
COPY ./

# 构建（启用CGO以支持SQLite）
RUN CGO_ENABLED=1 go build -o onecard-server ./server

# 运行阶段
FROM alpine:latest

# 安装SQLite运行时
RUN apk add --no-cache sqlite-libs

WORKDIR /app

# 复制二进制和静态文件
COPY --from=builder /app/onecard-server .
COPY --from=builder /app/server/static ./static

# 创建数据目录
RUN mkdir -p /data

EXPOSE 8080

CMD ["./onecard-server"]
```

### 5.2 Dockerfile.issuer

```dockerfile
# 构建阶段
FROM golang:1.23-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY ./

# 构建（无需CGO）
RUN CGO_ENABLED=0 go build -o onecard-issuer ./issuer

# 运行阶段
FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/onecard-issuer .
COPY --from=builder /app/issuer/static ./static

EXPOSE 3001

CMD ["./onecard-issuer"]
```

### 5.3 Dockerfile.terminal

```dockerfile
# 构建阶段
FROM golang:1.23-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY ./

# 构建（无需CGO）
RUN CGO_ENABLED=0 go build -o onecard-terminal ./terminal

# 运行阶段
FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/onecard-terminal .
COPY --from=builder /app/terminal/static ./static

EXPOSE 3002

CMD ["./onecard-terminal"]
```

---

## 六、服务访问地址

| 服务 | 容器内访问 | 宿主机访问 |
|------|-----------|-----------|
| 后端服务 | `http://onecard-server:8080` | `http://localhost:8080` |
| 发卡端 | `http://onecard-issuer:3001` | `http://localhost:3001` |
| 消费终端 | `http://onecard-terminal:3002` | `http://localhost:3002` |

**注意**：issuer 和 terminal 在容器内通过服务名访问 server，如：
```
SERVER_URL=http://onecard-server:8080
```

---

## 七、使用流程

### 7.1 首次部署

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env，设置 HMAC 密钥
vim .env

# 3. 启动服务（自动构建镜像）
docker-compose up -d

# 4. 查看日志确认启动成功
docker-compose logs -f
```

### 7.2 日常使用

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f server
docker-compose logs -f issuer
docker-compose logs -f terminal
```

### 7.3 重新构建

```bash
# 修改代码后重新构建并启动
docker-compose up -d --build

# 或者强制重新构建（不使用缓存）
docker-compose build --no-cache
docker-compose up -d
```

# 查看日志
make logs
```

### 8.3 重新构建

```bash
# 修改代码后重新构建
make rebuild
```

---

## 九、健康检查

后端服务提供健康检查端点：

```go
// GET /health
func HealthCheck(w http.ResponseWriter, r *http.Request) {
    // 检查数据库连接
    if err := db.DB.Ping(); err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        return
    }
    w.WriteHeader(http.StatusOK)
}
```

---

## 八、健康检查

后端服务提供健康检查端点：

```go
// GET /health
func HealthCheck(w http.ResponseWriter, r *http.Request) {
    // 检查数据库连接
    if err := db.DB.Ping(); err != nil {
        w.WriteHeader(http.StatusServiceUnavailable)
        return
    }
    w.WriteHeader(http.StatusOK)
}
```

---

## 九、数据备份

### 9.1 备份数据库

```bash
# 备份到当前目录
docker cp onecard-server:/data/onecard.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

### 9.2 恢复数据库

```bash
# 从备份恢复
docker cp ./backup_xxxxxx.db onecard-server:/data/onecard.db
docker-compose restart server
```

---

## 十、故障排查

### 10.1 查看服务状态

```bash
docker-compose ps
```

### 10.2 查看特定服务日志

```bash
# 后端服务
docker-compose logs server

# 发卡端
docker-compose logs issuer

# 消费终端
docker-compose logs terminal
```

### 10.3 进入容器调试

```bash
# 进入后端容器
docker exec -it onecard-server sh

# 进入发卡端容器
docker exec -it onecard-issuer sh

# 进入终端容器
docker exec -it onecard-terminal sh
```

---

## 十一、生产环境注意事项

| 事项 | 说明 |
|------|------|
| HMAC密钥 | 使用强密钥，通过环境变量或密钥管理系统注入 |
| HTTPS | 生产环境建议启用 TLS |
| 日志级别 | 生产环境设置为 `info` 或 `warn` |
| 数据备份 | 定期备份 SQLite 数据库 |
| 资源限制 | 根据实际负载设置 CPU/内存限制 |
| 高可用 | SQLite 不适合高并发，如需高可用考虑迁移到 PostgreSQL/MySQL |
