
import ast
import math
import operator
import re


# Supported arithmetic operations.
OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}

# Matches identifiers and simple numeric/string/Boolean literals.
OPERAND = (
    r"""(?:'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|"""
    r"""-?(?:\d+(?:\.\d*)?|\.\d+)|True|False|"""
    r"""[A-Za-z_]\w*)"""
)

ASSIGNMENT_PATTERN = re.compile(
    rf"^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*$"
)

BINARY_PATTERN = re.compile(
    rf"^\s*({OPERAND})\s*([+\-*/])\s*({OPERAND})\s*$"
)

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_]\w*$")


def parse_literal(value):
    """Parse a literal safely without executing source code."""
    try:
        result = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return None, False

    if isinstance(result, (int, float, str, bool)):
        return result, True

    return None, False


def format_literal(value):
    """Convert a supported constant back to TAC text."""
    return repr(value)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def fold_operation(left, op, right):
    """Calculate a supported operation only when it is safe."""
    if op not in OPERATORS:
        return None, False

    # Numeric arithmetic.
    if is_number(left) and is_number(right):
        if op == "/" and right == 0:
            return None, False

        try:
            result = OPERATORS[op](left, right)
        except (ArithmeticError, OverflowError, TypeError):
            return None, False

        if isinstance(result, float) and not math.isfinite(result):
            return None, False

        return result, True

    # String concatenation is supported by our language.
    if op == "+" and isinstance(left, str) and isinstance(right, str):
        return left + right, True

    return None, False


class TACOptimizer:
    def __init__(self):
        self.optimization_log = []

    def optimize(self, instructions):
        """
        Optimize straight-line TAC using constant folding
        and constant propagation.
        """
        self.optimization_log = []
        constants = {}
        optimized = []

        for instruction in instructions:
            line = instruction.strip()

            if not line:
                continue

            # Preserve print instructions while substituting known constants.
            if line.startswith("print "):
                operand = line[len("print "):].strip()
                operand = self.replace_constant(operand, constants)
                optimized.append(f"print {operand}")
                continue

            match = ASSIGNMENT_PATTERN.fullmatch(line)

            if not match:
                # Keep unknown instruction formats unchanged.
                optimized.append(line)
                continue

            target, expression = match.groups()

            # Invalidate the old value before processing reassignment.
            constants.pop(target, None)

            binary_match = BINARY_PATTERN.fullmatch(expression)

            if binary_match:
                left_text, op, right_text = binary_match.groups()

                left_text = self.replace_constant(left_text, constants)
                right_text = self.replace_constant(right_text, constants)

                left_value, left_is_constant = parse_literal(left_text)
                right_value, right_is_constant = parse_literal(right_text)

                if left_is_constant and right_is_constant:
                    result, succeeded = fold_operation(
                        left_value, op, right_value
                    )

                    if succeeded:
                        expression = format_literal(result)
                        constants[target] = result
                        self.optimization_log.append(
                            f"{target}: folded {left_text} {op} "
                            f"{right_text} into {expression}"
                        )
                    else:
                        expression = (
                            f"{left_text} {op} {right_text}"
                        )
                else:
                    expression = f"{left_text} {op} {right_text}"

            else:
                expression = self.replace_constant(expression, constants)
                value, is_constant = parse_literal(expression)

                if is_constant:
                    constants[target] = value

            optimized.append(f"{target} = {expression}")

        return optimized

    @staticmethod
    def replace_constant(operand, constants):
        """Replace a variable with its known constant value."""
        operand = operand.strip()

        if IDENTIFIER_PATTERN.fullmatch(operand):
            if operand in constants:
                return format_literal(constants[operand])

        return operand


def optimize_tac(instructions):
    """Convenience function for optimizing TAC instructions."""
    optimizer = TACOptimizer()
    return optimizer.optimize(instructions)
