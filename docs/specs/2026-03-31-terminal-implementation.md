# 消费终端 (terminal) 实现方案

**日期**: 2026-03-31
**状态**: 已确认

---

## 一、技术选型

| 项目 | 选型 |
|------|------|
| HTTP框架 | `net/http` 标准库 |
| 前端框架 | Vue/React |
| 界面风格 | 模拟POS机 |
| 卡片加载 | 文件选择器 + 拖拽 |
| 金额输入 | 数字键盘 |
| 端口 | 可配置（默认3002） |
| HMAC密钥 | 环境变量（与server一致） |

---

## 二、目录结构

```
terminal/
├── main.go              # 入口：HTTP服务、浏览器自动打开
├── api/
│   ├── router.go        # 路由注册
│   ├── handler.go       # API处理函数
│   └── client.go        # 后端HTTP客户端
├── card/
│   ├── parser.go        # 卡片文件解析
│   └── validator.go     # HMAC验证
├── crypto/
│   └── hmac.go          # HMAC签名（复用）
└── static/              # 前端界面
    └── embed.go         //go:embed
```

---

## 三、操作流程

```
1. 用户通过数字键盘输入金额
2. 点击"开始扣费"按钮（锁定金额）
3. 用户上传卡片文件（拖拽或选择）
4. 系统验证卡片HMAC
5. 调用后端API扣款
6. 更新卡片余额和交易记录
7. 返回更新后的卡片文件，自动下载
8. 显示扣费结果（余额、交易信息）
```

---

## 四、界面设计（模拟POS机）

```
┌─────────────────────────────────────────────────────────┐
│                    一卡通消费终端                         │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐  │
│  │                    显示区                          │  │
│  │                                                   │  │
│  │  状态：等待输入金额                                │  │
│  │  金额：¥ 0.00                                     │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────┐     │  │
│  │  │  拖拽卡片到此处，或点击上传              │     │  │
│  │  │         [上传卡片文件]                   │     │  │
│  │  └─────────────────────────────────────────┘     │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │      7       │  │      8       │  │      9       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │      4       │  │      5       │  │      6       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │      1       │  │      2       │  │      3       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   清除(C)    │  │      0       │  │   确认(OK)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              [开始扣费]                            │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 五、API 端点（terminal内部）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 前端界面 |
| POST | `/api/charge` | 扣费（接收卡片文件+金额） |

---

## 六、扣费流程实现

### 6.1 前端状态管理

```typescript
enum TerminalState {
  INPUT_AMOUNT,      // 输入金额
  WAIT_CARD,         // 等待上传卡片
  CHARGING,          // 扣费中
  SUCCESS,           // 扣费成功
  ERROR              // 扣费失败
}

interface TerminalData {
  state: TerminalState;
  amount: number;           // 输入的金额
  cardInfo?: CardInfo;      // 卡片信息
  result?: ChargeResult;    // 扣费结果
  message: string;          // 提示信息
}
```

### 6.2 扣费请求

```go
type ChargeRequest struct {
    Amount float64 `json:"amount"`
    CardFile []byte `json:"card_file"`
}

type ChargeResponse struct {
    Code    int    `json:"code"`
    Message string `json:"message"`
    Data    struct {
        Balance      float64 `json:"balance"`
        Transaction  Transaction `json:"transaction"`
        UpdatedCard  []byte  `json:"updated_card"` // 更新后的卡片文件
    } `json:"data"`
}
```

### 6.3 后端处理流程

```go
func HandleCharge(w http.ResponseWriter, r *http.Request) {
    // 1. 解析请求
    var req ChargeRequest
    json.NewDecoder(r.Body).Decode(&req)

    // 2. 解析卡片文件
    card, err := ParseCardFile(req.CardFile)
    if err != nil {
        writeError(w, 1005, "卡片格式错误")
        return
    }

    // 3. 验证HMAC
    if !VerifyHMAC(card, hmacKey) {
        writeError(w, 1005, "签名验证失败")
        return
    }

    // 4. 调用后端API扣款
    result, err := CallConsumeAPI(serverURL, card.CardID, req.Amount, "终端")
    if err != nil {
        writeError(w, 5000, err.Error())
        return
    }

    // 5. 更新卡片
    card.Balance = result.BalanceAfter
    card.Transactions = append(card.Transactions, result.Transaction)
    card.UpdatedAt = time.Now()
    card.HMAC = GenerateHMAC(card, hmacKey)

    // 6. 序列化更新后的卡片
    updatedCard, _ := json.Marshal(card)

    // 7. 返回结果
    writeJSON(w, ChargeResponse{
        Code: 0,
        Message: "success",
        Data: struct {
            Balance     float64    `json:"balance"`
            Transaction Transaction `json:"transaction"`
            UpdatedCard []byte     `json:"updated_card"`
        }{
            Balance:     card.Balance,
            Transaction: result.Transaction,
            UpdatedCard: updatedCard,
        },
    })
}
```

---

## 七、前端逻辑

### 7.1 金额输入

```typescript
function handleNumPad(num: number) {
  if (state.state !== TerminalState.INPUT_AMOUNT) return;
  const newAmount = state.amount * 10 + num;
  setState({ amount: newAmount });
}

function handleClear() {
  if (state.state !== TerminalState.INPUT_AMOUNT) return;
  setState({ amount: 0 });
}
```

### 7.2 开始扣费

```typescript
async function handleStartCharge() {
  if (state.amount <= 0) {
    setState({ message: "请输入有效金额" });
    return;
  }
  setState({
    state: TerminalState.WAIT_CARD,
    message: `请上传卡片，扣费金额：¥${state.amount.toFixed(2)}`
  });
}
```

### 7.3 上传卡片并扣费

```typescript
async function handleCardUpload(file: File) {
  setState({ state: TerminalState.CHARGING, message: "扣费中..." });

  const formData = new FormData();
  formData.append('amount', state.amount);
  formData.append('card_file', file);

  try {
    const resp = await fetch('/api/charge', {
      method: 'POST',
      body: formData
    });
    const result = await resp.json();

    if (result.code === 0) {
      setState({
        state: TerminalState.SUCCESS,
        result: result.data,
        message: `扣费成功！余额：¥${result.data.balance}`
      });

      // 自动下载更新后的卡片
      downloadCard(result.data.updated_card);
    } else {
      setState({
        state: TerminalState.ERROR,
        message: `扣费失败：${result.message}`
      });
    }
  } catch (err) {
    setState({
      state: TerminalState.ERROR,
      message: `网络错误：${err.message}`
    });
  }
}
```

### 7.4 下载卡片

```typescript
function downloadCard(cardData: Uint8Array) {
  const blob = new Blob([cardData], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `card_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
```

---

## 八、环境变量

```bash
# 后端服务地址
SERVER_URL=http://onecard-server:8080

# HMAC密钥（与server一致）
CARD_HMAC_KEY=your-secret-key-here

# 监听端口
PORT=3002

# 日志级别
LOG_LEVEL=debug
```

---

## 九、错误处理

| 错误 | 处理 |
|------|------|
| 金额无效 | 提示重新输入 |
| 卡片格式错误 | 提示卡片文件损坏 |
| HMAC验证失败 | 提示签名无效，可能被篡改 |
| 卡号不存在 | 提示卡片未注册 |
| 余额不足 | 提示余额不足，显示当前余额 |
| 卡片已过期 | 提示卡片已过期 |
| 卡片已挂失 | 提示卡片已挂失 |
| 网络错误 | 提示检查网络连接 |

---

## 十、Docker 配置

### 10.1 Dockerfile

```dockerfile
FROM golang:1.23-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -o onecard-terminal ./terminal

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/onecard-terminal .
COPY --from=builder /app/terminal/static ./static

EXPOSE 3002
CMD ["./onecard-terminal"]
```

### 10.2 docker-compose.yml

```yaml
services:
  terminal:
    build: .
    ports:
      - "3002:3002"
    environment:
      - SERVER_URL=http://onecard-server:8080
      - CARD_HMAC_KEY=${CARD_HMAC_KEY}
      - PORT=3002
    depends_on:
      - server
    network_mode: host
```

---

## 十一、开发步骤

1. [ ] 初始化 Go 模块和依赖
2. [ ] 实现卡片解析和HMAC验证
3. [ ] 实现扣费API处理器
4. [ ] 实现HTTP服务器
5. [ ] 实现浏览器自动打开
6. [ ] 前端界面开发（POS机风格）
7. [ ] 实现金额输入和卡片上传
8. [ ] 实现扣费流程和结果展示
9. [ ] 实现卡片自动下载
10. [ ] Docker 部署配置
