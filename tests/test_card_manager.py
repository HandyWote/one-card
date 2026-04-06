import unittest
import os
import tempfile
import json
import codecs
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

    def test_create_card(self):
        card = self.mgr.create_card("2024001", "张三", 100.0)
        self.assertEqual(card['card_id'], "2024001")
        self.assertEqual(card['name'], "张三")
        self.assertEqual(card['balance'], 100.0)
        self.assertEqual(card['status'], "active")

    def test_create_card_exists(self):
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
        card = self.mgr.load_card("9999999")
        self.assertIsNone(card)

    def test_save_card(self):
        self.mgr.create_card("2024001", "张三", 100.0)
        self.mgr.save_card({
            'card_id': '2024001', 'name': '张三',
            'balance': 80.0, 'status': 'active',
            'created_at': '2026-04-01'
        })
        card = self.mgr.load_card("2024001")
        self.assertEqual(card['balance'], 80.0)

    def test_deduct_success(self):
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.deduct("2024001", 30.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 70.0)

    def test_deduct_insufficient_balance(self):
        self.mgr.create_card("2024001", "张三", 10.0)
        success, msg = self.mgr.deduct("2024001", 50.0)
        self.assertFalse(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 10.0)

    def test_deduct_exact_balance(self):
        self.mgr.create_card("2024001", "张三", 50.0)
        success, msg = self.mgr.deduct("2024001", 50.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 0.0)

    def test_deduct_negative_amount(self):
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.deduct("2024001", -10.0)
        self.assertFalse(success)

    def test_deduct_card_not_found(self):
        success, msg = self.mgr.deduct("9999999", 10.0)
        self.assertFalse(success)

    def test_recharge_success(self):
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.recharge("2024001", 50.0)
        self.assertTrue(success)
        card = self.mgr.load_card("2024001")
        self.assertAlmostEqual(card['balance'], 150.0)

    def test_recharge_negative_amount(self):
        self.mgr.create_card("2024001", "张三", 100.0)
        success, msg = self.mgr.recharge("2024001", -10.0)
        self.assertFalse(success)

    def test_recharge_card_not_found(self):
        success, msg = self.mgr.recharge("9999999", 50.0)
        self.assertFalse(success)

    def test_export_card_creates_file(self):
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
        # 先手动创建一个 JSON 文件
        card_file = os.path.join(self.cards_dir, "2024002")
        with open(card_file, 'w') as f:
            json.dump({
                "card_id": "2024002", "name": "李四",
                "balance": 200.0, "status": "active",
                "created_at": "2026-04-02"
            }, f)
        card = self.mgr.import_card(card_file)
        self.assertEqual(card['card_id'], "2024002")
        # 验证数据库中有此卡
        db_card = self.mgr.load_card("2024002")
        self.assertIsNotNone(db_card)

    def test_import_card_updates_existing(self):
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

    def test_import_card_compatible_reads_gb18030(self):
        card_file = os.path.join(self.cards_dir, "2024003")
        card_payload = {
            "card_id": "2024003",
            "name": "张三",
            "balance": 88.0,
            "status": "active",
            "created_at": "2026-04-02"
        }
        raw = json.dumps(card_payload, ensure_ascii=False, indent=2).encode('gb18030')
        with open(card_file, 'wb') as f:
            f.write(raw)

        card, source_encoding = self.mgr.import_card_compatible(card_file)

        self.assertIsNotNone(card)
        self.assertEqual(card['card_id'], "2024003")
        self.assertEqual(card['name'], "张三")
        self.assertEqual(source_encoding, 'gb18030')

    def test_sync_card_file_preserves_utf8_sig(self):
        self.mgr.create_card("2024004", "李四", 100.0)
        card_file = os.path.join(self.cards_dir, "2024004")
        with open(card_file, 'wb') as f:
            f.write(codecs.BOM_UTF8)
            f.write(
                json.dumps({
                    "card_id": "2024004",
                    "name": "李四",
                    "balance": 100.0,
                    "status": "active",
                    "created_at": "2026-04-03"
                }, ensure_ascii=False, indent=2).encode('utf-8')
            )

        ok, _ = self.mgr.recharge("2024004", 10.0)
        self.assertTrue(ok)
        self.mgr.sync_card_file(card_file, "2024004", "utf-8-sig")

        with open(card_file, 'rb') as f:
            raw = f.read()
        self.assertTrue(raw.startswith(codecs.BOM_UTF8))
        card_data = json.loads(raw.decode('utf-8-sig'))
        self.assertAlmostEqual(card_data['balance'], 110.0)

if __name__ == '__main__':
    unittest.main()
