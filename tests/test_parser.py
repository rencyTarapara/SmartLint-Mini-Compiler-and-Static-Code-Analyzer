"""
Comprehensive parser tests for SmartLint.
"""
import pytest
from compiler.parser import parse_source


def parse_ok(source):
    """Parse source, assert no errors, return AST."""
    if not source.endswith("\n"):
        source += "\n"
    ast, errors = parse_source(source)
    assert not errors, f"Unexpected parse errors: {errors}"
    return ast


def parse_errs(source):
    """Parse source, return errors (expect at least one)."""
    if not source.endswith("\n"):
        source += "\n"
    ast, errors = parse_source(source)
    return errors


# ---------------------------------------------------------------------------
# Basic assignment
# ---------------------------------------------------------------------------

def test_assignment_integer():
    ast = parse_ok("x = 10\n")
    assert ast[0]["type"] == "assign"
    assert ast[0]["name"] == "x"
    assert ast[0]["value"] == {"type": "number", "value": 10, "line": 1}


def test_assignment_float():
    ast = parse_ok("x = 3.14\n")
    assert ast[0]["value"]["value"] == 3.14


def test_assignment_string():
    ast = parse_ok('x = "hello"\n')
    assert ast[0]["value"]["type"] == "string"
    assert ast[0]["value"]["value"] == "hello"


def test_assignment_boolean_true():
    ast = parse_ok("x = True\n")
    assert ast[0]["value"]["type"] == "boolean"
    assert ast[0]["value"]["value"] is True


def test_assignment_boolean_false():
    ast = parse_ok("x = False\n")
    assert ast[0]["value"]["value"] is False


# ---------------------------------------------------------------------------
# Print statement
# ---------------------------------------------------------------------------

def test_print():
    ast = parse_ok("print(42)\n")
    assert ast[0]["type"] == "print"
    assert ast[0]["value"]["value"] == 42


# ---------------------------------------------------------------------------
# Arithmetic operators
# ---------------------------------------------------------------------------

def test_addition():
    ast = parse_ok("x = 2 + 3\n")
    node = ast[0]["value"]
    assert node["type"] == "binary"
    assert node["operator"] == "+"


def test_subtraction():
    ast = parse_ok("x = 10 - 3\n")
    assert ast[0]["value"]["operator"] == "-"


def test_multiplication():
    ast = parse_ok("x = 4 * 5\n")
    assert ast[0]["value"]["operator"] == "*"


def test_true_division():
    ast = parse_ok("x = 10 / 4\n")
    assert ast[0]["value"]["operator"] == "/"


def test_floor_division():
    ast = parse_ok("x = 10 // 3\n")
    node = ast[0]["value"]
    assert node["type"] == "binary"
    assert node["operator"] == "//"


def test_modulo():
    ast = parse_ok("x = 10 % 3\n")
    assert ast[0]["value"]["operator"] == "%"


def test_exponentiation():
    ast = parse_ok("x = 2 ** 3\n")
    node = ast[0]["value"]
    assert node["type"] == "binary"
    assert node["operator"] == "**"


# ---------------------------------------------------------------------------
# Operator precedence
# ---------------------------------------------------------------------------

def test_precedence_mul_over_add():
    """2 + 3 * 4: the * should be deeper in the AST than +."""
    ast = parse_ok("x = 2 + 3 * 4\n")
    root = ast[0]["value"]
    # root is +: left=2, right=(3*4)
    assert root["operator"] == "+"
    assert root["left"]["value"] == 2
    assert root["right"]["operator"] == "*"


def test_precedence_grouped():
    """(2 + 3) * 4: the + should be deeper than *."""
    ast = parse_ok("x = (2 + 3) * 4\n")
    root = ast[0]["value"]
    assert root["operator"] == "*"
    assert root["left"]["operator"] == "+"
    assert root["right"]["value"] == 4


def test_precedence_pow_right_assoc():
    """2 ** 3 ** 2 == 2 ** (3 ** 2) → right child of outer ** is 3**2."""
    ast = parse_ok("x = 2 ** 3 ** 2\n")
    root = ast[0]["value"]
    assert root["operator"] == "**"
    assert root["left"]["value"] == 2
    assert root["right"]["operator"] == "**"
    assert root["right"]["left"]["value"] == 3
    assert root["right"]["right"]["value"] == 2


def test_unary_minus_lower_than_pow():
    """-2**2 → -(2**2): unary is the ROOT, ** inside."""
    ast = parse_ok("x = -2 ** 2\n")
    root = ast[0]["value"]
    assert root["type"] == "unary"
    assert root["operator"] == "-"
    assert root["value"]["operator"] == "**"


def test_grouped_unary_pow():
    """(-2)**2: unary is INSIDE the **."""
    ast = parse_ok("x = (-2) ** 2\n")
    root = ast[0]["value"]
    assert root["operator"] == "**"
    assert root["left"]["type"] == "unary"
    assert root["left"]["operator"] == "-"


def test_left_assoc_subtraction():
    """10 - 3 - 2 → (10 - 3) - 2: left-associative."""
    ast = parse_ok("x = 10 - 3 - 2\n")
    root = ast[0]["value"]
    # root is -: left is also - (10-3), right is 2
    assert root["operator"] == "-"
    assert root["right"]["value"] == 2
    assert root["left"]["operator"] == "-"


def test_left_assoc_floordiv_mod():
    """24 // 5 % 3 → (24 // 5) % 3."""
    ast = parse_ok("x = 24 // 5 % 3\n")
    root = ast[0]["value"]
    assert root["operator"] == "%"
    assert root["left"]["operator"] == "//"


# ---------------------------------------------------------------------------
# Unary operators
# ---------------------------------------------------------------------------

def test_unary_plus():
    ast = parse_ok("x = +5\n")
    root = ast[0]["value"]
    assert root["type"] == "unary"
    assert root["operator"] == "+"


def test_unary_minus():
    ast = parse_ok("x = -5\n")
    root = ast[0]["value"]
    assert root["type"] == "unary"
    assert root["operator"] == "-"


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------

def test_compare_gt():
    ast = parse_ok("x = 5 > 3\n")
    assert ast[0]["value"]["type"] == "compare"
    assert ast[0]["value"]["operator"] == ">"


def test_compare_ge():
    ast = parse_ok("x = 5 >= 3\n")
    assert ast[0]["value"]["operator"] == ">="


def test_compare_lt():
    ast = parse_ok("x = 3 < 5\n")
    assert ast[0]["value"]["operator"] == "<"


def test_compare_le():
    ast = parse_ok("x = 4 <= 4\n")
    assert ast[0]["value"]["operator"] == "<="


def test_compare_eq():
    ast = parse_ok("x = 5 == 5\n")
    assert ast[0]["value"]["operator"] == "=="


def test_compare_ne():
    ast = parse_ok("x = 5 != 3\n")
    assert ast[0]["value"]["operator"] == "!="


# ---------------------------------------------------------------------------
# Logical operators
# ---------------------------------------------------------------------------

def test_logical_and():
    ast = parse_ok("x = True and False\n")
    assert ast[0]["value"]["type"] == "logical_and"


def test_logical_or():
    ast = parse_ok("x = True or False\n")
    assert ast[0]["value"]["type"] == "logical_or"


def test_logical_not():
    ast = parse_ok("x = not True\n")
    assert ast[0]["value"]["type"] == "logical_not"


def test_logical_complex():
    ast = parse_ok("x = (5 > 3) and (2 < 4)\n")
    root = ast[0]["value"]
    assert root["type"] == "logical_and"
    assert root["left"]["type"] == "compare"
    assert root["right"]["type"] == "compare"


# ---------------------------------------------------------------------------
# Compound assignments
# ---------------------------------------------------------------------------

def test_compound_plus_eq():
    ast = parse_ok("x = 10\nx += 5\n")
    node = ast[1]
    assert node["type"] == "compound"
    assert node["name"] == "x"
    assert node["operator"] == "+"


def test_compound_minus_eq():
    ast = parse_ok("x = 10\nx -= 2\n")
    assert ast[1]["operator"] == "-"


def test_compound_times_eq():
    ast = parse_ok("x = 10\nx *= 3\n")
    assert ast[1]["operator"] == "*"


def test_compound_divide_eq():
    ast = parse_ok("x = 10\nx /= 2\n")
    assert ast[1]["operator"] == "/"


def test_compound_floordiv_eq():
    ast = parse_ok("x = 10\nx //= 3\n")
    assert ast[1]["operator"] == "//"


def test_compound_mod_eq():
    ast = parse_ok("x = 10\nx %= 3\n")
    assert ast[1]["operator"] == "%"


def test_compound_pow_eq():
    ast = parse_ok("x = 2\nx **= 8\n")
    assert ast[1]["operator"] == "**"


# ---------------------------------------------------------------------------
# Syntax errors
# ---------------------------------------------------------------------------

def test_syntax_error_missing_rhs():
    errors = parse_errs("x =\n")
    assert errors
    assert errors[0]["severity"] == "ERROR"
    assert errors[0]["category"] == "SYNTAX"


def test_syntax_error_operator_only():
    errors = parse_errs("x = * 3\n")
    assert errors


def test_syntax_error_missing_closing_paren():
    errors = parse_errs("x = (2 + 3\n")
    assert errors


def test_syntax_error_dangling_operator():
    errors = parse_errs("x = 5 +\n")
    assert errors


def test_syntax_error_double_exponent():
    errors = parse_errs("x = 2 **\n")
    assert errors


# ---------------------------------------------------------------------------
# Multi-statement programs
# ---------------------------------------------------------------------------

def test_multi_statement():
    ast = parse_ok("x = 10\ny = 20\nz = x + y\n")
    assert len(ast) == 3
    assert ast[2]["value"]["type"] == "binary"


def test_blank_lines_ignored():
    ast = parse_ok("\nx = 10\n\ny = 20\n")
    assert len(ast) == 2


def test_line_numbers_recorded():
    ast = parse_ok("x = 10\ny = 20\n")
    assert ast[0]["line"] == 1
    assert ast[1]["line"] == 2
