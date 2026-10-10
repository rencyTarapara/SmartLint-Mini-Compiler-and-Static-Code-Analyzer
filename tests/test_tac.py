"""
Comprehensive TAC generation tests for SmartLint.
"""
import pytest
from compiler.parser import parse_source
from compiler.tac import generate_tac


def get_tac(source: str) -> list[str]:
    """Parse source and return generated TAC instructions."""
    if not source.endswith("\n"):
        source += "\n"
    ast, errors = parse_source(source)
    assert not errors, f"Unexpected syntax errors: {errors}"
    return generate_tac(ast)


# ---------------------------------------------------------------------------
# Basic assignments
# ---------------------------------------------------------------------------

def test_simple_assignment_int():
    assert get_tac("x = 10\n") == ["x = 10"]


def test_simple_assignment_float():
    assert get_tac("x = 3.14\n") == ["x = 3.14"]


def test_simple_assignment_bool():
    assert get_tac("x = True\n") == ["x = True"]


def test_simple_assignment_string():
    tac = get_tac('x = "hello"\n')
    assert tac == ["x = 'hello'"]


# ---------------------------------------------------------------------------
# Arithmetic operators — TAC shape
# ---------------------------------------------------------------------------

def test_addition_tac():
    tac = get_tac("x = 2 + 3\n")
    assert "t1 = 2 + 3" in tac
    assert "x = t1" in tac


def test_floor_division_tac():
    tac = get_tac("x = 10 // 3\n")
    assert "t1 = 10 // 3" in tac


def test_modulo_tac():
    tac = get_tac("x = 10 % 3\n")
    assert "t1 = 10 % 3" in tac


def test_exponentiation_tac():
    tac = get_tac("x = 2 ** 3\n")
    assert "t1 = 2 ** 3" in tac


# ---------------------------------------------------------------------------
# Operator precedence preserved in TAC
# ---------------------------------------------------------------------------

def test_operator_precedence():
    """x = 10 + 20 * 3  →  multiplication goes first."""
    tac = get_tac("x = 10 + 20 * 3\n")
    assert tac == [
        "t1 = 20 * 3",
        "t2 = 10 + t1",
        "x = t2",
    ]


def test_grouped_precedence():
    """x = (10 + 20) * 3  →  addition goes first."""
    tac = get_tac("x = (10 + 20) * 3\n")
    assert tac == [
        "t1 = 10 + 20",
        "t2 = t1 * 3",
        "x = t2",
    ]


def test_pow_right_assoc_tac():
    """x = 2 ** 3 ** 2  →  inner first: t1 = 3**2, t2 = 2**t1."""
    tac = get_tac("x = 2 ** 3 ** 2\n")
    assert tac == [
        "t1 = 3 ** 2",
        "t2 = 2 ** t1",
        "x = t2",
    ]


def test_unary_minus_lower_than_pow_tac():
    """-2**2  →  ** goes first, then unary."""
    tac = get_tac("x = -2 ** 2\n")
    assert tac == [
        "t1 = 2 ** 2",
        "t2 = -t1",
        "x = t2",
    ]


def test_grouped_unary_pow_tac():
    """(-2)**2 → unary first, then **."""
    tac = get_tac("x = (-2) ** 2\n")
    assert tac == [
        "t1 = -2",
        "t2 = t1 ** 2",
        "x = t2",
    ]


# ---------------------------------------------------------------------------
# Unary operators
# ---------------------------------------------------------------------------

def test_unary_minus_literal():
    """x = -5  →  t1 = -5  (literal fold, no intermediate)."""
    tac = get_tac("x = -5\n")
    assert tac == ["t1 = -5", "x = t1"]


def test_unary_plus_is_noop():
    """x = +5  →  no extra instruction for unary +."""
    tac = get_tac("x = +5\n")
    assert tac == ["x = 5"]


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------

def test_compare_gt_tac():
    tac = get_tac("x = 5 > 3\n")
    assert tac == ["t1 = 5 > 3", "x = t1"]


def test_compare_ge_tac():
    tac = get_tac("x = 5 >= 3\n")
    assert "t1 = 5 >= 3" in tac


def test_compare_eq_tac():
    tac = get_tac("x = 5 == 5\n")
    assert "t1 = 5 == 5" in tac


# ---------------------------------------------------------------------------
# Logical operators
# ---------------------------------------------------------------------------

def test_logical_and_tac():
    tac = get_tac("x = True and False\n")
    assert any("and" in instr for instr in tac)


def test_logical_or_tac():
    tac = get_tac("x = True or False\n")
    assert any("or" in instr for instr in tac)


def test_logical_not_tac():
    tac = get_tac("x = not True\n")
    assert any("not" in instr for instr in tac)


def test_logical_complex_tac():
    tac = get_tac("x = (5 > 3) and (2 < 4)\n")
    # should produce: t1 = 5>3, t2 = 2<4, t3 = t1 and t2, x = t3
    assert any("and" in instr for instr in tac)


# ---------------------------------------------------------------------------
# Compound assignments
# ---------------------------------------------------------------------------

def test_compound_plus_eq_tac():
    tac = get_tac("x = 10\nx += 5\n")
    assert tac == ["x = 10", "t1 = x + 5", "x = t1"]


def test_compound_minus_eq_tac():
    tac = get_tac("x = 10\nx -= 3\n")
    assert tac == ["x = 10", "t1 = x - 3", "x = t1"]


def test_compound_times_eq_tac():
    tac = get_tac("x = 4\nx *= 3\n")
    assert tac == ["x = 4", "t1 = x * 3", "x = t1"]


def test_compound_floordiv_eq_tac():
    tac = get_tac("x = 10\nx //= 3\n")
    assert tac == ["x = 10", "t1 = x // 3", "x = t1"]


def test_compound_pow_eq_tac():
    tac = get_tac("x = 2\nx **= 8\n")
    assert tac == ["x = 2", "t1 = x ** 8", "x = t1"]


# ---------------------------------------------------------------------------
# Print statement
# ---------------------------------------------------------------------------

def test_print_variable():
    tac = get_tac("x = 5\nprint(x)\n")
    assert tac == ["x = 5", "print x"]


def test_print_expression():
    tac = get_tac("print(2 + 3)\n")
    assert "print t1" in tac


# ---------------------------------------------------------------------------
# Multi-statement
# ---------------------------------------------------------------------------

def test_blank_lines():
    tac = get_tac("\nx = 10\n\nprint(x)\n")
    assert tac == ["x = 10", "print x"]


def test_string_concatenation_tac():
    tac = get_tac('x = "hello" + " world"\n')
    assert tac[0] == "t1 = 'hello' + ' world'"
