# 校园一卡通模拟系统 — 5 人并行实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Python/tkinter 校园一卡通模拟系统，包含消费终端和充值发卡站两个程序。

**Architecture:** 5 人并行开发，每人负责独立的文件集。数据层（A）最先完成接口定义，其他人基于接口契约并行开发，最后集成。TDD 驱动，每份任务可独立验收。

**Tech Stack:** Python 3.x / tkinter / SQLite / unittest / uv

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

### 开发顺序与依赖

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

## 人员 A：数据持久层（database.py + logger.py）

**文件：**
- 创建：`database.py`
- 创建：`logger.py`
- 创建：`tests/test_database.py`
- 创建：`tests/test_logger.py`

**依赖：** 无，可第一个开始。

---

### Task A1: database.py — 数据库连接管理

**Step 1: 写失败测试**

```python
# tests/test_database.py
import unittest
import os
import tempfile
from database import Database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'test.db')
        self.db = Database(self.db_path)

    def tearDown(self):
        self.db.close()
        # 清理临时文件

    def test_init_creates_directory_and_file(self):
        """初始化时应自动创建 data 目录和 .db 文件"""
        self.assertTrue(os.path.exists(self.db_path))

    def test_init_tables_creates_cards_table(self):
        """init_tables 应创建 cards 表"""
        self.db.init_tables()
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cards'"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_init_tables_creates_transactions_table(self):
        """init_tables 应创建 transactions 表"""
        self.db.init_tables()
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_init_tables_idempotent(self):
        """重复调用 init_tables 不应报错"""
        self.db.init_tables()
        self.db.init_tables()  # 不应抛异常

    def test_get_connection_returns_working_connection(self):
        """get_connection 应返回可执行的连接"""
        self.db.init_tables()
        conn = self.db.get_connection()
        result = conn.execute("SELECT 1 + 1").fetchone()
        self.assertEqual(result[0], 2)
```

**Step 2: 运行测试确认失败**

Run: `uv run -m pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'database'`

**Step 3: 实现 database.py**

```python
# database.py
import sqlite3
import os


class Database:
    def __init__(self, db_path: str = 'data/onecard.db'):
        # 自动创建目录
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def get_connection(self) -> sqlite3.Connection:
        return self.conn

    def init_tables(self) -> None:
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS cards (
                card_id    TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                balance    REAL NOT NULL DEFAULT 0,
                status     TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                tx_id         TEXT PRIMARY KEY,
                card_id       TEXT NOT NULL REFERENCES cards(card_id),
                type          TEXT NOT NULL,
                amount        REAL NOT NULL,
                balance_after REAL NOT NULL,
                merchant      TEXT DEFAULT '',
                time          TEXT NOT NULL
            );
        ''')
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
```

**Step 4: 运行测试确认通过**

Run: `uv run -m pytest tests/test_database.py -v`
Expected: 5 passed

**Step 5: 提交**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add database module with SQLite connection and table init"
```

---

### Task A2: logger.py — 交易记录模块

**Step 1: 写失败测试**

```python
# tests/test_logger.py
import unittest
import os
import tempfile
from database import Database
from logger import Logger
from card_manager import CardManager


class TestLogger(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = Database(os.path.join(self.tmpdir, 'test.db'))
        self.db.init_tables()
        self.logger = Logger(self.db)
        self.card_mgr = CardManager(self.db)
        # 创建测试卡片
        self.card_mgr.create_card("T001", "测试用户", 100.0)

    def tearDown(self):
        self.db.close()

    def test_log_transaction_creates_record(self):
        """log_transaction 应在 transactions 表中创建一条记录"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0, "一食堂")
        txs = self.logger.get_transactions("T001")
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['amount'], 10.0)
        self.assertEqual(txs[0]['balance_after'], 90.0)

    def test_log_transaction_generates_unique_tx_id(self):
        """每次 log_transaction 应生成不同的 tx_id"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        self.logger.log_transaction("T001", "consume", 5.0, 85.0)
        txs = self.logger.get_transactions("T001")
        self.assertNotEqual(txs[0]['tx_id'], txs[1]['tx_id'])

    def test_log_transaction_tx_id_starts_with_TX(self):
        """流水号应以 TX 开头"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        txs = self.logger.get_transactions("T001")
        self.assertTrue(txs[0]['tx_id'].startswith('TX'))

    def test_get_transactions_filter_by_card_id(self):
        """按卡号过滤交易记录"""
        self.card_mgr.create_card("T002", "用户B", 50.0)
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        self.logger.log_transaction("T002", "recharge", 20.0, 70.0)
        txs = self.logger.get_transactions("T001")
        self.assertEqual(len(txs), 1)

    def test_get_transactions_all(self):
        """不传 card_id 时返回所有记录"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        self.logger.log_transaction("T001", "consume", 5.0, 85.0)
        txs = self.logger.get_transactions()
        self.assertEqual(len(txs), 2)

    def test_get_merchant_summary(self):
        """商户汇总统计"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0, "一食堂")
        self.logger.log_transaction("T001", "consume", 5.0, 85.0, "一食堂")
        self.logger.log_transaction("T001", "consume", 3.0, 82.0, "校内超市")
        summary = self.logger.get_merchant_summary("一食堂")
        self.assertEqual(summary['total_amount'], 15.0)
        self.assertEqual(summary['count'], 2)

    def test_log_recharge(self):
        """充值记录应有 type='recharge'"""
        self.logger.log_transaction("T001", "recharge", 50.0, 150.0, "充值中心")
        txs = self.logger.get_transactions("T001")
        self.assertEqual(txs[0]['type'], 'recharge')
```

**Step 2: 运行测试确认失败**

Run: `uv run -m pytest tests/test_logger.py -v`
Expected: FAIL — 依赖 card_manager.py（Person B）的 create_card 方法

> **注意：** 此测试依赖 Person B 的 `card_manager.py`。可先与 B 协调一个最小实现（仅 `create_card` 方法），或在测试中直接操作数据库绕过。推荐直接插入测试数据：

```python
# 替代方案：绕过 card_manager
def setUp(self):
    ...
    self.db.get_connection().execute(
        "INSERT INTO cards VALUES (?, ?, ?, ?, ?)",
        ("T001", "测试用户", 100.0, "active", "2026-04-01")
    )
    self.db.get_connection().commit()
```

**Step 3: 实现 logger.py**

```python
# logger.py
import datetime
import random


class Logger:
    def __init__(self, db):
        self.db = db

    def _generate_tx_id(self) -> str:
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        rand_part = random.randint(100, 999)
        return f"TX{now}{rand_part}"

    def log_transaction(self, card_id: str, tx_type: str,
                        amount: float, balance_after: float,
                        merchant: str = '') -> None:
        tx_id = self._generate_tx_id()
        time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tx_id, card_id, tx_type, amount, balance_after, merchant, time_str)
        )
        conn.commit()

    def get_transactions(self, card_id: str = None) -> list[dict]:
        conn = self.db.get_connection()
        original_factory = conn.row_factory
        conn.row_factory = sqlite3.Row
        try:
            if card_id:
                rows = conn.execute(
                    "SELECT tx_id, card_id, type, amount, balance_after, merchant, time "
                    "FROM transactions WHERE card_id = ? ORDER BY time",
                    (card_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT tx_id, card_id, type, amount, balance_after, merchant, time "
                    "FROM transactions ORDER BY time"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.row_factory = original_factory

    def get_merchant_summary(self, merchant: str) -> dict:
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0), COUNT(*) "
            "FROM transactions WHERE merchant = ?",
            (merchant,)
        ).fetchone()
        return {
            'total_amount': row[0],
            'count': row[1]
        }
```

**Step 4: 运行测试确认通过**

Run: `uv run -m pytest tests/test_logger.py -v`
Expected: 7 passed

**Step 5: 提交**

```bash
git add logger.py tests/test_logger.py
git commit -m "feat: add logger module for transaction recording and queries"
```

---

### 验收标准 — 人员 A

| # | 验收项 | 验证命令/操作 | 预期结果 |
|---|--------|-------------|---------|
| A-1 | database.py 模块存在且可导入 | `uv run -c "from database import Database; print('OK')"` | 输出 `OK` |
| A-2 | 自动建表 | `uv run -c "from database import Database; d=Database('/tmp/test.db'); d.init_tables(); print('OK')"` | 输出 `OK`，无报错 |
| A-3 | database 单元测试全部通过 | `uv run -m pytest tests/test_database.py -v` | 5 passed |
| A-4 | logger.py 模块存在且可导入 | `uv run -c "from logger import Logger; print('OK')"` | 输出 `OK` |
| A-5 | logger 单元测试全部通过 | `uv run -m pytest tests/test_logger.py -v` | 7 passed |
| A-6 | 数据库文件可打开查看 | `uv run -c "import sqlite3; c=sqlite3.connect('/tmp/test.db'); print(c.execute('SELECT name FROM sqlite_master').fetchall())"` | 包含 cards 和 transactions 两个表 |

---

## 人员 B：卡片管理逻辑（card_manager.py）

**文件：**
- 创建：`card_manager.py`
- 创建：`tests/test_card_manager.py`

**依赖：** `database.py`（Person A 的接口）。B 可以先基于接口签名开发，用 mock 或临时 stub 替代 Database。

---

### Task B1: card_manager.py — 基础 CRUD

**Step 1: 写失败测试**

```python
# tests/test_card_manager.py
import unittest
import os
import tempfile
import json
from database import Database
from card_manager import CardManager


class TestCardManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cards_dir = os.path.join(self.tmpdir, 'cards')
        os.makedirs(self.cards_dir, exist_ok=True)
        db_path = os.path.join(self.tmpdir, 'test.db')
        self.db = Database(db_path)
        self.db.init_tables()
        self.mgr = CardManager(self.db)

    def tearDown(self):
        self.db.close()

    # --- 基础 CRUD ---

    def test_create_card(self):
        """创建卡片应写入数据库"""
        card = self.mgr.create_card("2024001", "张三", 100.0)
        self.assertEqual(card['card_id'], "2024001")
        self.assertEqual(card['name'], "张三")
        self.assertEqual(card['balance'], 100.0)
        self.assertEqual(card['status'], "active")

    def test_create_card_exists(self):
        """重复卡号应返回 None 或抛异常"""
        self.mgr.create_card("2024001", "张三", 100.0)
        result = self.mgr.create_card("2024001", "李四", 50.0)
        # 重复创建应该失败
        self.assertIsNone(result)  # 或者测试抛异常

    def test_load_card(self):
        """加载存在的卡片应返回数据"""
        self.mgr.create_card("2024001", "张三", 100.0)
        card = self.mgr.load_card("2024001")
        self.assertIsNotNone(card)
        self.assertEqual(card['name'], "张三")
        self.assertEqual(card['balance'], 100.0)

    def test_load_card_not_found(self):
        """加载不存在的卡片应返回 None"""
        card = self.mgr.load_card("9999999")
        self.assertIsNone(card)

    def test_save_card(self):
        """save_card 应更新数据库中的卡片"""
        self.mgr.create_card("2024001", "张三", 100.0)
        self.mgr.save_card({
            'card_id': '2024001', 'name': '张三',
            'balance': 80.0, 'status': 'active',
            'created_at': '2026-04-01'
        })
        card = self.mgr.load_card("2024001")
        self.assertEqual(card['balance'], 80.0)

    # --- 扣款 ---

    def test_deduct_success(self):
        """余额充足时扣款成功"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.deduct("2024001", 30.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 70.0)

    def test_deduct_insufficient_balance(self):
        """余额不足时扣款失败"""
        self.mgr.create_card("2024001", "张三", 10.0)
        success, msg = self.mgr.deduct("2024001", 50.0)
        self.assertFalse(success)
        # 余额不变
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 10.0)

    def test_deduct_exact_balance(self):
        """余额恰好等于扣款金额时应成功"""
        self.mgr.create_card("2024001", "张三", 50.0)
        success, msg = self.mgr.deduct("2024001", 50.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 0.0)

    def test_deduct_negative_amount(self):
        """扣款金额为负数时应失败"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.deduct("2024001", -10.0)
        self.assertFalse(success)

    def test_deduct_card_not_found(self):
        """卡片不存在时扣款失败"""
        success, msg = self.mgr.deduct("9999999", 10.0)
        self.assertFalse(success)

    # --- 充值 ---

    def test_recharge_success(self):
        """充值成功"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.recharge("2024001", 50.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 150.0)

    def test_recharge_negative_amount(self):
        """充值金额为负数时应失败"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.recharge("2024001", -10.0)
        self.assertFalse(success)

    def test_recharge_card_not_found(self):
        """卡片不存在时充值失败"""
        success, msg = self.mgr.recharge("9999999", 50.0)
        self.assertFalse(success)

    # --- JSON 导入导出 ---

    def test_export_card_creates_file(self):
        """导出应创建卡片文件（文件名即卡号，无后缀）"""
        self.mgr.create_card("2024001", "张三", 100.0)
        path = self.mgr.export_card("2024001", self.cards_dir)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.path.basename(path), "2024001")

    def test_export_card_json_content(self):
        """导出文件内容应为合法 JSON"""
        self.mgr.create_card("2024001", "张三", 100.0)
        path = self.mgr.export_card("2024001", self.cards_dir)
        with open(path, 'r') as f:
            data = json.load(f)
        self.assertEqual(data['card_id'], "2024001")
        self.assertEqual(data['name'], "张三")

    def test_import_card(self):
        """导入应将 JSON 文件写入数据库"""
        # 先手动创建一个 JSON 文件
        card_file = os.path.join(self.cards_dir, "2024002")
        with open(card_file, 'w') as f:
            json.dump({
                "card_id": "2024002", "name": "李四",
                "balance": 200.0, "status": "active",
                "created_at": "2026-04-02"
            }, f)
        card = self.mgr.import_card(card_file)
        self.assertEqual(card['card_id'], "2024002")
        # 验证数据库中有此卡
        db_card = self.mgr.load_card("2024002")
        self.assertIsNotNone(db_card)

    def test_import_card_updates_existing(self):
        """导入已存在的卡应更新数据库记录"""
        self.mgr.create_card("2024001", "张三", 100.0)
        # 创建新的 JSON 文件，余额不同
        card_file = os.path.join(self.cards_dir, "2024001")
        with open(card_file, 'w') as f:
            json.dump({
                "card_id": "2024001", "name": "张三",
                "balance": 300.0, "status": "active",
                "created_at": "2026-04-01"
            }, f)
        card = self.mgr.import_card(card_file)
        # 数据库余额不应被覆盖（以 SQLite 为准）
        # 但 import_card 的职责是：读 JSON → 更新 SQLite
        db_card = self.mgr.load_card("2024001")
        self.assertEqual(db_card['balance'], 300.0)
```

**Step 2: 运行测试确认失败**

Run: `uv run -m pytest tests/test_card_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: 实现 card_manager.py**

```python
# card_manager.py
import json
import os


class CardManager:
    def __init__(self, db):
        self.db = db

    def load_card(self, card_id: str) -> dict | None:
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT card_id, name, balance, status, created_at FROM cards WHERE card_id = ?",
            (card_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def save_card(self, card_data: dict) -> None:
        conn = self.db.get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO cards (card_id, name, balance, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (card_data['card_id'], card_data['name'], card_data['balance'],
             card_data['status'], card_data['created_at'])
        )
        conn.commit()

    def export_card(self, card_id: str, export_dir: str) -> str:
        card = self.load_card(card_id)
        if card is None:
            raise ValueError(f"Card {card_id} not found")
        os.makedirs(export_dir, exist_ok=True)
        path = os.path.join(export_dir, card_id)
        with open(path, 'w') as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        return path

    def import_card(self, json_path: str) -> dict:
        with open(json_path, 'r') as f:
            card_data = json.load(f)
        self.save_card(card_data)
        return self.load_card(card_data['card_id'])

    def deduct(self, card_id: str, amount: float) -> tuple[bool, str]:
        if amount <= 0:
            return False, "扣款金额必须大于零"
        card = self.load_card(card_id)
        if card is None:
            return False, "卡片不存在"
        if card['status'] != 'active':
            return False, "卡片已挂失"
        if card['balance'] < amount:
            return False, f"余额不足，当前余额 {card['balance']:.2f} 元"
        new_balance = card['balance'] - amount
        card['balance'] = new_balance
        self.save_card(card)
        return True, f"扣款成功，余额 {new_balance:.2f} 元"

    def recharge(self, card_id: str, amount: float) -> tuple[bool, str]:
        if amount <= 0:
            return False, "充值金额必须大于零"
        card = self.load_card(card_id)
        if card is None:
            return False, "卡片不存在"
        new_balance = card['balance'] + amount
        card['balance'] = new_balance
        self.save_card(card)
        return True, f"充值成功，余额 {new_balance:.2f} 元"

    def create_card(self, card_id: str, name: str,
                    initial_balance: float) -> dict | None:
        if self.load_card(card_id) is not None:
            return None
        import datetime
        card_data = {
            'card_id': card_id,
            'name': name,
            'balance': initial_balance,
            'status': 'active',
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d')
        }
        self.save_card(card_data)
        return self.load_card(card_id)
```

**Step 4: 运行测试确认通过**

Run: `uv run -m pytest tests/test_card_manager.py -v`
Expected: 15 passed

**Step 5: 提交**

```bash
git add card_manager.py tests/test_card_manager.py
git commit -m "feat: add card manager with CRUD, deduct, recharge, JSON import/export"
```

---

### 验收标准 — 人员 B

| # | 验收项 | 验证命令/操作 | 预期结果 |
|---|--------|-------------|---------|
| B-1 | 模块可导入 | `uv run -c "from card_manager import CardManager; print('OK')"` | 输出 `OK` |
| B-2 | 单元测试全部通过 | `uv run -m pytest tests/test_card_manager.py -v` | 15 passed |
| B-3 | 创建卡片后数据库有记录 | 运行测试后检查 `/tmp` 下测试数据库 | cards 表有数据 |
| B-4 | 导出文件无后缀 | 运行 `test_export_card_creates_file` 后 `ls` | 文件名是 `2024001`（无 .json） |
| B-5 | 余额不足扣款失败 | `test_deduct_insufficient_balance` | passed，余额不变 |
| B-6 | 充值后余额增加 | `test_recharge_success` | passed，100→150 |

---

## 人员 C：运算引擎（calculator.py）

**文件：**
- 创建：`calculator.py`
- 创建：`tests/test_calculator.py`

**依赖：** 无，完全独立模块，可第一个开始。

---

### Task C1: calculator.py — 辅助运算模块

**Step 1: 写失败测试**

```python
# tests/test_calculator.py
import unittest
from calculator import Calculator


class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_input_single_digit(self):
        """输入单个数字应正确显示"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_digit('0'), '0')

    def test_input_multi_digit(self):
        """连续输入数字应拼接"""
        self.assertEqual(self.calc.input_digit('1'), '1')
        self.assertEqual(self.calc.input_digit('2'), '12')
        self.assertEqual(self.calc.input_digit('3'), '123')

    def test_input_decimal_point(self):
        """输入小数点"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_digit('.'), '5.')
        self.assertEqual(self.calc.input_digit('5'), '5.5')

    def test_no_double_decimal(self):
        """不应允许输入两个小数点"""
        self.calc.input_digit('5')
        self.calc.input_digit('.')
        result = self.calc.input_digit('.')
        self.assertEqual(result, '5.')

    def test_input_operator(self):
        """输入运算符应锁定当前数字"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_operator('+'), '5 +')
        self.assertEqual(self.calc.input_digit('3'), '3')

    def test_backspace(self):
        """回退应删除最后一位"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_digit('3'), '53')
        self.assertEqual(self.calc.backspace(), '5')
        self.assertEqual(self.calc.backspace(), '0')

    def test_clear(self):
        """清除应重置所有状态"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('3')
        self.calc.clear()
        self.assertEqual(self.calc.get_display(), '')

    def test_calculate_single_number(self):
        """只输入一个数字直接计算应返回该数"""
        self.calc.input_digit('25.5')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 25.5)

    def test_calculate_addition(self):
        """5.5 + 8.0 = 13.5"""
        self.calc.input_digit('5.5')
        self.calc.input_operator('+')
        self.calc.input_digit('8.0')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 13.5)

    def test_calculate_subtraction(self):
        """20 - 7.5 = 12.5"""
        self.calc.input_digit('20')
        self.calc.input_operator('-')
        self.calc.input_digit('7.5')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 12.5)

    def test_calculate_multiplication(self):
        """3 × 4 = 12"""
        self.calc.input_digit('3')
        self.calc.input_operator('×')
        self.calc.input_digit('4')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 12.0)

    def test_calculate_sequential(self):
        """按输入顺序计算：5 + 8.0 + 12.0 = 25.0（不是数学优先级）"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('8.0')
        self.calc.input_operator('+')
        self.calc.input_digit('12.0')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 25.0)

    def test_calculate_sequential_mixed(self):
        """10 + 3 × 2 = 26（按顺序：先 10+3=13，再 13×2=26）"""
        self.calc.input_digit('10')
        self.calc.input_operator('+')
        self.calc.input_digit('3')
        self.calc.input_operator('×')
        self.calc.input_digit('2')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 26.0)

    def test_calculate_then_input_clears(self):
        """计算完成后输入新数字应清除旧结果"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('3')
        self.calc.calculate()  # 8
        display = self.calc.input_digit('1')
        self.assertEqual(display, '1')

    def test_get_display(self):
        """get_display 应返回当前输入内容"""
        self.assertEqual(self.calc.get_display(), '')
        self.calc.input_digit('5')
        self.assertEqual(self.calc.get_display(), '5')
        self.calc.input_operator('+')
        self.assertEqual(self.calc.get_display(), '5 +')

    def test_calculate_no_input(self):
        """无输入时计算应返回 0"""
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 0.0)

    def test_calculate_operator_only(self):
        """只输入运算符没有第二操作数时应返回第一操作数"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 5.0)

    def test_zero_amount(self):
        """输入 0 应正常工作"""
        self.calc.input_digit('0')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 0.0)
```

**Step 2: 运行测试确认失败**

Run: `uv run -m pytest tests/test_calculator.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: 实现 calculator.py**

```python
# calculator.py


class Calculator:
    def __init__(self):
        self.expression = []    # [数字, 运算符, 数字, ...]
        self.current_num = ''   # 当前正在输入的数字字符串
        self._result = None     # calculate() 的结果

    def input_digit(self, digit: str) -> str:
        if self._result is not None:
            # 计算完成后输入新数字，清除旧结果
            self.clear()
        if digit == '.' and '.' in self.current_num:
            return self.get_display()
        self.current_num += digit
        return self.get_display()

    def input_operator(self, op: str) -> str:
        if self._result is not None:
            self.clear()
        if self.current_num == '' and not self.expression:
            return self.get_display()
        if self.current_num != '':
            self.expression.append(float(self.current_num))
            self.current_num = ''
        self.expression.append(op)
        return self.get_display()

    def backspace(self) -> str:
        if self.current_num:
            self.current_num = self.current_num[:-1]
        return self.get_display()

    def calculate(self) -> float:
        if self.current_num != '':
            self.expression.append(float(self.current_num))
            self.current_num = ''

        if not self.expression:
            return 0.0

        # 取第一个数字作为初始值
        result = self.expression[0]
        # 按输入顺序计算：[数字, 运算符, 数字, 运算符, 数字, ...]
        i = 1
        while i < len(self.expression):
            op = self.expression[i]
            if i + 1 < len(self.expression):
                next_num = self.expression[i + 1]
            else:
                next_num = result  # 运算符后没有数字，返回当前值
            if op == '+':
                result = result + next_num
            elif op == '-':
                result = result - next_num
            elif op == '×':
                result = result * next_num
            i += 2

        self._result = result
        return result

    def get_display(self) -> str:
        parts = []
        if self.expression:
            parts.append(str(self.expression[0]).rstrip('0').rstrip('.'))
            i = 1
            while i < len(self.expression):
                parts.append(self.expression[i])
                i += 1
                if i < len(self.expression):
                    parts.append(
                        str(self.expression[i]).rstrip('0').rstrip('.')
                    )
                i += 1
        if self.current_num:
            parts.append(self.current_num)
        return ' '.join(parts)

    def clear(self) -> None:
        self.expression = []
        self.current_num = ''
        self._result = None
```

**Step 4: 运行测试确认通过**

Run: `uv run -m pytest tests/test_calculator.py -v`
Expected: 17 passed

**Step 5: 提交**

```bash
git add calculator.py tests/test_calculator.py
git commit -m "feat: add calculator with sequential evaluation (+, -, ×)"
```

---

### 验收标准 — 人员 C

| # | 验收项 | 验证命令/操作 | 预期结果 |
|---|--------|-------------|---------|
| C-1 | 模块可导入 | `uv run -c "from calculator import Calculator; print('OK')"` | 输出 `OK` |
| C-2 | 单元测试全部通过 | `uv run -m pytest tests/test_calculator.py -v` | 17 passed |
| C-3 | 加法正确 | 测试 `5.5 + 8.0` | 13.5 |
| C-4 | 减法正确 | 测试 `20 - 7.5` | 12.5 |
| C-5 | 乘法正确 | 测试 `3 × 4` | 12.0 |
| C-6 | 按输入顺序计算 | 测试 `10 + 3 × 2` | 26.0（非 16） |
| C-7 | 连续多步运算 | 测试 `5 + 8 + 12` | 25.0 |
| C-8 | 计算后输入清空 | `calculate()` 后 `input_digit('1')` | 显示 `1` |

---

## 人员 D：消费终端 GUI（terminal.py）

**文件：**
- 创建：`terminal.py`

**依赖：** `calculator.py`（C）、`card_manager.py`（B）、`logger.py`（A）、`database.py`（A）。D 可以先搭建 GUI 布局，后续集成。

---

### Task D1: terminal.py — 消费终端完整实现

**Step 1: 搭建 GUI 框架**

创建 `terminal.py`，实现以下功能：

**界面布局（4 个区域）：**

```
┌─────────────────────────────────────┐
│           显示区（大字体）            │  ← StringVar 绑定
│            ¥ 25.50                  │
├─────────────────────────────────────┤
│         结果区（交易反馈）            │  ← Label
│  扣款成功，张三，扣款 25.50 元       │
├───────┬───────┬───────┬─────────────┤
│   7   │   8   │   9   │    回退     │
├───────┼───────┼───────┼─────────────┤
│   4   │   5   │   6   │     +      │
├───────┼───────┼───────┼─────────────┤
│   1   │   2   │   3   │     -      │
├───────┼───────┼───────┼─────────────┤
│   0   │   .   │   ×   │    清除     │
├───────┴───────┼───────┴─────────────┤
│     清除      │       确定          │
└───────────────┴─────────────────────┘
```

**状态机（4 个状态）：**

```python
STATE_INPUT = 'input'       # 输入金额
STATE_WAITING = 'waiting'   # 等待刷卡（确定后）
STATE_RESULT = 'result'     # 显示结果（刷卡后）
```

**核心实现要点：**

1. **显示区**：大字体（如 24pt），绑定 `StringVar`，实时反映 Calculator 的 `get_display()`
2. **结果区**：初始隐藏/为空，扣款成功/失败后显示文本
3. **按键区**：每个按钮绑定对应处理函数
   - 数字键 0-9、`.`：调用 `calc.input_digit()`
   - `+`、`-`、`×`：调用 `calc.input_operator()`
   - 回退：调用 `calc.backspace()`
   - 清除：调用 `calc.clear()`，重置到 `STATE_INPUT`
   - 确定：调用 `calc.calculate()`，切换到 `STATE_WAITING`，显示区显示"¥ XX.XX，请刷卡"
4. **拖放区**：整个窗口绑定 `TkinterDnD` 或使用文件对话框替代
   - 当状态为 `STATE_WAITING` 时，接受拖入的卡片文件
   - 读取文件 → `card_mgr.import_card()` → `card_mgr.deduct()` → `logger.log_transaction()` → `card_mgr.export_card()`
   - 成功：结果显示"扣款成功，{姓名}，扣款 {金额} 元，余额 {余额} 元"
   - 失败：结果显示错误信息
   - 切换到 `STATE_RESULT`
5. **结果保持**：`STATE_RESULT` 时，按数字键自动清除结果并切换到 `STATE_INPUT`

**拖放实现方案（优先使用 tkinterdnd2）：**

```python
# 尝试导入 tkinterdnd2，若不可用则回退到按钮选择文件
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
```

若无 `tkinterdnd2`，在 `STATE_WAITING` 状态下额外显示一个「选择卡片」按钮作为替代。

**Step 2: 完整实现代码**

```python
# terminal.py
import tkinter as tk
from tkinter import font as tkfont
import os

from database import Database
from card_manager import CardManager
from calculator import Calculator
from logger import Logger

MERCHANT = "一食堂"
DB_PATH = 'data/onecard.db'
CARDS_DIR = 'data/cards'

STATE_INPUT = 'input'
STATE_WAITING = 'waiting'
STATE_RESULT = 'result'


class TerminalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("校园一卡通 — 消费终端")
        self.root.resizable(False, False)

        self.state = STATE_INPUT
        self.calculator = Calculator()
        self.amount = 0.0

        # 初始化数据库和模块
        self.db = Database(DB_PATH)
        self.db.init_tables()
        self.card_mgr = CardManager(self.db)
        self.logger = Logger(self.db)

        self._build_ui()

        # 尝试启用拖放
        try:
            from tkinterdnd2 import DND_FILES
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
        except ImportError:
            # 创建"选择卡片"按钮作为替代
            pass

    def _build_ui(self):
        # 显示区
        self.display_var = tk.StringVar(value='')
        display_font = tkfont.Font(size=28, weight='bold')
        tk.Label(self.root, textvariable=self.display_var,
                 font=display_font, anchor='e', padx=20, pady=15,
                 relief='sunken', width=16).pack(fill='x', padx=10, pady=(10, 5))

        # 结果区
        self.result_var = tk.StringVar(value='')
        tk.Label(self.root, textvariable=self.result_var,
                 font=('Arial', 12), fg='green', anchor='w', padx=10,
                 wraplength=280, height=2).pack(fill='x', padx=10)

        # 按键区
        keypad = tk.Frame(self.root)
        keypad.pack(padx=10, pady=10)

        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2), ('回退', 0, 3),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('+', 1, 3),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2), ('-', 2, 3),
            ('0', 3, 0), ('.', 3, 1), ('×', 3, 2), ('清除', 3, 3),
        ]

        for text, row, col in buttons:
            btn = tk.Button(keypad, text=text, width=6, height=2,
                            font=('Arial', 14))
            btn.grid(row=row, column=col, padx=2, pady=2)
            if text in '0123456789.':
                btn.config(command=lambda t=text: self._on_digit(t))
            elif text in '+-×':
                btn.config(command=lambda t=text: self._on_operator(t))
            elif text == '回退':
                btn.config(command=self._on_backspace)
            elif text == '清除':
                btn.config(command=self._on_clear)

        # 底部两行
        tk.Button(keypad, text='清除', width=14, height=2,
                  font=('Arial', 14), command=self._on_clear
                  ).grid(row=4, column=0, columnspan=2, padx=2, pady=2)
        tk.Button(keypad, text='确定', width=14, height=2,
                  font=('Arial', 14, 'bold'),
                  command=self._on_confirm
                  ).grid(row=4, column=2, columnspan=2, padx=2, pady=2)

    def _on_digit(self, digit):
        if self.state == STATE_RESULT:
            self.result_var.set('')
            self.calculator.clear()
            self.state = STATE_INPUT
        if self.state in (STATE_INPUT, STATE_RESULT):
            display = self.calculator.input_digit(digit)
            self.display_var.set(display)

    def _on_operator(self, op):
        if self.state == STATE_RESULT:
            self.result_var.set('')
            self.calculator.clear()
            self.state = STATE_INPUT
        if self.state == STATE_INPUT:
            display = self.calculator.input_operator(op)
            self.display_var.set(display)

    def _on_backspace(self):
        if self.state == STATE_INPUT:
            display = self.calculator.backspace()
            self.display_var.set(display)

    def _on_clear(self):
        self.calculator.clear()
        self.display_var.set('')
        self.result_var.set('')
        self.state = STATE_INPUT

    def _on_confirm(self):
        if self.state == STATE_RESULT:
            self.result_var.set('')
            self.calculator.clear()
            self.state = STATE_INPUT
            return
        if self.state != STATE_INPUT:
            return
        self.amount = self.calculator.calculate()
        if self.amount <= 0:
            self.result_var.set('请先输入金额')
            return
        self.display_var.set(f'¥ {self.amount:.2f}  请刷卡')
        self.state = STATE_WAITING

    def _on_drop(self, event):
        if self.state != STATE_WAITING:
            return
        filepath = event.data.strip('{}')
        self._process_card(filepath)

    def _process_card(self, filepath):
        try:
            card_data = self.card_mgr.import_card(filepath)
            if card_data is None:
                self.result_var.set('卡片文件无效')
                self.state = STATE_RESULT
                return
            card_id = card_data['card_id']
            card = self.card_mgr.load_card(card_id)
            if card is None:
                self.result_var.set('卡片不存在')
                self.state = STATE_RESULT
                return

            # 执行扣款
            success, msg = self.card_mgr.deduct(card_id, self.amount)
            if success:
                card = self.card_mgr.load_card(card_id)
                self.logger.log_transaction(
                    card_id, 'consume', self.amount,
                    card['balance'], MERCHANT
                )
                self.card_mgr.export_card(card_id, CARDS_DIR)
                self.result_var.set(
                    f"扣款成功，{card['name']}，扣款 ¥{self.amount:.2f} 元，"
                    f"余额 ¥{card['balance']:.2f} 元"
                )
            else:
                self.result_var.set(f"扣款失败：{msg}")
            self.state = STATE_RESULT
        except Exception as e:
            self.result_var.set(f'错误：{e}')
            self.state = STATE_RESULT

    def cleanup(self):
        self.db.close()


def main():
    root = tk.Tk()
    app = TerminalApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()


if __name__ == '__main__':
    main()
```

**Step 3: 手动验收测试**

见下方验收标准。

**Step 4: 提交**

```bash
git add terminal.py
git commit -m "feat: add terminal GUI with keypad, drag-drop, and state machine"
```

---

### 验收标准 — 人员 D

| # | 验收项 | 操作步骤 | 预期结果 |
|---|--------|---------|---------|
| D-1 | 程序可启动 | `uv run terminal.py` | 窗口正常弹出，显示按键区 |
| D-2 | 数字输入 | 依次点 5、.、5 | 显示区显示 `5.5` |
| D-3 | 加法运算 | 点 5、+、8、=（确定） | 显示 `¥ 13.00  请刷卡` |
| D-4 | 确定后拖卡 | 在 A 的帮助下准备卡片文件，拖入窗口 | 显示扣款结果或余额不足 |
| D-5 | 扣款成功 | 余额 100，扣 30 | 显示"扣款成功...余额 ¥70.00" |
| D-6 | 余额不足 | 余额 10，扣 50 | 显示"余额不足"，SQLite 余额不变 |
| D-7 | 清除重置 | 扣款后点清除 | 显示区和结果区清空 |
| D-8 | 结果保持 | 扣款成功后不操作 | 结果持续显示 |
| D-9 | 下次输入自动清除 | 扣款后按任意数字键 | 结果消失，显示新数字 |
| D-10 | 窗口关闭不报错 | 关闭窗口 | 正常退出，无报错 |

---

## 人员 E：充值发卡站 GUI（issuer.py + 集成测试）

**文件：**
- 创建：`issuer.py`
- 创建：`tests/test_integration.py`
- 创建：`data/cards/`（示例卡片）

**依赖：** `card_manager.py`（B）、`logger.py`（A）、`database.py`（A）。E 可以先搭建 GUI 布局。

---

### Task E1: issuer.py — 充值发卡站完整实现

**Step 1: 搭建 GUI 框架**

创建 `issuer.py`，实现两个选项卡：

**发卡选项卡：**
```
┌──────────────────────────────┐
│  卡号：[________________]    │
│  姓名：[________________]    │
│  初始余额：[____________]    │
│                              │
│      [  生成卡片  ]          │
│                              │
│  状态：发卡成功！            │
└──────────────────────────────┘
```

**充值选项卡：**
```
┌──────────────────────────────┐
│  充值金额：[____________]    │
│                              │
│      [ 选择卡片文件 ]         │
│  或拖拽卡片文件到此处        │
│                              │
│  状态：充值成功！            │
└──────────────────────────────┘
```

**核心实现要点：**

1. 使用 `ttk.Notebook` 创建两个选项卡
2. **发卡**：读取输入 → `card_mgr.create_card()` → `card_mgr.export_card()` → 显示结果
3. **充值**：
   - 状态机：`input_amount` → `waiting_card` → `result`
   - 输入金额 → 进入等待刷卡状态
   - 拖入卡片 / 选择文件 → `card_mgr.import_card()` → `card_mgr.recharge()` → `logger.log_transaction()` → `card_mgr.export_card()` → 显示结果
4. 拖放方案与 terminal.py 相同（优先 tkinterdnd2，回退按钮选择）

**Step 2: 完整实现代码**

```python
# issuer.py
import tkinter as tk
from tkinter import ttk, font as tkfont, filedialog
import os

from database import Database
from card_manager import CardManager
from logger import Logger

MERCHANT = "充值中心"
DB_PATH = 'data/onecard.db'
CARDS_DIR = 'data/cards'

STATE_INPUT = 'input'
STATE_WAITING = 'waiting'
STATE_RESULT = 'result'


class IssuerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("校园一卡通 — 充值发卡站")
        self.root.resizable(False, False)

        self.recharge_state = STATE_INPUT
        self.recharge_amount = 0.0

        # 初始化数据库
        self.db = Database(DB_PATH)
        self.db.init_tables()
        self.card_mgr = CardManager(self.db)
        self.logger = Logger(self.db)

        self._build_ui()

        # 尝试启用拖放（充值选项卡）
        try:
            from tkinterdnd2 import DND_FILES
            self.recharge_frame.drop_target_register(DND_FILES)
            self.recharge_frame.dnd_bind('<<Drop>>', self._on_recharge_drop)
        except ImportError:
            pass

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(padx=10, pady=10, fill='both', expand=True)

        # === 发卡选项卡 ===
        create_frame = ttk.Frame(notebook, padding=20)
        notebook.add(create_frame, text='发卡')

        ttk.Label(create_frame, text='卡号：').grid(row=0, column=0, sticky='w', pady=5)
        self.entry_card_id = ttk.Entry(create_frame, width=20)
        self.entry_card_id.grid(row=0, column=1, pady=5)

        ttk.Label(create_frame, text='姓名：').grid(row=1, column=0, sticky='w', pady=5)
        self.entry_name = ttk.Entry(create_frame, width=20)
        self.entry_name.grid(row=1, column=1, pady=5)

        ttk.Label(create_frame, text='初始余额：').grid(row=2, column=0, sticky='w', pady=5)
        self.entry_balance = ttk.Entry(create_frame, width=20)
        self.entry_balance.grid(row=2, column=1, pady=5)

        ttk.Button(create_frame, text='生成卡片',
                   command=self._on_create_card).grid(row=3, column=0,
                   columnspan=2, pady=15)

        self.create_status = tk.StringVar(value='')
        ttk.Label(create_frame, textvariable=self.create_status,
                  font=('Arial', 11)).grid(row=4, column=0, columnspan=2)

        # === 充值选项卡 ===
        self.recharge_frame = ttk.Frame(notebook, padding=20)
        notebook.add(self.recharge_frame, text='充值')

        ttk.Label(self.recharge_frame, text='充值金额：').grid(
            row=0, column=0, sticky='w', pady=5)
        self.entry_recharge_amount = ttk.Entry(self.recharge_frame, width=20)
        self.entry_recharge_amount.grid(row=0, column=1, pady=5)

        ttk.Button(self.recharge_frame, text='确定金额',
                   command=self._on_recharge_confirm).grid(row=1, column=0,
                   columnspan=2, pady=5)

        ttk.Button(self.recharge_frame, text='选择卡片文件',
                   command=self._on_select_card).grid(row=2, column=0,
                   columnspan=2, pady=5)

        ttk.Label(self.recharge_frame, text='（或将卡片文件拖拽到此窗口）',
                  foreground='gray').grid(row=3, column=0, columnspan=2, pady=5)

        self.recharge_status = tk.StringVar(value='')
        ttk.Label(self.recharge_frame, textvariable=self.recharge_status,
                  font=('Arial', 11), wraplength=250).grid(
            row=4, column=0, columnspan=2, pady=10)

    def _on_create_card(self):
        card_id = self.entry_card_id.get().strip()
        name = self.entry_name.get().strip()
        balance_str = self.entry_balance.get().strip()

        if not card_id or not name:
            self.create_status.set('请填写卡号和姓名')
            return
        try:
            balance = float(balance_str)
            if balance < 0:
                raise ValueError
        except ValueError:
            self.create_status.set('请输入有效的金额')
            return

        card = self.card_mgr.create_card(card_id, name, balance)
        if card is None:
            self.create_status.set(f'卡号 {card_id} 已存在')
            return

        try:
            path = self.card_mgr.export_card(card_id, CARDS_DIR)
            self.create_status.set(
                f'发卡成功！卡号 {card_id}，姓名 {name}，余额 ¥{balance:.2f} 元\n'
                f'卡片文件：{path}'
            )
        except Exception as e:
            self.create_status.set(f'导出失败：{e}')

    def _on_recharge_confirm(self):
        amount_str = self.entry_recharge_amount.get().strip()
        try:
            self.recharge_amount = float(amount_str)
            if self.recharge_amount <= 0:
                raise ValueError
        except ValueError:
            self.recharge_status.set('请输入有效的充值金额')
            return
        self.recharge_state = STATE_WAITING
        self.recharge_status.set(f'充值金额 ¥{self.recharge_amount:.2f}，请将卡片文件拖入窗口')

    def _on_select_card(self):
        if self.recharge_state != STATE_WAITING:
            self.recharge_status.set('请先输入充值金额并点"确定金额"')
            return
        filepath = filedialog.askopenfilename(
            title='选择卡片文件',
            initialdir=CARDS_DIR
        )
        if filepath:
            self._process_recharge(filepath)

    def _on_recharge_drop(self, event):
        if self.recharge_state != STATE_WAITING:
            return
        filepath = event.data.strip('{}')
        self._process_recharge(filepath)

    def _process_recharge(self, filepath):
        try:
            card_data = self.card_mgr.import_card(filepath)
            if card_data is None:
                self.recharge_status.set('卡片文件无效')
                return

            card_id = card_data['card_id']
            card = self.card_mgr.load_card(card_id)
            if card is None:
                self.recharge_status.set('卡片不存在')
                return

            success, msg = self.card_mgr.recharge(card_id, self.recharge_amount)
            if success:
                card = self.card_mgr.load_card(card_id)
                self.logger.log_transaction(
                    card_id, 'recharge', self.recharge_amount,
                    card['balance'], MERCHANT
                )
                self.card_mgr.export_card(card_id, CARDS_DIR)
                self.recharge_status.set(
                    f"充值成功！{card['name']}，充值 ¥{self.recharge_amount:.2f} 元，"
                    f"余额 ¥{card['balance']:.2f} 元"
                )
            else:
                self.recharge_status.set(f"充值失败：{msg}")
            self.recharge_state = STATE_RESULT
        except Exception as e:
            self.recharge_status.set(f'错误：{e}')

    def cleanup(self):
        self.db.close()


def main():
    root = tk.Tk()
    app = IssuerApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()


if __name__ == '__main__':
    main()
```

---

### Task E2: 集成测试脚本

**Step 1: 创建集成测试**

```python
# tests/test_integration.py
import unittest
import os
import tempfile
import json
from database import Database
from card_manager import CardManager
from calculator import Calculator
from logger import Logger


class TestIntegration(unittest.TestCase):
    """端到端集成测试：模拟完整的发卡 → 消费 → 充值流程"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cards_dir = os.path.join(self.tmpdir, 'cards')
        os.makedirs(self.cards_dir, exist_ok=True)
        db_path = os.path.join(self.tmpdir, 'test.db')
        self.db = Database(db_path)
        self.db.init_tables()
        self.card_mgr = CardManager(self.db)
        self.logger = Logger(self.db)
        self.calc = Calculator()

    def tearDown(self):
        self.db.close()

    def test_full_flow_create_consume_recharge(self):
        """完整流程：发卡 → 消费 → 余额不足 → 充值 → 再次消费"""
        # 1. 发卡
        card = self.card_mgr.create_card("T001", "集成测试", 100.0)
        self.assertIsNotNone(card)
        self.assertEqual(card['balance'], 100.0)

        # 2. 正常消费
        success, msg = self.card_mgr.deduct("T001", 30.0)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 70.0)

        # 3. 余额不足
        success, msg = self.card_mgr.deduct("T001", 80.0)
        self.assertFalse(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 70.0)

        # 4. 充值
        success, msg = self.card_mgr.recharge("T001", 50.0)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 120.0)

        # 5. 再次消费
        success, msg = self.card_mgr.deduct("T001", 45.5)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 74.5)

    def test_export_import_roundtrip(self):
        """导出 → 导入 → 数据一致性"""
        self.card_mgr.create_card("T002", "往返测试", 200.0)
        self.card_mgr.deduct("T002", 50.0)

        # 导出
        export_path = self.card_mgr.export_card("T002", self.cards_dir)
        self.assertTrue(os.path.exists(export_path))

        # 读取导出文件
        with open(export_path, 'r') as f:
            exported = json.load(f)
        self.assertEqual(exported['balance'], 150.0)

        # 模拟"另一台终端"扣款
        self.card_mgr.deduct("T002", 20.0)

        # 导入旧文件（余额以 SQLite 为准，import_card 覆盖 SQLite）
        self.card_mgr.import_card(export_path)
        card = self.card_mgr.load_card("T002")
        # import_card 会把 JSON 的 balance 写入 SQLite
        self.assertEqual(card['balance'], 150.0)

    def test_calculator_to_card_flow(self):
        """Calculator 计算金额 → CardManager 扣款"""
        self.card_mgr.create_card("T003", "计算测试", 50.0)

        # 模拟 POS 操作：5.5 + 8.0 + 12.0
        self.calc.input_digit('5.5')
        self.calc.input_operator('+')
        self.calc.input_digit('8.0')
        self.calc.input_operator('+')
        self.calc.input_digit('12.0')
        amount = self.calc.calculate()

        self.assertAlmostEqual(amount, 25.5)

        # 扣款
        success, msg = self.card_mgr.deduct("T003", amount)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T003")
        self.assertAlmostEqual(card['balance'], 24.5)

    def test_transaction_logging_after_operations(self):
        """扣款和充值后交易记录完整"""
        self.card_mgr.create_card("T004", "日志测试", 100.0)

        self.card_mgr.deduct("T004", 10.0)
        self.logger.log_transaction("T004", "consume", 10.0, 90.0, "一食堂")

        self.card_mgr.recharge("T004", 50.0)
        self.logger.log_transaction("T004", "recharge", 50.0, 140.0, "充值中心")

        txs = self.logger.get_transactions("T004")
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0]['type'], 'consume')
        self.assertEqual(txs[1]['type'], 'recharge')
```

**Step 2: 运行集成测试**

Run: `uv run -m pytest tests/test_integration.py -v`
Expected: 4 passed

**Step 3: 提交**

```bash
git add issuer.py tests/test_integration.py
git commit -m "feat: add issuer GUI and integration tests"
```

---

### 验收标准 — 人员 E

| # | 验收项 | 操作步骤 | 预期结果 |
|---|--------|---------|---------|
| E-1 | 程序可启动 | `uv run issuer.py` | 窗口弹出，有两个选项卡 |
| E-2 | 发卡成功 | 输入卡号/姓名/余额，点生成卡片 | 状态显示成功，`data/cards/` 下有对应文件 |
| E-3 | 发卡重复卡号 | 用已存在的卡号再次发卡 | 提示"卡号已存在" |
| E-4 | 空字段校验 | 不填卡号直接点生成 | 提示"请填写卡号和姓名" |
| E-5 | 充值流程 | 输入金额→确定→拖入卡片文件 | 显示充值成功，余额更新 |
| E-6 | 充值后卡片文件更新 | 充值后查看 JSON 文件 | `balance` 字段为充值后金额 |
| E-7 | 集成测试通过 | `uv run -m pytest tests/test_integration.py -v` | 4 passed |
| E-8 | 完整流程测试 | 发卡→消费→充值→再消费 | 所有步骤正常，数据一致 |
| E-9 | 窗口关闭不报错 | 关闭窗口 | 正常退出，无报错 |

---

## 集成验收（全员完成后）

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
