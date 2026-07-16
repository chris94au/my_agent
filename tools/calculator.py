import ast
import operator

from .registry import Tool, ToolParameter


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class CalculatorError(Exception):
    pass



def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.Num):
        return node.n

    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        return ALLOWED_OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
        operand = _evaluate(node.operand)
        return ALLOWED_OPERATORS[type(node.op)](operand)

    raise CalculatorError("Unsupported expression")



def calculator(expression):
    try:
        tree = ast.parse(str(expression), mode="eval")
        result = _evaluate(tree)
        return str(result)
    except Exception as e:
        return f"Fehler beim Rechnen: {e}"


calculator_tool = Tool(
    name="calculator",
    description="Berechnet mathematische Ausdrücke.",
    parameters=[
        ToolParameter(
            name="expression",
            type="string",
            required=True,
            description="Mathematischer Ausdruck"
        )
    ],
    execute_fn=lambda data: calculator(
        data["expression"] if isinstance(data, dict) else data
    ),
    permission="math",
    requires_confirmation=False,
    accepts_scalar=True,
)


tool = calculator_tool
