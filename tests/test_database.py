import unittest
import os
import tempfile
from database import Database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'test.db')
        self.db = Database(self.db_path)

    def tearDown(self):
        self.db.close()
        # 清理临时文件

    def test_init_creates_directory_and_file(self):
        """初始化时应自动创建 data 目录和 .db 文件"""
        self.assertTrue(os.path.exists(self.db_path))

    def test_init_tables_creates_cards_table(self):
        """init_tables 应创建 cards 表"""
        self.db.init_tables()
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cards'"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_init_tables_creates_transactions_table(self):
        """init_tables 应创建 transactions 表"""
        self.db.init_tables()
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_init_tables_idempotent(self):
        """重复调用 init_tables 不应报错"""
        self.db.init_tables()
        self.db.init_tables()  # 不应抛异常

    def test_get_connection_returns_working_connection(self):
        """get_connection 应返回可执行的连接"""
        self.db.init_tables()
        conn = self.db.get_connection()
        result = conn.execute("SELECT 1 + 1").fetchone()
        self.assertEqual(result[0], 2)
