import tkinter as tk
from tkinter import ttk, filedialog, font as tkfont

from database import Database
from card_manager import CardManager
from logger import Logger

MERCHANT = "充值中心"
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


class IssuerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("校园一卡通 — 充值发卡站")
        self.root.resizable(False, False)
        self.font_family = _get_font_family(root)

        self.recharge_state = STATE_INPUT
        self.recharge_amount = 0.0

        self.db = Database(DB_PATH)
        self.db.init_tables()
        self.card_mgr = CardManager(self.db)
        self.logger = Logger(self.db)

        self._build_ui()

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
                   command=self._on_create_card).grid(
            row=3, column=0, columnspan=2, pady=15)

        self.create_status = tk.StringVar(value='')
        ttk.Label(create_frame, textvariable=self.create_status,
                  font=(self.font_family, 11), wraplength=280).grid(
            row=4, column=0, columnspan=2)

        # === 充值选项卡 ===
        self.recharge_frame = ttk.Frame(notebook, padding=20)
        notebook.add(self.recharge_frame, text='充值')

        ttk.Label(self.recharge_frame, text='充值金额：').grid(
            row=0, column=0, sticky='w', pady=5)
        self.entry_recharge_amount = ttk.Entry(self.recharge_frame, width=20)
        self.entry_recharge_amount.grid(row=0, column=1, pady=5)

        ttk.Button(self.recharge_frame, text='确定金额',
                   command=self._on_recharge_confirm).grid(
            row=1, column=0, columnspan=2, pady=5)

        ttk.Button(self.recharge_frame, text='选择卡片文件',
                   command=self._on_select_card).grid(
            row=2, column=0, columnspan=2, pady=5)

        ttk.Label(self.recharge_frame, text='（或将卡片文件拖拽到此窗口）',
                  foreground='gray').grid(row=3, column=0, columnspan=2, pady=5)

        self.recharge_status = tk.StringVar(value='')
        ttk.Label(self.recharge_frame, textvariable=self.recharge_status,
                  font=(self.font_family, 11), wraplength=280).grid(
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
        self.recharge_status.set(
            f'充值金额 ¥{self.recharge_amount:.2f}，请将卡片文件拖入窗口或点击"选择卡片文件"')

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
