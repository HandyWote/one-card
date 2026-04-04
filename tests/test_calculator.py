import unittest
from calculator import Calculator


class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_input_single_digit(self):
        """输入单个数字应正确显示"""
        self.assertEqual(self.calc.input_digit('5'), '5')

    def test_input_multi_digit(self):
        """连续输入数字应拼接"""
        self.assertEqual(self.calc.input_digit('1'), '1')
        self.assertEqual(self.calc.input_digit('2'), '12')
        self.assertEqual(self.calc.input_digit('3'), '123')

    def test_input_decimal_point(self):
        """输入小数点"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_digit('.'), '5.')
        self.assertEqual(self.calc.input_digit('5'), '5.5')

    def test_no_double_decimal(self):
        """不应允许输入两个小数点"""
        self.calc.input_digit('5')
        self.calc.input_digit('.')
        result = self.calc.input_digit('.')
        self.assertEqual(result, '5.')

    def test_input_operator(self):
        """输入运算符应锁定当前数字，后续输入新数字只显示新数字"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_operator('+'), '5 +')
        self.assertEqual(self.calc.input_digit('3'), '3')

    def test_backspace(self):
        """回退应删除最后一位；退到空显示空字符串"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_digit('3'), '53')
        self.assertEqual(self.calc.backspace(), '5')
        self.assertEqual(self.calc.backspace(), '')

    def test_clear(self):
        """清除应重置所有状态"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('3')
        self.calc.clear()
        self.assertEqual(self.calc.get_display(), '')

    def test_calculate_single_number(self):
        """只输入一个数字直接计算应返回该数"""
        self.calc.input_digit('25.5')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 25.5)

    def test_calculate_addition(self):
        """5.5 + 8.0 = 13.5"""
        self.calc.input_digit('5')
        self.calc.input_digit('.')
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('8')
        self.calc.input_digit('.')
        self.calc.input_digit('0')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 13.5)

    def test_calculate_subtraction(self):
        """20 - 7.5 = 12.5"""
        self.calc.input_digit('2')
        self.calc.input_digit('0')
        self.calc.input_operator('-')
        self.calc.input_digit('7')
        self.calc.input_digit('.')
        self.calc.input_digit('5')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 12.5)

    def test_calculate_multiplication(self):
        """3 × 4 = 12"""
        self.calc.input_digit('3')
        self.calc.input_operator('×')
        self.calc.input_digit('4')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 12.0)

    def test_calculate_sequential(self):
        """按输入顺序计算：5 + 8 + 12 = 25（不是数学优先级）"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('8')
        self.calc.input_operator('+')
        self.calc.input_digit('1')
        self.calc.input_digit('2')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 25.0)

    def test_calculate_sequential_mixed(self):
        """10 + 3 × 2 = 26（按顺序：先 10+3=13，再 13×2=26）"""
        self.calc.input_digit('1')
        self.calc.input_digit('0')
        self.calc.input_operator('+')
        self.calc.input_digit('3')
        self.calc.input_operator('×')
        self.calc.input_digit('2')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 26.0)

    def test_calculate_then_input_clears(self):
        """计算完成后输入新数字应清除旧结果"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('3')
        self.calc.calculate()
        display = self.calc.input_digit('1')
        self.assertEqual(display, '1')

    def test_get_display(self):
        """get_display 应返回当前输入内容"""
        self.assertEqual(self.calc.get_display(), '')
        self.calc.input_digit('5')
        self.assertEqual(self.calc.get_display(), '5')
        self.calc.input_operator('+')
        self.assertEqual(self.calc.get_display(), '5 +')

    def test_calculate_no_input(self):
        """无输入时计算应返回 0"""
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 0.0)

    def test_calculate_operator_only(self):
        """只输入运算符没有第二操作数时应返回第一操作数"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 5.0)

    def test_zero_amount(self):
        """输入 0 应正常工作"""
        self.calc.input_digit('0')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 0.0)


if __name__ == '__main__':
    unittest.main()
