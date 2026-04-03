# 人员 C：运算引擎（calculator.py）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现辅助运算模块，提供 POS 机风格逐项累加计算功能。不遵循数学优先级，按输入顺序从左到右计算。

**Architecture:** Calculator 类维护一个表达式列表和当前输入数字，支持数字输入、运算符输入、回退、清除和计算。完全独立模块，无外部依赖。

**Tech Stack:** Python 3.x / unittest / uv

---

## 文件所有权

| 角色 | 我负责的文件 | 我不得修改的文件 |
|------|------------|----------------|
| 人员 C | `calculator.py`、`tests/test_calculator.py` | 其他所有文件 |

---

## 依赖说明

- **无外部依赖**：本模块不依赖项目中其他任何模块，可第一个开始。
- **被依赖关系**：`calculator.py` 被 D（terminal.py）依赖。请确保接口签名与全局契约一致。

---

## 接口契约

以下是本人员需要对外暴露的接口签名，集成时不可更改。

```python
# calculator.py
class Calculator:
    def __init__(self): ...
    def input_digit(self, digit: str) -> str: ...
    def input_operator(self, op: str) -> str: ...
    def backspace(self) -> str: ...
    def calculate(self) -> float: ...
    def get_display(self) -> str: ...
    def clear(self) -> None: ...
```

**关键行为约束：**
- 按输入顺序计算（不遵循数学优先级）
- 支持的运算符：`+`、`-`、`×`
- `calculate()` 后再输入数字会自动清空旧结果
- `calculate()` 后再输入运算符也会自动清空旧结果

---

## Task C1: calculator.py — 辅助运算模块

### Step 1: 写失败测试

```python
# tests/test_calculator.py
import unittest
from calculator import Calculator


class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_input_single_digit(self):
        """输入单个数字应正确显示"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_digit('0'), '0')

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
        """输入运算符应锁定当前数字"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_operator('+'), '5 +')
        self.assertEqual(self.calc.input_digit('3'), '3')

    def test_backspace(self):
        """回退应删除最后一位"""
        self.assertEqual(self.calc.input_digit('5'), '5')
        self.assertEqual(self.calc.input_digit('3'), '53')
        self.assertEqual(self.calc.backspace(), '5')
        self.assertEqual(self.calc.backspace(), '0')

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
        self.calc.input_digit('5.5')
        self.calc.input_operator('+')
        self.calc.input_digit('8.0')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 13.5)

    def test_calculate_subtraction(self):
        """20 - 7.5 = 12.5"""
        self.calc.input_digit('20')
        self.calc.input_operator('-')
        self.calc.input_digit('7.5')
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
        """按输入顺序计算：5 + 8.0 + 12.0 = 25.0（不是数学优先级）"""
        self.calc.input_digit('5')
        self.calc.input_operator('+')
        self.calc.input_digit('8.0')
        self.calc.input_operator('+')
        self.calc.input_digit('12.0')
        result = self.calc.calculate()
        self.assertAlmostEqual(result, 25.0)

    def test_calculate_sequential_mixed(self):
        """10 + 3 × 2 = 26（按顺序：先 10+3=13，再 13×2=26）"""
        self.calc.input_digit('10')
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
        self.calc.calculate()  # 8
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
```

### Step 2: 运行测试确认失败

Run: `uv run -m pytest tests/test_calculator.py -v`
Expected: FAIL — `ModuleNotFoundError`

### Step 3: 实现 calculator.py

```python
# calculator.py


class Calculator:
    def __init__(self):
        self.expression = []    # [数字, 运算符, 数字, ...]
        self.current_num = ''   # 当前正在输入的数字字符串
        self._result = None     # calculate() 的结果

    def input_digit(self, digit: str) -> str:
        if self._result is not None:
            # 计算完成后输入新数字，清除旧结果
            self.clear()
        if digit == '.' and '.' in self.current_num:
            return self.get_display()
        self.current_num += digit
        return self.get_display()

    def input_operator(self, op: str) -> str:
        if self._result is not None:
            self.clear()
        if self.current_num == '' and not self.expression:
            return self.get_display()
        if self.current_num != '':
            self.expression.append(float(self.current_num))
            self.current_num = ''
        self.expression.append(op)
        return self.get_display()

    def backspace(self) -> str:
        if self.current_num:
            self.current_num = self.current_num[:-1]
        return self.get_display()

    def calculate(self) -> float:
        if self.current_num != '':
            self.expression.append(float(self.current_num))
            self.current_num = ''

        if not self.expression:
            return 0.0

        # 取第一个数字作为初始值
        result = self.expression[0]
        # 按输入顺序计算：[数字, 运算符, 数字, 运算符, 数字, ...]
        i = 1
        while i < len(self.expression):
            op = self.expression[i]
            if i + 1 < len(self.expression):
                next_num = self.expression[i + 1]
            else:
                next_num = result  # 运算符后没有数字，返回当前值
            if op == '+':
                result = result + next_num
            elif op == '-':
                result = result - next_num
            elif op == '×':
                result = result * next_num
            i += 2

        self._result = result
        return result

    def get_display(self) -> str:
        parts = []
        if self.expression:
            parts.append(str(self.expression[0]).rstrip('0').rstrip('.'))
            i = 1
            while i < len(self.expression):
                parts.append(self.expression[i])
                i += 1
                if i < len(self.expression):
                    parts.append(
                        str(self.expression[i]).rstrip('0').rstrip('.')
                    )
                i += 1
        if self.current_num:
            parts.append(self.current_num)
        return ' '.join(parts)

    def clear(self) -> None:
        self.expression = []
        self.current_num = ''
        self._result = None
```

### Step 4: 运行测试确认通过

Run: `uv run -m pytest tests/test_calculator.py -v`
Expected: 17 passed

### Step 5: 提交

```bash
git add calculator.py tests/test_calculator.py
git commit -m "feat: add calculator with sequential evaluation (+, -, ×)"
```

---

## 验收标准 — 人员 C

| # | 验收项 | 验证命令/操作 | 预期结果 |
|---|--------|-------------|---------|
| C-1 | 模块可导入 | `uv run -c "from calculator import Calculator; print('OK')"` | 输出 `OK` |
| C-2 | 单元测试全部通过 | `uv run -m pytest tests/test_calculator.py -v` | 17 passed |
| C-3 | 加法正确 | 测试 `5.5 + 8.0` | 13.5 |
| C-4 | 减法正确 | 测试 `20 - 7.5` | 12.5 |
| C-5 | 乘法正确 | 测试 `3 × 4` | 12.0 |
| C-6 | 按输入顺序计算 | 测试 `10 + 3 × 2` | 26.0（非 16） |
| C-7 | 连续多步运算 | 测试 `5 + 8 + 12` | 25.0 |
| C-8 | 计算后输入清空 | `calculate()` 后 `input_digit('1')` | 显示 `1` |
