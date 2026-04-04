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
