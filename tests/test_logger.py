import unittest
import os
import tempfile
from database import Database
from logger import Logger


class TestLogger(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = Database(os.path.join(self.tmpdir, 'test.db'))
        self.db.init_tables()
        self.logger = Logger(self.db)
        # 直接插入测试卡片，绕过 card_manager 依赖
        self.db.get_connection().execute(
            "INSERT INTO cards VALUES (?, ?, ?, ?, ?)",
            ("T001", "测试用户", 100.0, "active", "2026-04-01")
        )
        self.db.get_connection().commit()

    def tearDown(self):
        self.db.close()

    def test_log_transaction_creates_record(self):
        """log_transaction 应在 transactions 表中创建一条记录"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0, "一食堂")
        txs = self.logger.get_transactions("T001")
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]['amount'], 10.0)
        self.assertEqual(txs[0]['balance_after'], 90.0)

    def test_log_transaction_generates_unique_tx_id(self):
        """每次 log_transaction 应生成不同的 tx_id"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        self.logger.log_transaction("T001", "consume", 5.0, 85.0)
        txs = self.logger.get_transactions("T001")
        self.assertNotEqual(txs[0]['tx_id'], txs[1]['tx_id'])

    def test_log_transaction_tx_id_starts_with_TX(self):
        """流水号应以 TX 开头"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        txs = self.logger.get_transactions("T001")
        self.assertTrue(txs[0]['tx_id'].startswith('TX'))

    def test_get_transactions_filter_by_card_id(self):
        """按卡号过滤交易记录"""
        self.db.get_connection().execute(
            "INSERT INTO cards VALUES (?, ?, ?, ?, ?)",
            ("T002", "用户B", 50.0, "active", "2026-04-01")
        )
        self.db.get_connection().commit()
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        self.logger.log_transaction("T002", "recharge", 20.0, 70.0)
        txs = self.logger.get_transactions("T001")
        self.assertEqual(len(txs), 1)

    def test_get_transactions_all(self):
        """不传 card_id 时返回所有记录"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0)
        self.logger.log_transaction("T001", "consume", 5.0, 85.0)
        txs = self.logger.get_transactions()
        self.assertEqual(len(txs), 2)

    def test_get_merchant_summary(self):
        """商户汇总统计"""
        self.logger.log_transaction("T001", "consume", 10.0, 90.0, "一食堂")
        self.logger.log_transaction("T001", "consume", 5.0, 85.0, "一食堂")
        self.logger.log_transaction("T001", "consume", 3.0, 82.0, "校内超市")
        summary = self.logger.get_merchant_summary("一食堂")
        self.assertEqual(summary['total_amount'], 15.0)
        self.assertEqual(summary['count'], 2)

    def test_log_recharge(self):
        """充值记录应有 type='recharge'"""
        self.logger.log_transaction("T001", "recharge", 50.0, 150.0, "充值中心")
        txs = self.logger.get_transactions("T001")
        self.assertEqual(txs[0]['type'], 'recharge')
