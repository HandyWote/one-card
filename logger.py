import datetime
import random
import sqlite3


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
