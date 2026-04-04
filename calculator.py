# calculator.py
# POS 机风格辅助运算模块：按输入顺序从左到右计算，不遵循数学优先级。


class Calculator:
    def __init__(self):
        self.expression = []    # [数字, 运算符, 数字, ...]
        self.current_num = ''   # 当前正在输入的数字字符串
        self._result = None     # calculate() 的结果

    def input_digit(self, digit: str) -> str:
        """输入一个数字字符（0-9 或 '.'），返回当前正在输入的数字串。"""
        if self._result is not None:
            # 计算完成后输入新数字，清除旧结果
            self.clear()
        if digit == '.' and '.' in self.current_num:
            return self.current_num
        self.current_num += digit
        return self.current_num

    def input_operator(self, op: str) -> str:
        """输入运算符（'+', '-', '×'），锁定当前数字，返回当前显示内容。"""
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
        """删除当前输入的最后一个字符，空时返回 '0'。"""
        if self.current_num:
            self.current_num = self.current_num[:-1]
        return self.current_num if self.current_num else '0'

    def calculate(self) -> float:
        """按输入顺序从左到右计算结果，返回 float。"""
        if self.current_num != '':
            self.expression.append(float(self.current_num))
            self.current_num = ''

        if not self.expression:
            return 0.0

        # 取第一个数字作为初始值
        result = self.expression[0]
        i = 1
        while i < len(self.expression):
            op = self.expression[i]
            if i + 1 < len(self.expression):
                next_num = self.expression[i + 1]
                i += 2
            else:
                # 运算符后没有第二操作数，直接返回当前值
                break
            if op == '+':
                result = result + next_num
            elif op == '-':
                result = result - next_num
            elif op == '×':
                result = result * next_num

        self._result = result
        return result

    def get_display(self) -> str:
        """返回当前完整显示字符串，例如 '5 + 3'。"""
        parts = []
        if self.expression:
            # 首个数字
            parts.append(self._fmt(self.expression[0]))
            i = 1
            while i < len(self.expression):
                parts.append(self.expression[i])   # 运算符
                i += 1
                if i < len(self.expression):
                    parts.append(self._fmt(self.expression[i]))
                i += 1
        if self.current_num:
            parts.append(self.current_num)
        return ' '.join(parts)

    def clear(self) -> None:
        """重置所有状态。"""
        self.expression = []
        self.current_num = ''
        self._result = None

    # ── 内部工具 ──────────────────────────────────────────
    @staticmethod
    def _fmt(value: float) -> str:
        """将 float 格式化为简洁字符串（去除多余的 .0）。"""
        return str(value).rstrip('0').rstrip('.')
