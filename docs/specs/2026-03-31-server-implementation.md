# 后端服务 (server) 实现方案

**日期**: 2026-03-31
**状态**: 已确认

---

## 一、技术选型

| 项目 | 选型 |
|------|------|
| HTTP框架 | `net/http` 标准库 |
| ORM | GORM |
| 路由 | RESTful 风格 (`/api/cards/:id`) |
| 鉴权 | 无（开放访问）|
| 中间件 | 请求日志 |
| 日志格式 | 结构化 JSON |
| 数据库迁移 | GORM AutoMigrate |
| 管理界面 | Vue/React |
| HMAC密钥 | 环境变量 |
| 数据库 | SQLite（GORM 抽象，可迁移 PostgreSQL） |
| 服务设计 | 无状态，可水平扩展 |

---

## 二、目录结构

```
server/
├── main.go              # 入口：初始化DB、HTTP服务、路由注册
├── api/
│   ├── router.go        # 路由注册：ServeHTTP + 路由树
│   ├── handler.go       # 请求处理函数（按领域分组）
│   └── middleware.go    # 日志中间件
├── db/
│   ├── db.go            # GORM初始化 + AutoMigrate（支持多驱动）
│   └── models.go        # Card/Transaction 结构体
├── service/
│   ├── card.go          # 卡片业务逻辑
│   └── stats.go         # 统计业务逻辑
├── crypto/
│   └── hmac.go          # HMAC签名/验证
└── static/              # 管理界面（Vue/React构建产物）
    └── embed.go         //go:embed
```

---

## 三、API 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/cards` | 创建卡片 |
| GET | `/api/cards` | 查询所有卡片（管理后台） |
| GET | `/api/cards/:id` | 查询单张卡片 |
| POST | `/api/cards/:id/consume` | 消费扣款 |
| POST | `/api/cards/:id/recharge` | 充值 |
| POST | `/api/cards/:id/suspend` | 挂失 |
| POST | `/api/cards/:id/activate` | 解挂 |
| GET | `/api/transactions` | 查询交易记录（可按card_id筛选） |
| GET | `/api/transactions/all` | 所有交易（管理后台） |
| GET | `/api/stats` | 统计数据 |
| GET | `/health` | 健康检查 |
| GET | `/` | 管理界面（SPA fallback） |

---

## 四、数据模型

### 4.1 Card 结构体

```go
type Card struct {
    ID        uint      `gorm:"primaryKey"`
    CardID    string    `gorm:"uniqueIndex;size:50"`
    Name      string    `gorm:"size:100"`
    Balance   float64   `gorm:"type:decimal(10,2)"`
    Status    string    `gorm:"size:20;default:active"` // active, suspended
    ExpiresAt time.Time
    CreatedAt time.Time
    UpdatedAt time.Time
}
```

### 4.2 Transaction 结构体

```go
type Transaction struct {
    ID           uint      `gorm:"primaryKey"`
    TxID         string    `gorm:"uniqueIndex;size:50"`
    CardID       string    `gorm:"index;size:50"`
    Type         string    `gorm:"size:20"` // consume, recharge
    Amount       float64   `gorm:"type:decimal(10,2)"`
    Merchant     string    `gorm:"size:100"`
    BalanceAfter float64   `gorm:"type:decimal(10,2)"`
    CreatedAt    time.Time
}
```

---

## 五、通用响应格式

```go
type Response struct {
    Code    int         `json:"code"`    // 0=成功，非0=错误
    Message string      `json:"message"`
    Data    interface{} `json:"data,omitempty"`
}
```

### 错误码定义

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 卡号不存在 |
| 1002 | 余额不足 |
| 1003 | 卡片已过期 |
| 1004 | 卡片已挂失 |
| 1005 | 签名验证失败 |
| 5000 | 服务器内部错误 |

---

## 六、环境变量

```bash
# HMAC签名密钥（必填）
CARD_HMAC_KEY=your-secret-key-here

# 数据库配置（GORM 抽象层，便于迁移）
DB_DRIVER=sqlite                    # sqlite | postgres
DB_DSN=/data/onecard.db             # SQLite: 文件路径 | PostgreSQL: 连接串

# 服务端口
PORT=8080

# 日志级别
LOG_LEVEL=debug
```

---

## 七、中间件设计

### 7.1 请求日志中间件

```go
func LoggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()

        // 记录请求信息
        log.Entry{
            Time:    start,
            Method:  r.Method,
            Path:    r.URL.Path,
            Query:   r.URL.RawQuery,
            Client:  r.RemoteAddr,
        }.Info("Request")

        // 调用下一个处理器
        next.ServeHTTP(w, r)

        // 记录响应时间
        duration := time.Since(start)
        log.Entry{
            Duration: duration,
        }.Info("Response")
    })
}
```

---

## 八、核心业务逻辑

### 8.1 创建卡片

1. 验证请求参数（card_id、name、initial_balance）
2. 检查 card_id 是否已存在
3. 创建 Card 记录
4. 返回卡片信息

### 8.2 消费扣款

1. 验证 HMAC 签名
2. 检查卡片是否存在、状态是否正常、是否过期
3. 检查余额是否充足
4. 开启事务：
   - 扣减卡片余额
   - 创建交易记录
5. 提交事务
6. 返回扣款结果

### 8.3 充值

1. 验证 HMAC 签名
2. 检查卡片是否存在
3. 开启事务：
   - 增加卡片余额
   - 创建交易记录
4. 提交事务
5. 返回充值结果

### 8.4 统计数据

```go
type Stats struct {
    TotalCards      int64   // 总卡片数
    ActiveCards     int64   // 活跃卡片数
    TotalBalance    float64 // 总余额
    TotalConsume    float64 // 累计消费金额
    TotalRecharge   float64 // 累计充值金额
    TodayConsume    float64 // 今日消费
    TodayRecharge   float64 // 今日充值
}
```

---

## 九、HMAC 签名

### 9.1 签名生成

```go
func GenerateHMAC(data []byte, key string) string {
    h := hmac.New(sha256.New, []byte(key))
    h.Write(data)
    return hex.EncodeToString(h.Sum(nil))
}
```

### 9.2 签名验证

```go
func VerifyHMAC(data []byte, key, signature string) bool {
    expected := GenerateHMAC(data, key)
    return hmac.Equal([]byte(expected), []byte(signature))
}
```

---

## 十、管理界面（Vue/React）

### 10.1 功能模块

| 模块 | 功能 |
|------|------|
| 仪表盘 | 统计数据展示（卡片数、余额、交易额） |
| 卡片管理 | 列表、搜索、详情查看 |
| 交易记录 | 列表、筛选（按卡号、类型、时间） |

### 10.2 构建集成

```go
//go:embed static/*
var staticFS embed.FS

func main() {
    // ...
    http.Handle("/", http.FileServer(http.FS(staticFS)))
}
```

---

## 十一、Docker 配置

### 11.1 Dockerfile

```dockerfile
FROM golang:1.23-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=1 go build -o onecard-server ./server

FROM alpine:latest
RUN apk add --no-cache sqlite-libs
WORKDIR /app
COPY --from=builder /app/onecard-server .
COPY --from=builder /app/server/static ./static

RUN mkdir -p /data

EXPOSE 8080
CMD ["./onecard-server"]
```

### 11.2 docker-compose.yml（server 部分）

```yaml
server:
    build:
      context: .
      dockerfile: Dockerfile.server
    ports:
      - "8080:8080"
    environment:
      - CARD_HMAC_KEY=${CARD_HMAC_KEY}
      - DB_DRIVER=sqlite
      - DB_DSN=/data/onecard.db
    volumes:
      - ./data:/data
    networks:
      - onecard-net
```

### 11.3 水平扩展（迁移 PG 后）

```bash
# 迁移 PG 后，server 可水平扩展
docker-compose up -d --scale server=3 --scale terminal=10
```

---

## 十二、开发步骤

1. [ ] 初始化 Go 模块和依赖
2. [ ] 实现数据模型和 GORM 配置
3. [ ] 实现 HMAC 签名工具
4. [ ] 实现卡片服务（CRUD）
5. [ ] 实现交易服务
6. [ ] 实现 API 路由和处理器
7. [ ] 实现统计服务
8. [ ] 添加日志中间件
9. [ ] 前端管理界面开发
10. [ ] Docker 部署配置
