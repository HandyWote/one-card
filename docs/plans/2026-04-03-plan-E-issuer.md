# 人员 E：充值发卡站（issuer.py + 集成测试）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现充值发卡站 GUI 程序和集成测试。充值发卡站支持发卡（创建新卡并导出 JSON 文件）和圈存充值（导入卡片文件并充值），以及端到端集成测试验证完整流程。

**Architecture:** IssuerApp 类基于 tkinter 的 ttk.Notebook 构建双选项卡界面。集成测试覆盖发卡→消费→充值→再消费的完整端到端流程。依赖 Database、CardManager 和 Logger 模块。

**Tech Stack:** Python 3.x / tkinter / tkinterdnd2（可选） / sqlite3 / unittest / uv

---

## 文件所有权

| 角色 | 我负责的文件 | 我不得修改的文件 |
|------|------------|----------------|
| 人员 E | `issuer.py`、`tests/test_integration.py`、`data/cards/` | 其他所有源代码文件 |

---

## 依赖说明

- **依赖**：
  - `card_manager.py`（Person B）— 卡片管理
  - `logger.py`（Person A）— 交易记录
  - `database.py`（Person A）— 数据库连接
  - `calculator.py`（Person C）— 仅集成测试中使用
- **被依赖关系**：无。issuer.py 和集成测试是最终的集成验证。

---

## 接口契约

以下是本人员需要使用的接口签名（由 A、B、C 提供，不可修改）：

```python
# 来自 Person A — database.py
class Database:
    def __init__(self, db_path: str = 'data/onecard.db'): ...
    def init_tables(self) -> None: ...
    def close(self) -> None: ...

# 来自 Person A — logger.py
class Logger:
    def __init__(self, db: Database): ...
    def log_transaction(self, card_id: str, tx_type: str,
                        amount: float, balance_after: float,
                        merchant: str = '') -> None: ...
    def get_transactions(self, card_id: str = None) -> list[dict]: ...

# 来自 Person B — card_manager.py
class CardManager:
    def create_card(self, card_id: str, name: str,
                    initial_balance: float) -> dict: ...
    def import_card(self, json_path: str) -> dict: ...
    def load_card(self, card_id: str) -> dict | None: ...
    def recharge(self, card_id: str, amount: float) -> tuple[bool, str]: ...
    def deduct(self, card_id: str, amount: float) -> tuple[bool, str]: ...
    def export_card(self, card_id: str, export_dir: str) -> str: ...

# 来自 Person C — calculator.py（仅集成测试使用）
class Calculator:
    def input_digit(self, digit: str) -> str: ...
    def input_operator(self, op: str) -> str: ...
    def calculate(self) -> float: ...
    def clear(self) -> None: ...
```

**公共常量：**
- 商户名称：`MERCHANT = "充值中心"`
- 数据库路径：`DB_PATH = 'data/onecard.db'`
- 卡片文件目录：`CARDS_DIR = 'data/cards'`

---

## Task E1: issuer.py — 充值发卡站完整实现

### Step 1: 搭建 GUI 框架

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

### Step 2: 完整实现代码

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

### Step 3: 提交

```bash
git add issuer.py
git commit -m "feat: add issuer GUI with create-card and recharge tabs"
```

---

## Task E2: 集成测试脚本

### Step 1: 创建集成测试

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

### Step 2: 运行集成测试

Run: `uv run -m pytest tests/test_integration.py -v`
Expected: 4 passed

### Step 3: 提交

```bash
git add issuer.py tests/test_integration.py
git commit -m "feat: add issuer GUI and integration tests"
```

---

## 验收标准 — 人员 E

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
