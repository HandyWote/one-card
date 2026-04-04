import unittest
import os
import tempfile
import json
from database import Database
from card_manager import CardManager
from calculator import Calculator
from logger import Logger


class TestIntegration(unittest.TestCase):
    """端到端集成测试：模拟完整的发卡 → 消费 → 充值流程"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cards_dir = os.path.join(self.tmpdir, 'cards')
        os.makedirs(self.cards_dir, exist_ok=True)
        db_path = os.path.join(self.tmpdir, 'test.db')
        self.db = Database(db_path)
        self.db.init_tables()
        self.card_mgr = CardManager(self.db)
        self.logger = Logger(self.db)
        self.calc = Calculator()

    def tearDown(self):
        self.db.close()

    def test_full_flow_create_consume_recharge(self):
        """完整流程：发卡 → 消费 → 余额不足 → 充值 → 再次消费"""
        # 1. 发卡
        card = self.card_mgr.create_card("T001", "集成测试", 100.0)
        self.assertIsNotNone(card)
        self.assertEqual(card['balance'], 100.0)

        # 2. 正常消费
        success, msg = self.card_mgr.deduct("T001", 30.0)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 70.0)

        # 3. 余额不足
        success, msg = self.card_mgr.deduct("T001", 80.0)
        self.assertFalse(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 70.0)

        # 4. 充值
        success, msg = self.card_mgr.recharge("T001", 50.0)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 120.0)

        # 5. 再次消费
        success, msg = self.card_mgr.deduct("T001", 45.5)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T001")
        self.assertAlmostEqual(card['balance'], 74.5)

    def test_export_import_roundtrip(self):
        """导出 → 导入 → 数据一致性"""
        self.card_mgr.create_card("T002", "往返测试", 200.0)
        self.card_mgr.deduct("T002", 50.0)

        # 导出
        export_path = self.card_mgr.export_card("T002", self.cards_dir)
        self.assertTrue(os.path.exists(export_path))

        # 读取导出文件
        with open(export_path, 'r', encoding='utf-8') as f:
            exported = json.load(f)
        self.assertEqual(exported['balance'], 150.0)

        # 模拟"另一台终端"扣款
        self.card_mgr.deduct("T002", 20.0)

        # 导入旧文件（import_card 将 JSON 余额覆盖写入 SQLite）
        self.card_mgr.import_card(export_path)
        card = self.card_mgr.load_card("T002")
        self.assertEqual(card['balance'], 150.0)

    def test_calculator_to_card_flow(self):
        """Calculator 计算金额 → CardManager 扣款"""
        self.card_mgr.create_card("T003", "计算测试", 50.0)

        # 模拟 POS 操作：5.5 + 8.0 + 12.0
        self.calc.input_digit('5.5')
        self.calc.input_operator('+')
        self.calc.input_digit('8.0')
        self.calc.input_operator('+')
        self.calc.input_digit('12.0')
        amount = self.calc.calculate()

        self.assertAlmostEqual(amount, 25.5)

        success, msg = self.card_mgr.deduct("T003", amount)
        self.assertTrue(success)
        card = self.card_mgr.load_card("T003")
        self.assertAlmostEqual(card['balance'], 24.5)

    def test_transaction_logging_after_operations(self):
        """扣款和充值后交易记录完整"""
        self.card_mgr.create_card("T004", "日志测试", 100.0)

        self.card_mgr.deduct("T004", 10.0)
        self.logger.log_transaction("T004", "consume", 10.0, 90.0, "一食堂")

        self.card_mgr.recharge("T004", 50.0)
        self.logger.log_transaction("T004", "recharge", 50.0, 140.0, "充值中心")

        txs = self.logger.get_transactions("T004")
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0]['type'], 'consume')
        self.assertEqual(txs[1]['type'], 'recharge')
