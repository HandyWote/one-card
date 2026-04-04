# 校园一卡通模拟系统 — 总览

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Python/tkinter 校园一卡通模拟系统，包含消费终端和充值发卡站两个程序。

**Architecture:** 5 人并行开发，每人负责独立的文件集。数据层（A）最先完成接口定义，其他人基于接口契约并行开发，最后集成。TDD 驱动，每份任务可独立验收。

**Tech Stack:** Python 3.x / tkinter / SQLite / unittest / uv

---

## 子计划索引

| 编号 | 文件 | 负责人 | 内容 |
|------|------|--------|------|
| A | [2026-04-03-plan-A-data-layer.md](2026-04-03-plan-A-data-layer.md) | 人员 A | 数据持久层（database.py + logger.py） |
| B | [2026-04-03-plan-B-card-manager.md](2026-04-03-plan-B-card-manager.md) | 人员 B | 卡片管理逻辑（card_manager.py） |
| C | [2026-04-03-plan-C-calculator.md](2026-04-03-plan-C-calculator.md) | 人员 C | 运算引擎（calculator.py） |
| D | [2026-04-03-plan-D-terminal.md](2026-04-03-plan-D-terminal.md) | 人员 D | 消费终端 GUI（terminal.py） |
| E | [2026-04-03-plan-E-issuer.md](2026-04-03-plan-E-issuer.md) | 人员 E | 充值发卡站（issuer.py + 集成测试） |

---

## 全局约定

### 文件所有权

| 人员 | 负责文件 | 不得修改的文件 |
|------|---------|--------------|
| A（数据层） | `database.py`、`logger.py`、`test_database.py`、`test_logger.py` | 其他所有 |
| B（卡片逻辑） | `card_manager.py`、`test_card_manager.py` | 其他所有 |
| C（运算引擎） | `calculator.py`、`test_calculator.py` | 其他所有 |
| D（消费终端） | `terminal.py` | 其他所有 |
| E（充值发卡站） | `issuer.py`、`tests/test_integration.py`、`data/cards/` | 其他所有 |

### 接口契约（所有人必须遵守）

以下是各模块对外暴露的接口签名。每个人基于此契约开发，集成时签名不可更改。

```python
# database.py — Person A
class Database:
    def __init__(self, db_path: str = 'data/onecard.db'): ...
    def get_connection(self) -> sqlite3.Connection: ...
    def init_tables(self) -> None: ...
    def close(self) -> None: ...

# logger.py — Person A
class Logger:
    def __init__(self, db: Database): ...
    def log_transaction(self, card_id: str, tx_type: str,
                        amount: float, balance_after: float,
                        merchant: str = '') -> None: ...
    def get_transactions(self, card_id: str = None) -> list[dict]: ...
    def get_merchant_summary(self, merchant: str) -> dict: ...

# card_manager.py — Person B
class CardManager:
    def __init__(self, db: Database): ...
    def load_card(self, card_id: str) -> dict | None: ...
    def save_card(self, card_data: dict) -> None: ...
    def export_card(self, card_id: str, export_dir: str) -> str: ...
    def import_card(self, json_path: str) -> dict: ...
    def deduct(self, card_id: str, amount: float) -> tuple[bool, str]: ...
    def recharge(self, card_id: str, amount: float) -> tuple[bool, str]: ...
    def create_card(self, card_id: str, name: str,
                    initial_balance: float) -> dict: ...

# calculator.py — Person C
class Calculator:
    def __init__(self): ...
    def input_digit(self, digit: str) -> str: ...
    def input_operator(self, op: str) -> str: ...
    def backspace(self) -> str: ...
    def calculate(self) -> float: ...
    def get_display(self) -> str: ...
    def clear(self) -> None: ...
```

### 开发顺序与依赖图

```
时间轴 ──────────────────────────────────────────────►

Person A: ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Person B: ░░░████████████████░░░░░░░░░░░░░░░░░░░░░░░░
Person C: ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Person D: ░░░░░░░░░░░░████████████████████░░░░░░░░░░░░
Person E: ░░░░░░░░░░░░░░░░████████████████████░░░░░░░░

A 完成后 → B 可以运行完整测试
A+B+C 完成后 → D 和 E 集成
全部完成后 → E 运行集成测试
```

**关键路径：** A → B → D/E 集成

### 公共约定

- 运行命令统一使用 `uv run`（如 `uv run -m pytest tests/`）
- 数据库路径：`data/onecard.db`，不存在时自动创建 `data/` 目录
- 卡片文件路径：`data/cards/{card_id}`（无后缀）
- 商户名称：固定值，消费终端为 `"一食堂"`，充值站为 `"充值中心"`
- 时间格式：`YYYY-MM-DD HH:MM:SS`
- 流水号格式：`TX` + `YYYYMMDDHHMMSS` + 3位随机数

---

## 集成验收标准

全部子计划完成后，进行以下集成验收：

| # | 验收项 | 操作步骤 | 预期结果 |
|---|--------|---------|---------|
| F-1 | 全部单元测试通过 | `uv run -m pytest tests/ -v` | 所有测试 passed |
| F-2 | 发卡→消费完整流程 | issuer 发卡 → terminal 拖卡消费 | 扣款成功，余额正确 |
| F-3 | 充值→消费流程 | issuer 充值 → terminal 拖卡消费 | 扣款成功，余额为充值后金额 |
| F-4 | 余额不足拒绝 | terminal 输入超额金额 → 拖卡 | 提示余额不足，余额不变 |
| F-5 | 多步运算 | terminal 输入 5.5+8+12 → 确定 → 拖卡 | 扣款 ¥25.50 |
| F-6 | 交易记录完整 | 查看 SQLite transactions 表 | 每笔交易有完整字段 |
| F-7 | 卡片文件无后缀 | `ls data/cards/` | 文件名如 `2024001`（无 .json） |
| F-8 | 两个程序可同时运行 | 同时启动 terminal.py 和 issuer.py | 两个窗口独立运行 |
