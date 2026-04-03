# 校园一卡通模拟消费终端系统

一个基于 python + tkinter 的校园一卡通模拟系统，包含消费终端和充值发卡站两个独立程序，使用 SQLite 数据库保证数据一致性。

> 该项目属于汕头大学一级项目，采用 MIT 协议

---

## 系统架构

```
issuer.py（充值发卡站）──► SQLite 数据库 ◄── terminal.py（消费终端）
                               │
                      data/cards/*（卡片文件，文件名即卡号，无后缀）
```

### 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| **消费终端** | `terminal.py` | POS 风格刷卡消费，支持多件商品金额运算 |
| **充值发卡站** | `issuer.py` | 新卡发行、圈存充值 |

### 技术栈

- **Python 3.x** — 编程语言
- **tkinter** — GUI 框架（标准库，无需额外安装）
- **SQLite** — 轻量级数据库，存储卡片和交易数据
- **unittest** — 单元测试框架

---

## 快速开始

### 前置要求

- Python 3.x
- uv（Python 包管理器，可选）

### 运行程序

```bash
# 运行消费终端
uv run terminal.py

# 运行充值发卡站
uv run issuer.py

# 运行单元测试
uv run -m pytest tests/
```

---

## 使用流程

### 1. 发卡

运行 `issuer.py` → 切换到「发卡」选项卡 → 输入卡号、姓名、初始金额 → 点击「生成卡片」→ 自动创建卡片文件（文件名即卡号）

### 2. 消费

运行 `terminal.py` → 通过按键区输入/计算金额 → 点击「确定」→ 拖拽卡片文件到窗口 → 自动扣款并显示结果

### 3. 充值

运行 `issuer.py` → 切换到「充值」选项卡 → 输入充值金额 → 拖拽卡片文件到窗口 → 自动完成圈存充值

---

## 卡片文件格式

卡片文件名即卡号（如 `2024001`，无后缀），内容为 JSON 格式：

```json
{
  "card_id": "2024001",
  "name": "张三",
  "balance": 85.50,
  "status": "active",
  "created_at": "2026-04-01"
}
```

文件是卡片的导入/导出格式，真实数据存储在 SQLite 数据库中。

---

## 项目结构

```
one-card/
├── terminal.py          # 消费终端主程序
├── issuer.py            # 充值发卡站主程序
├── card_manager.py      # 卡片管理模块
├── calculator.py        # 辅助运算模块
├── logger.py            # 交易记录模块
├── database.py          # 数据库管理模块
├── data/
│   ├── onecard.db       # SQLite 数据库
│   └── cards/           # 卡片文件（文件名即卡号）
├── tests/               # 单元测试
└── docs/                # 设计文档
```

---

## 文档

详细设计文档请查看 [docs/specs/](docs/specs/)：

- [系统设计文档](docs/specs/2026-04-03-design.md) — 完整的系统设计、模块说明和结算方案

---

## 许可证

MIT License
