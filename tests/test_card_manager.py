import unittest
import os
import tempfile
import json
from database import Database
from card_manager import CardManager


class TestCardManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cards_dir = os.path.join(self.tmpdir, 'cards')
        os.makedirs(self.cards_dir, exist_ok=True)
        db_path = os.path.join(self.tmpdir, 'test.db')
        self.db = Database(db_path)
        self.db.init_tables()
        self.mgr = CardManager(self.db)

    def tearDown(self):
        self.db.close()

    # --- 基础 CRUD ---

    def test_create_card(self):
        """创建卡片应写入数据库"""
        card = self.mgr.create_card("2024001", "张三", 100.0)
        self.assertEqual(card['card_id'], "2024001")
        self.assertEqual(card['name'], "张三")
        self.assertEqual(card['balance'], 100.0)
        self.assertEqual(card['status'], "active")

    def test_create_card_exists(self):
        """重复卡号应返回 None"""
        self.mgr.create_card("2024001", "张三", 100.0)
        result = self.mgr.create_card("2024001", "李四", 50.0)
        self.assertIsNone(result)

    def test_load_card(self):
        """加载存在的卡片应返回数据"""
        self.mgr.create_card("2024001", "张三", 100.0)
        card = self.mgr.load_card("2024001")
        self.assertIsNotNone(card)
        self.assertEqual(card['name'], "张三")
        self.assertEqual(card['balance'], 100.0)

    def test_load_card_not_found(self):
        """加载不存在的卡片应返回 None"""
        card = self.mgr.load_card("9999999")
        self.assertIsNone(card)

    def test_save_card(self):
        """save_card 应更新数据库中的卡片"""
        self.mgr.create_card("2024001", "张三", 100.0)
        self.mgr.save_card({
            'card_id': '2024001', 'name': '张三',
            'balance': 80.0, 'status': 'active',
            'created_at': '2026-04-01'
        })
        card = self.mgr.load_card("2024001")
        self.assertEqual(card['balance'], 80.0)

    # --- 扣款 ---

    def test_deduct_success(self):
        """余额充足时扣款成功"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.deduct("2024001", 30.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 70.0)

    def test_deduct_insufficient_balance(self):
        """余额不足时扣款失败"""
        self.mgr.create_card("2024001", "张三", 10.0)
        success, msg = self.mgr.deduct("2024001", 50.0)
        self.assertFalse(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 10.0)

    def test_deduct_exact_balance(self):
        """余额恰好等于扣款金额时应成功"""
        self.mgr.create_card("2024001", "张三", 50.0)
        success, msg = self.mgr.deduct("2024001", 50.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 0.0)

    def test_deduct_negative_amount(self):
        """扣款金额为负数时应失败"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.deduct("2024001", -10.0)
        self.assertFalse(success)

    def test_deduct_card_not_found(self):
        """卡片不存在时扣款失败"""
        success, msg = self.mgr.deduct("9999999", 10.0)
        self.assertFalse(success)

    # --- 充值 ---

    def test_recharge_success(self):
        """充值成功"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.recharge("2024001", 50.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 150.0)

    def test_recharge_negative_amount(self):
        """充值金额为负数时应失败"""
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.recharge("2024001", -10.0)
        self.assertFalse(success)

    def test_recharge_card_not_found(self):
        """卡片不存在时充值失败"""
        success, msg = self.mgr.recharge("9999999", 50.0)
        self.assertFalse(success)

    # --- JSON 导入导出 ---

    def test_export_card_creates_file(self):
        """导出应创建卡片文件（文件名即卡号，无后缀）"""
        self.mgr.create_card("2024001", "张三", 100.0)
        path = self.mgr.export_card("2024001", self.cards_dir)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(os.path.basename(path), "2024001")

    def test_export_card_json_content(self):
        """导出文件内容应为合法 JSON"""
        self.mgr.create_card("2024001", "张三", 100.0)
        path = self.mgr.export_card("2024001", self.cards_dir)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['card_id'], "2024001")
        self.assertEqual(data['name'], "张三")

    def test_import_card(self):
        """导入应将 JSON 文件写入数据库"""
        card_file = os.path.join(self.cards_dir, "2024002")
        with open(card_file, 'w') as f:
            json.dump({
                "card_id": "2024002", "name": "李四",
                "balance": 200.0, "status": "active",
                "created_at": "2026-04-02"
            }, f)
        card = self.mgr.import_card(card_file)
        self.assertEqual(card['card_id'], "2024002")
        db_card = self.mgr.load_card("2024002")
        self.assertIsNotNone(db_card)

    def test_import_card_updates_existing(self):
        """导入已存在的卡应覆盖数据库记录"""
        self.mgr.create_card("2024001", "张三", 100.0)
        card_file = os.path.join(self.cards_dir, "2024001")
        with open(card_file, 'w') as f:
            json.dump({
                "card_id": "2024001", "name": "张三",
                "balance": 300.0, "status": "active",
                "created_at": "2026-04-01"
            }, f)
        self.mgr.import_card(card_file)
        db_card = self.mgr.load_card("2024001")
        self.assertEqual(db_card['balance'], 300.0)
