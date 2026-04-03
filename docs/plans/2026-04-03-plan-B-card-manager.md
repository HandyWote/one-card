# 人员 B：卡片管理逻辑（card_manager.py）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现卡片管理模块，提供卡片的 CRUD 操作、扣款、充值、以及 JSON 文件的导入导出功能。

**Architecture:** CardManager 类封装所有卡片操作逻辑，依赖 Database 类进行 SQLite 数据存取。卡片通过 JSON 文件在程序间传递（文件名即卡号，无后缀）。

**Tech Stack:** Python 3.x / sqlite3 / json / unittest / uv

---

## 文件所有权

| 角色 | 我负责的文件 | 我不得修改的文件 |
|------|------------|----------------|
| 人员 B | `card_manager.py`、`tests/test_card_manager.py` | 其他所有文件 |

---

## 依赖说明

- **依赖**：`database.py`（Person A 的接口）。B 可以先基于接口签名开发，用 mock 或临时 stub 替代 Database。
- **被依赖关系**：`card_manager.py` 被 D（terminal.py）、E（issuer.py）和 A 的 logger 测试依赖。请确保接口签名与全局契约一致。

---

## 接口契约

以下是本人员需要对外暴露的接口签名，集成时不可更改。

```python
# card_manager.py
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
```

---

## Task B1: card_manager.py — 基础 CRUD

### Step 1: 写失败测试

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

### Step 2: 运行测试确认失败

Run: `uv run -m pytest tests/test_card_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

### Step 3: 实现 card_manager.py

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

### Step 4: 运行测试确认通过

Run: `uv run -m pytest tests/test_card_manager.py -v`
Expected: 15 passed

### Step 5: 提交

```bash
git add card_manager.py tests/test_card_manager.py
git commit -m "feat: add card manager with CRUD, deduct, recharge, JSON import/export"
```

---

## 验收标准 — 人员 B

| # | 验收项 | 验证命令/操作 | 预期结果 |
|---|--------|-------------|---------|
| B-1 | 模块可导入 | `uv run -c "from card_manager import CardManager; print('OK')"` | 输出 `OK` |
| B-2 | 单元测试全部通过 | `uv run -m pytest tests/test_card_manager.py -v` | 15 passed |
| B-3 | 创建卡片后数据库有记录 | 运行测试后检查 `/tmp` 下测试数据库 | cards 表有数据 |
| B-4 | 导出文件无后缀 | 运行 `test_export_card_creates_file` 后 `ls` | 文件名是 `2024001`（无 .json） |
| B-5 | 余额不足扣款失败 | `test_deduct_insufficient_balance` | passed，余额不变 |
| B-6 | 充值后余额增加 | `test_recharge_success` | passed，100→150 |
