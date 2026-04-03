# 人员 D：消费终端 GUI（terminal.py）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现消费终端 GUI 程序，模拟食堂/超市 POS 刷卡机，支持数字键盘输入、运算、拖拽刷卡和自动扣款。

**Architecture:** TerminalApp 类基于 tkinter 构建，包含显示区、结果区和按键区。通过状态机管理输入→等待刷卡→显示结果三种状态。依赖 Calculator、CardManager、Database 和 Logger 模块。

**Tech Stack:** Python 3.x / tkinter / tkinterdnd2（可选） / uv

---

## 文件所有权

| 角色 | 我负责的文件 | 我不得修改的文件 |
|------|------------|----------------|
| 人员 D | `terminal.py` | 其他所有文件 |

---

## 依赖说明

- **依赖**：
  - `calculator.py`（Person C）— 运算引擎
  - `card_manager.py`（Person B）— 卡片管理
  - `logger.py`（Person A）— 交易记录
  - `database.py`（Person A）— 数据库连接
- **被依赖关系**：无。terminal.py 是最终消费端程序。

---

## 接口契约

以下是本人员需要使用的接口签名（由 A、B、C 提供，不可修改）：

```python
# 来自 Person C — calculator.py
class Calculator:
    def input_digit(self, digit: str) -> str: ...
    def input_operator(self, op: str) -> str: ...
    def backspace(self) -> str: ...
    def calculate(self) -> float: ...
    def get_display(self) -> str: ...
    def clear(self) -> None: ...

# 来自 Person B — card_manager.py
class CardManager:
    def import_card(self, json_path: str) -> dict: ...
    def load_card(self, card_id: str) -> dict | None: ...
    def deduct(self, card_id: str, amount: float) -> tuple[bool, str]: ...
    def export_card(self, card_id: str, export_dir: str) -> str: ...

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
```

**公共常量：**
- 商户名称：`MERCHANT = "一食堂"`
- 数据库路径：`DB_PATH = 'data/onecard.db'`
- 卡片文件目录：`CARDS_DIR = 'data/cards'`

---

## Task D1: terminal.py — 消费终端完整实现

### Step 1: 搭建 GUI 框架

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

**状态机（3 个状态）：**

```python
STATE_INPUT = 'input'       # 输入金额
STATE_WAITING = 'waiting'   # 等待刷卡（确定后）
STATE_RESULT = 'result'     # 显示结果（刷卡后）
```

**核心实现要点：**

1. **显示区**：大字体（如 28pt bold），绑定 `StringVar`，实时反映 Calculator 的 `get_display()`
2. **结果区**：初始为空，扣款成功/失败后显示文本
3. **按键区**：每个按钮绑定对应处理函数
   - 数字键 0-9、`.`：调用 `calc.input_digit()`
   - `+`、`-`、`×`：调用 `calc.input_operator()`
   - 回退：调用 `calc.backspace()`
   - 清除：调用 `calc.clear()`，重置到 `STATE_INPUT`
   - 确定：调用 `calc.calculate()`，切换到 `STATE_WAITING`，显示区显示"¥ XX.XX  请刷卡"
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

### Step 2: 完整实现代码

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

### Step 3: 手动验收测试

见下方验收标准。

### Step 4: 提交

```bash
git add terminal.py
git commit -m "feat: add terminal GUI with keypad, drag-drop, and state machine"
```

---

## 验收标准 — 人员 D

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
