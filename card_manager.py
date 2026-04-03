import json
import os
import sqlite3
import datetime


class CardManager:
    def __init__(self, db):
        self.db = db

    def load_card(self, card_id: str) -> dict | None:
        conn = self.db.get_connection()
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT card_id, name, balance, status, created_at FROM cards WHERE card_id = ?",
            (card_id,)
        ).fetchone()
        conn.row_factory = None
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
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        return path

    def import_card(self, json_path: str) -> dict:
        with open(json_path, 'r', encoding='utf-8') as f:
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
        card['balance'] = round(card['balance'] - amount, 2)
        self.save_card(card)
        return True, f"扣款成功，余额 {card['balance']:.2f} 元"

    def recharge(self, card_id: str, amount: float) -> tuple[bool, str]:
        if amount <= 0:
            return False, "充值金额必须大于零"
        card = self.load_card(card_id)
        if card is None:
            return False, "卡片不存在"
        card['balance'] = round(card['balance'] + amount, 2)
        self.save_card(card)
        return True, f"充值成功，余额 {card['balance']:.2f} 元"

    def create_card(self, card_id: str, name: str,
                    initial_balance: float) -> dict | None:
        if self.load_card(card_id) is not None:
            return None
        card_data = {
            'card_id': card_id,
            'name': name,
            'balance': initial_balance,
            'status': 'active',
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d')
        }
        self.save_card(card_data)
        return self.load_card(card_id)
