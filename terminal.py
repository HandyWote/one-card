# terminal.py
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog

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
        self._use_file_picker = False

        # 初始化数据库和模块
        self.db = Database(DB_PATH)
        self.db.init_tables()
        self.card_mgr = CardManager(self.db)
        self.logger = Logger(self.db)

        self._build_ui()
        self._setup_card_input()
        self._set_state(STATE_INPUT)

    def _build_ui(self):
        # 显示区
        self.display_var = tk.StringVar(value='')
        display_font = tkfont.Font(size=28, weight='bold')
        tk.Label(self.root, textvariable=self.display_var,
                 font=display_font, anchor='e', padx=20, pady=15,
                 relief='sunken', width=16).pack(fill='x', padx=10, pady=(10, 5))

        # 结果区
        self.result_var = tk.StringVar(value='')
        result_font_family = 'Microsoft YaHei UI'
        if result_font_family not in tkfont.families():
            result_font_family = 'SimHei'
        tk.Label(self.root, textvariable=self.result_var,
                 font=(result_font_family, 12), fg='green', anchor='w', padx=10,
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

        self.pick_card_btn = tk.Button(
            self.root,
            text='选择卡片',
            font=('Arial', 12),
            command=self._on_pick_card
        )

    def _setup_card_input(self):
        # 尝试启用拖放，失败时回退到文件选择按钮
        try:
            from tkinterdnd2 import DND_FILES
            if hasattr(self.root, 'drop_target_register') and hasattr(self.root, 'dnd_bind'):
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self._on_drop)
            else:
                self._enable_file_picker()
        except ImportError:
            self._enable_file_picker()
        except Exception:
            self._enable_file_picker()

    def _enable_file_picker(self):
        self._use_file_picker = True
        self.pick_card_btn.pack(fill='x', padx=10, pady=(0, 10))

    def _set_state(self, state):
        self.state = state
        if self._use_file_picker:
            picker_state = tk.NORMAL if state == STATE_WAITING else tk.DISABLED
            self.pick_card_btn.config(state=picker_state)

    def _on_digit(self, digit):
        if self.state == STATE_RESULT:
            self.result_var.set('')
            self.calculator.clear()
            self._set_state(STATE_INPUT)
        if self.state in (STATE_INPUT, STATE_RESULT):
            display = self.calculator.input_digit(digit)
            self.display_var.set(display)

    def _on_operator(self, op):
        if self.state == STATE_RESULT:
            self.result_var.set('')
            self.calculator.clear()
            self._set_state(STATE_INPUT)
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
        self._set_state(STATE_INPUT)

    def _on_confirm(self):
        if self.state == STATE_RESULT:
            self.result_var.set('')
            self.calculator.clear()
            self._set_state(STATE_INPUT)
            return
        if self.state != STATE_INPUT:
            return
        self.amount = self.calculator.calculate()
        if self.amount <= 0:
            self.result_var.set('请先输入金额')
            return
        self.display_var.set(f'¥ {self.amount:.2f}  请刷卡')
        self._set_state(STATE_WAITING)

    def _on_drop(self, event):
        if self.state != STATE_WAITING:
            return
        paths = self.root.tk.splitlist(event.data)
        if not paths:
            return
        self._process_card(paths[0])

    def _on_pick_card(self):
        if self.state != STATE_WAITING:
            return
        filepath = filedialog.askopenfilename(
            title='选择卡片文件',
            initialdir=CARDS_DIR
        )
        if filepath:
            self._process_card(filepath)

    def _process_card(self, filepath):
        try:
            card_data, source_encoding = self.card_mgr.import_card_compatible(filepath)
            if card_data is None:
                self.result_var.set('卡片文件无效')
                self._set_state(STATE_RESULT)
                return
            card_id = card_data['card_id']
            card = self.card_mgr.load_card(card_id)
            if card is None:
                self.result_var.set('卡片不存在')
                self._set_state(STATE_RESULT)
                return

            # 执行扣款
            success, msg = self.card_mgr.deduct(card_id, self.amount)
            if success:
                card = self.card_mgr.load_card(card_id)
                self.logger.log_transaction(
                    card_id, 'consume', self.amount,
                    card['balance'], MERCHANT
                )
                self.card_mgr.sync_card_file(filepath, card_id, source_encoding)
                self.display_var.set(f'¥ {card["balance"]:.2f} 元')
                self.result_var.set(
                    f"扣款成功，{card['name']}，扣款 ¥{self.amount:.2f} 元，"
                    f"余额 ¥{card['balance']:.2f} 元"
                )
            else:
                self.result_var.set(f"扣款失败：{msg}")
            self._set_state(STATE_RESULT)
        except Exception as e:
            self.result_var.set(f'错误：{e}')
            self._set_state(STATE_RESULT)

    def cleanup(self):
        self.db.close()


def main():
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    app = TerminalApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()


if __name__ == '__main__':
    main()
