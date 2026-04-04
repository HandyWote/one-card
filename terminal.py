# terminal.py
import tkinter as tk
from tkinter import font as tkfont, filedialog
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


def _get_font_family(root):
    families = set(tkfont.families(root))
    for candidate in ['Noto Sans CJK SC', 'WenQuanYi Micro Hei',
                       'Microsoft YaHei', 'PingFang SC', 'Arial']:
        if candidate in families:
            return candidate
    return 'TkDefaultFont'


class TerminalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("校园一卡通 — 消费终端")
        self.root.resizable(False, False)
        self.font_family = _get_font_family(root)

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
        except Exception:
            pass

    def _build_ui(self):
        # 显示区
        self.display_var = tk.StringVar(value='')
        display_font = tkfont.Font(family=self.font_family, size=28, weight='bold')
        tk.Label(self.root, textvariable=self.display_var,
                 font=display_font, anchor='e', padx=20, pady=15,
                 relief='sunken', width=16).pack(fill='x', padx=10, pady=(10, 5))

        # 结果区
        self.result_var = tk.StringVar(value='')
        tk.Label(self.root, textvariable=self.result_var,
                 font=(self.font_family, 12), fg='green', anchor='w', padx=10,
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
                            font=(self.font_family, 14))
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
                  font=(self.font_family, 14), command=self._on_clear
                  ).grid(row=4, column=0, columnspan=2, padx=2, pady=2)
        tk.Button(keypad, text='确定', width=14, height=2,
                  font=(self.font_family, 14, 'bold'),
                  command=self._on_confirm
                  ).grid(row=4, column=2, columnspan=2, padx=2, pady=2)

        # 选择卡片按钮（拖放的替代/补充）
        tk.Button(self.root, text='选择卡片', width=30, height=1,
                  font=(self.font_family, 11),
                  command=self._on_select_card
                  ).pack(pady=(0, 10))

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

    def _on_select_card(self):
        if self.state != STATE_WAITING:
            self.result_var.set('请先输入金额并点击"确定"')
            return
        filepath = filedialog.askopenfilename(
            title='选择卡片文件',
            initialdir=CARDS_DIR
        )
        if filepath:
            self._process_card(filepath)

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
