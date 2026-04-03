# 人员 A：数据持久层（database.py + logger.py）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现数据持久层，提供 SQLite 数据库连接管理和交易记录模块。本模块是整个系统的基础，其他所有模块均依赖于此。

**Architecture:** Database 类负责 SQLite 连接管理和表结构初始化；Logger 类负责交易记录的写入和查询。无外部依赖，可第一个开始。

**Tech Stack:** Python 3.x / sqlite3 / unittest / uv

---

## 文件所有权

| 角色 | 我负责的文件 | 我不得修改的文件 |
|------|------------|----------------|
| 人员 A | `database.py`、`logger.py`、`tests/test_database.py`、`tests/test_logger.py` | 其他所有文件 |

---

## 依赖说明

- **无外部依赖**：本模块不依赖项目中其他任何模块，可第一个开始。
- **被依赖关系**：`database.py` 和 `logger.py` 被 B、D、E 的模块依赖。请确保接口签名与全局契约一致。

---

## 接口契约

以下是本人员需要对外暴露的接口签名，集成时不可更改。

```python
# database.py
class Database:
    def __init__(self, db_path: str = 'data/onecard.db'): ...
    def get_connection(self) -> sqlite3.Connection: ...
    def init_tables(self) -> None: ...
    def close(self) -> None: ...

# logger.py
class Logger:
    def __init__(self, db: Database): ...
    def log_transaction(self, card_id: str, tx_type: str,
                        amount: float, balance_after: float,
                        merchant: str = '') -> None: ...
    def get_transactions(self, card_id: str = None) -> list[dict]: ...
    def get_merchant_summary(self, merchant: str) -> dict: ...
```

---

## Task A1: database.py — 数据库连接管理

### Step 1: 写失败测试

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

### Step 2: 运行测试确认失败

Run: `uv run -m pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'database'`

### Step 3: 实现 database.py

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

### Step 4: 运行测试确认通过

Run: `uv run -m pytest tests/test_database.py -v`
Expected: 5 passed

### Step 5: 提交

```bash
git add database.py tests/test_database.py
git commit -m "feat: add database module with SQLite connection and table init"
```

---

## Task A2: logger.py — 交易记录模块

### Step 1: 写失败测试

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

### Step 2: 运行测试确认失败

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

### Step 3: 实现 logger.py

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

### Step 4: 运行测试确认通过

Run: `uv run -m pytest tests/test_logger.py -v`
Expected: 7 passed

### Step 5: 提交

```bash
git add logger.py tests/test_logger.py
git commit -m "feat: add logger module for transaction recording and queries"
```

---

## 验收标准 — 人员 A

| # | 验收项 | 验证命令/操作 | 预期结果 |
|---|--------|-------------|---------|
| A-1 | database.py 模块存在且可导入 | `uv run -c "from database import Database; print('OK')"` | 输出 `OK` |
| A-2 | 自动建表 | `uv run -c "from database import Database; d=Database('/tmp/test.db'); d.init_tables(); print('OK')"` | 输出 `OK`，无报错 |
| A-3 | database 单元测试全部通过 | `uv run -m pytest tests/test_database.py -v` | 5 passed |
| A-4 | logger.py 模块存在且可导入 | `uv run -c "from logger import Logger; print('OK')"` | 输出 `OK` |
| A-5 | logger 单元测试全部通过 | `uv run -m pytest tests/test_logger.py -v` | 7 passed |
| A-6 | 数据库文件可打开查看 | `uv run -c "import sqlite3; c=sqlite3.connect('/tmp/test.db'); print(c.execute('SELECT name FROM sqlite_master').fetchall())"` | 包含 cards 和 transactions 两个表 |
