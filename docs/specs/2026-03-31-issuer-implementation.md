# 发卡端 (issuer) 实现方案

**日期**: 2026-03-31
**状态**: 已确认

---

## 一、技术选型

| 项目 | 选型 |
|------|------|
| HTTP框架 | `net/http` 标准库 |
| 前端框架 | Vue/React |
| 卡片保存 | 用户选择目录 |
| HMAC密钥 | 环境变量（与server一致） |
| 浏览器 | 启动时自动打开 |
| 端口 | 可配置（默认3001） |

---

## 二、目录结构

```
issuer/
├── main.go              # 入口：HTTP服务、浏览器自动打开
├── api/
│   ├── router.go        # 路由注册
│   ├── handler.go       # API处理函数
│   └── client.go        # 后端HTTP客户端封装
├── card/
│   ├── generator.go     # 卡片生成逻辑
│   └── file.go          # 文件保存（用户选择目录）
├── crypto/
│   └── hmac.go          # HMAC签名（复用common或独立）
└── static/              # 前端界面（Vue/React构建产物）
    └── embed.go         //go:embed
```

---

## 三、功能模块

### 3.1 核心功能

| 功能 | 说明 |
|------|------|
| 创建卡片 | 输入卡号、姓名、初始金额 → 生成JSON卡片文件 + 调用后端API创建记录 |
| 充值 | 输入卡号、充值金额 → 调用后端API充值 |

### 3.2 前端界面

```
┌─────────────────────────────────────┐
│           一卡通发卡端               │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐   │
│  │  功能选择：                 │   │
│  │  ○ 创建卡片                 │   │
│  │  ○ 充值                     │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  创建卡片                   │   │
│  │                             │   │
│  │  卡号：[_____________]      │   │
│  │  姓名：[_____________]      │   │
│  │  初始金额：[_____]          │   │
│  │                             │   │
│  │  保存位置：[选择目录...]    │   │
│  │                             │   │
│  │  [ 创建并保存卡片 ]         │   │
│  └─────────────────────────────┘   │
│                                     │
│  结果：[消息显示区域]               │
└─────────────────────────────────────┘
```

---

## 四、API 端点（issuer内部）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 前端界面 |
| POST | `/api/create` | 创建卡片 |
| POST | `/api/recharge` | 充值 |
| GET | `/api/select-dir` | 触发目录选择（可选） |

---

## 五、创建卡片流程

```
1. 用户输入：卡号、姓名、初始金额
2. 选择保存目录
3. 生成卡片数据：
   - 填充基本字段
   - 生成 HMAC 签名
4. 调用后端 API: POST /api/cards
5. 保存 JSON 文件到用户选择目录
6. 返回结果给前端
```

### 5.1 卡片文件生成

```go
type CardFile struct {
    CardID       string                   `json:"card_id"`
    Name         string                   `json:"name"`
    Balance      float64                  `json:"balance"`
    Status       string                   `json:"status"`
    ExpiresAt    time.Time                `json:"expires_at"`
    CreatedAt    time.Time                `json:"created_at"`
    UpdatedAt    time.Time                `json:"updated_at"`
    Transactions []TransactionRecord      `json:"transactions"`
    HMAC         string                   `json:"hmac"`
}

func GenerateCard(cardID, name string, initialBalance float64, hmacKey string) (*CardFile, error) {
    now := time.Now()
    card := &CardFile{
        CardID:       cardID,
        Name:         name,
        Balance:      initialBalance,
        Status:       "active",
        ExpiresAt:    now.AddDate(4, 0, 0), // 4年有效期
        CreatedAt:    now,
        UpdatedAt:    now,
        Transactions: []TransactionRecord{},
    }

    // 计算HMAC
    data, _ := json.Marshal(card)
    card.HMAC = generateHMAC(data, hmacKey)

    return card, nil
}
```

---

## 六、充值流程

```
1. 用户输入：卡号、充值金额
2. 调用后端 API: POST /api/cards/:id/recharge
3. 显示充值结果
```

---

## 七、环境变量

```bash
# 后端服务地址
SERVER_URL=http://onecard-server:8080

# HMAC密钥（与server一致）
CARD_HMAC_KEY=your-secret-key-here

# 监听端口
PORT=3001

# 日志级别
LOG_LEVEL=debug
```

---

## 八、与后端交互

### 8.1 创建卡片（调用后端）

```go
func CreateCardOnServer(serverURL, cardID, name string, initialBalance float64) error {
    payload := map[string]interface{}{
        "card_id":          cardID,
        "name":             name,
        "initial_balance":  initialBalance,
    }

    resp, err := http.Post(
        fmt.Sprintf("%s/api/cards", serverURL),
        "application/json",
        bytes.NewReader(payload),
    )
    // ...
}
```

### 8.2 充值（调用后端）

```go
func RechargeCard(serverURL, cardID string, amount float64) error {
    payload := map[string]interface{}{
        "amount": amount,
    }

    resp, err := http.Post(
        fmt.Sprintf("%s/api/cards/%s/recharge", serverURL, cardID),
        "application/json",
        bytes.NewReader(payload),
    )
    // ...
}
```

---

## 九、浏览器自动打开

```go
func OpenBrowser(url string) error {
    var cmd string
    var args []string

    switch runtime.GOOS {
    case "windows":
        cmd = "cmd"
        args = []string{"/c", "start"}
    case "darwin":
        cmd = "open"
    default: // "linux", "freebsd", "openbsd", "netbsd"
        cmd = "xdg-open"
    }
    args = append(args, url)
    return exec.Command(cmd, args...).Start()
}

// main.go
func main() {
    port := getPort() // 默认3001
    url := fmt.Sprintf("http://localhost:%d", port)

    // 启动HTTP服务
    go startServer(port)

    // 延迟打开浏览器
    time.Sleep(500 * time.Millisecond)
    OpenBrowser(url)

    // 等待信号
    sig := make(chan os.Signal, 1)
    signal.Notify(sig, os.Interrupt)
    <-sig
}
```

---

## 十、Docker 配置

### 10.1 Dockerfile

```dockerfile
FROM golang:1.23-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -o onecard-issuer ./issuer

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/onecard-issuer .
COPY --from=builder /app/issuer/static ./static

EXPOSE 3001
CMD ["./onecard-issuer"]
```

### 10.2 docker-compose.yml

```yaml
services:
  issuer:
    build: .
    ports:
      - "3001:3001"
    environment:
      - SERVER_URL=http://onecard-server:8080
      - CARD_HMAC_KEY=${CARD_HMAC_KEY}
      - PORT=3001
    depends_on:
      - server
    network_mode: host
```

---

## 十一、开发步骤

1. [ ] 初始化 Go 模块和依赖
2. [ ] 实现卡片生成逻辑（含HMAC）
3. [ ] 实现文件保存功能
4. [ ] 实现后端API客户端
5. [ ] 实现HTTP服务器和路由
6. [ ] 实现浏览器自动打开
7. [ ] 前端界面开发
8. [ ] Docker 部署配置
