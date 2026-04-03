# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## TOP RULES
ALWAYS REPLY IN CHINESE
have to use superpower
use TDD to develop(REG)
always give me several resolutions and recommand a plan that has lower tech-debt
dont edit code without acception, just discuss

---

## Project Overview

校园一卡通模拟消费终端系统，包含两个独立的 Python 程序：

- **消费终端**（`terminal.py`）— 模拟食堂/超市 POS 刷卡机，支持拖拽刷卡、运算、自动扣款
- **充值发卡站**（`issuer.py`）— 模拟校内自助充值机，支持发卡和圈存充值

技术栈：Python 3.x + tkinter + SQLite，无网络通信，通过文件系统和 SQLite 数据库交换数据。

---

## Architecture

```
issuer.py ──► SQLite (data/onecard.db) ◄── terminal.py
                    │
           data/cards/*  (卡片文件，文件名即卡号，无后缀，内容为 JSON)
```

**Key Design Decisions:**

1. **SQLite 为主存储** — 卡片数据和交易记录存储在 SQLite 数据库中，保证数据一致性
2. **JSON 为导入/导出格式** — 卡片通过文件在程序间传递，文件名即卡号（无后缀），内容为 JSON，模拟真实卡片的物理载体
3. **无网络通信** — 两个独立程序，通过共享 SQLite 数据库和 JSON 文件交换数据
4. **tkinter GUI** — 使用标准库，无需额外安装
5. **运算器按输入顺序计算** — 不遵循数学优先级，符合 POS 机逐项累加的使用习惯
6. **先输金额再刷卡** — 模拟真实 POS 机流程：先在终端输入/计算金额，再拖拽卡片文件到窗口模拟刷卡，自动触发扣款
7. **无需拔卡** — 交易完成后结果保持显示，直到下次输入操作自动重置

---

## File Structure

```
project/
├── terminal.py          # 消费终端 GUI
├── issuer.py            # 充值发卡站 GUI
├── card_manager.py      # 卡片管理（SQLite CRUD + JSON 导入导出）
├── calculator.py        # 辅助运算（+、-、×）
├── logger.py            # 交易记录（SQLite）
├── database.py          # SQLite 连接管理
├── data/
│   ├── onecard.db       # SQLite 数据库
│   └── cards/           # 卡片文件目录（文件名即卡号，无后缀）
├── tests/
│   ├── test_card_manager.py
│   ├── test_calculator.py
│   └── test_logger.py
└── docs/
    └── specs/
        └── 2026-04-03-design.md   # 详细设计文档
```

---

## Database Schema

**cards 表**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `card_id` | TEXT PK | 卡号 |
| `name` | TEXT | 持卡人姓名 |
| `balance` | REAL | 当前余额 |
| `status` | TEXT | active / suspended |
| `created_at` | TEXT | 建卡日期 |

**transactions 表**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `tx_id` | TEXT PK | 流水号 TX+时间戳 |
| `card_id` | TEXT | 关联卡号 |
| `type` | TEXT | consume / recharge |
| `amount` | REAL | 交易金额 |
| `balance_after` | REAL | 交易后余额 |
| `merchant` | TEXT | 商户名称 |
| `time` | TEXT | 交易时间 |

---

## Run

```bash
# 运行消费终端
uv run terminal.py

# 运行充值发卡站
uv run issuer.py

# 运行单元测试
uv run -m pytest tests/
```

### 消费终端操作流程

1. 通过按键区输入/计算消费金额
2. 点击「确定」→ 显示区提示"请刷卡"
3. 拖拽卡片 JSON 文件到窗口 → 自动扣款并显示结果
4. 结果保持显示直到下次输入操作

### 充值站操作流程

- **发卡**：输入卡号、姓名、初始金额 → 点击「生成卡片」
- **圈存**：输入充值金额 → 拖拽卡片 JSON 文件到窗口 → 自动完成充值

---

## Documentation

详细设计文档：`docs/specs/2026-04-03-design.md`
