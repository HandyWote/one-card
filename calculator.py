class Calculator:
    def __init__(self):
        self.expression = []    # [数字, 运算符, 数字, ...]
        self.current_num = ''   # 当前正在输入的数字字符串
        self._result = None     # calculate() 的结果，非 None 表示刚计算完

    def input_digit(self, digit: str) -> str:
        if self._result is not None:
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

        # 过滤尾部运算符（只有运算符没有第二操作数时，忽略该运算符）
        while self.expression and isinstance(self.expression[-1], str):
            self.expression.pop()

        if not self.expression:
            return 0.0

        result = self.expression[0]
        i = 1
        while i < len(self.expression):
            op = self.expression[i]
            next_num = self.expression[i + 1] if i + 1 < len(self.expression) else None
            if next_num is None:
                break
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
        # 有当前输入中的数字时，只显示当前数字
        if self.current_num:
            return self.current_num
        # 否则从 expression 构建显示
        if not self.expression:
            return ''
        parts = []
        i = 0
        while i < len(self.expression):
            item = self.expression[i]
            if isinstance(item, float):
                # 去掉多余的 .0
                s = f'{item:g}'
                parts.append(s)
            else:
                parts.append(item)
            i += 1
        return ' '.join(parts)

    def clear(self) -> None:
        self.expression = []
        self.current_num = ''
        self._result = None
