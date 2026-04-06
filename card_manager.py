import json
import os
import datetime
import codecs

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
        return {
            "card_id": row[0],
            "name": row[1],
            "balance": row[2],
            "status": row[3],
            "created_at": row[4]
        }

    def save_card(self, card_data: dict) -> None:
        conn = self.db.get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO cards (card_id, name, balance, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (card_data['card_id'], card_data['name'], card_data['balance'],
             card_data['status'], card_data['created_at'])
        )
        conn.commit()

    def export_card(self, card_id: str, export_dir: str, encoding: str = 'utf-8') -> str:
        card = self.load_card(card_id)
        if card is None:
            raise ValueError(f"Card {card_id} not found")
        os.makedirs(export_dir, exist_ok=True)
        path = os.path.join(export_dir, card_id)
        with open(path, 'w', encoding=encoding) as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        return path

    def import_card(self, json_path: str) -> dict:
        card_data, _ = self.import_card_compatible(json_path)
        return card_data

    def import_card_compatible(self, json_path: str) -> tuple[dict | None, str | None]:
        card_data, source_encoding = self._read_card_file_compatible(json_path)
        if card_data is None:
            return None, None

        name = card_data.get('name')
        if isinstance(name, str):
            card_data['name'] = self._fix_mojibake_name(name)

        self.save_card(card_data)
        return self.load_card(card_data['card_id']), source_encoding

    def sync_card_file(self, json_path: str, card_id: str, source_encoding: str | None = None) -> None:
        card = self.load_card(card_id)
        if card is None:
            return
        encoding = source_encoding or 'utf-8'
        with open(json_path, 'w', encoding=encoding) as f:
            json.dump(card, f, ensure_ascii=False, indent=2)

    def _read_card_file_compatible(self, json_path: str) -> tuple[dict | None, str | None]:
        try:
            with open(json_path, 'rb') as f:
                raw = f.read()
        except OSError:
            return None, None

        candidates = ['utf-8-sig'] if raw.startswith(codecs.BOM_UTF8) else ['utf-8']
        candidates.append('gb18030')

        for encoding in candidates:
            try:
                text = raw.decode(encoding)
                card_data = json.loads(text)
                if not isinstance(card_data, dict):
                    return None, None
                required = ('card_id', 'name', 'balance', 'status', 'created_at')
                if not all(k in card_data for k in required):
                    return None, None
                return card_data, encoding
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return None, None

    def _fix_mojibake_name(self, name: str) -> str:
        for wrong_enc in ('gbk', 'latin1'):
            try:
                fixed = name.encode(wrong_enc).decode('utf-8')
                if fixed:
                    return fixed
            except UnicodeError:
                continue
        return name

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
