"""Evaluate a small arithmetic expression without eval().

Only names, numbers, + - * / **, unary +/- and a whitelist of functions are allowed.
"""
import ast


class ExpressionError(ValueError):
    pass


_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
}


def evaluate(text, names, functions=None, number=lambda value: value):
    """Evaluate `text` with `names` (symbol -> value) and `functions` (name -> callable)."""
    functions = functions or {}
    try:
        tree = ast.parse(text.strip(), mode='eval')
    except SyntaxError as error:
        raise ExpressionError(f'cannot parse expression: {text!r}') from error

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return number(node.value)
        if isinstance(node, ast.Name):
            if node.id not in names:
                raise ExpressionError(f'undeclared symbol: {node.id}')
            return names[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            right = walk(node.right)
            if isinstance(node.op, ast.Pow):
                if not isinstance(node.right, ast.Constant) and not (
                        isinstance(node.right, ast.UnaryOp) and isinstance(node.right.operand, ast.Constant)):
                    raise ExpressionError('exponents must be numeric constants')
                right = _plain_number(node.right)
            return _BINOPS[type(node.op)](walk(node.left), right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions and not node.keywords:
            return functions[node.func.id](*[walk(arg) for arg in node.args])
        raise ExpressionError(f'unsupported syntax: {ast.dump(node)[:80]}')

    return walk(tree)


def _plain_number(node):
    if isinstance(node, ast.Constant):
        return node.value
    value = node.operand.value
    return -value if isinstance(node.op, ast.USub) else value


def parse_assignments(items, separator):
    """Parse ["a:m/s", "b:kg"] into {"a": "m/s", "b": "kg"}."""
    result = {}
    for item in items:
        for part in item.split(','):
            part = part.strip()
            if not part:
                continue
            if separator not in part:
                raise ExpressionError(f'expected name{separator}value, got {part!r}')
            name, value = part.split(separator, 1)
            result[name.strip()] = value.strip()
    return result
