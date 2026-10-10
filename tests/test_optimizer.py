"""
Comprehensive optimizer tests for SmartLint.
"""
import pytest
from compiler.optimizer import optimize_tac


def opt(instructions):
    """Run optimizer and return result."""
    return optimize_tac(instructions)


# ---------------------------------------------------------------------------
# Constant folding — arithmetic
# ---------------------------------------------------------------------------

def test_fold_addition():
    assert opt(["t1 = 2 + 3"]) == ["t1 = 5"]


def test_fold_subtraction():
    assert opt(["t1 = 10 - 3"]) == ["t1 = 7"]


def test_fold_multiplication():
    assert opt(["t1 = 4 * 5"]) == ["t1 = 20"]


def test_fold_true_division():
    assert opt(["t1 = 10 / 4"]) == [f"t1 = {repr(2.5)}"]


def test_fold_floor_division():
    assert opt(["t1 = 10 // 3"]) == ["t1 = 3"]


def test_fold_modulo():
    assert opt(["t1 = 10 % 3"]) == ["t1 = 1"]


def test_fold_exponentiation():
    assert opt(["t1 = 2 ** 10"]) == ["t1 = 1024"]


def test_constant_folding_chain():
    """Full constant folding + propagation chain."""
    tac = [
        "t1 = 20 * 3",
        "t2 = 10 + t1",
        "x = t2",
    ]
    result = opt(tac)
    assert result == ["t1 = 60", "t2 = 70", "x = 70"]


# ---------------------------------------------------------------------------
# Constant propagation
# ---------------------------------------------------------------------------

def test_constant_propagation():
    result = opt(["x = 10", "y = x", "print y"])
    assert result == ["x = 10", "y = 10", "print 10"]


def test_constant_propagation_chain():
    result = opt(["a = 5", "b = a", "c = b + 0"])
    assert result == ["a = 5", "b = 5", "c = 5"]


def test_variable_reassignment():
    """Stale constant must NOT be propagated after reassignment."""
    result = opt(["x = 10", "x = 20", "y = x + 5"])
    assert result == ["x = 10", "x = 20", "y = 25"]


# ---------------------------------------------------------------------------
# Copy propagation
# ---------------------------------------------------------------------------

def test_copy_propagation():
    result = opt(["a = x", "b = a + 2"])
    # a is a copy of x, so b = x + 2 (or kept if x unknown)
    # At minimum, a = x must be preserved and b = a + 2 preserved
    assert "a = x" in result


# ---------------------------------------------------------------------------
# Division-by-zero safety
# ---------------------------------------------------------------------------

def test_division_by_zero_not_folded():
    assert opt(["x = 10 / 0"]) == ["x = 10 / 0"]


def test_floor_division_by_zero_not_folded():
    assert opt(["x = 10 // 0"]) == ["x = 10 // 0"]


def test_modulo_by_zero_not_folded():
    assert opt(["x = 10 % 0"]) == ["x = 10 % 0"]


# ---------------------------------------------------------------------------
# Algebraic simplification
# ---------------------------------------------------------------------------

def test_add_zero_right():
    result = opt(["t1 = x + 0"])
    assert result == ["t1 = x"]


def test_add_zero_left():
    result = opt(["t1 = 0 + x"])
    assert result == ["t1 = x"]


def test_subtract_zero():
    result = opt(["t1 = x - 0"])
    assert result == ["t1 = x"]


def test_multiply_by_one_right():
    result = opt(["t1 = x * 1"])
    assert result == ["t1 = x"]


def test_multiply_by_one_left():
    result = opt(["t1 = 1 * x"])
    assert result == ["t1 = x"]


def test_multiply_by_zero():
    result = opt(["t1 = x * 0"])
    assert result == ["t1 = 0"]


def test_multiply_by_zero_left():
    result = opt(["t1 = 0 * x"])
    assert result == ["t1 = 0"]


def test_divide_by_one():
    result = opt(["t1 = x / 1"])
    assert result == ["t1 = x"]


def test_pow_to_zero():
    result = opt(["t1 = x ** 0"])
    assert result == ["t1 = 1"]


def test_pow_to_one():
    result = opt(["t1 = x ** 1"])
    assert result == ["t1 = x"]


def test_one_pow_any():
    result = opt(["t1 = 1 ** x"])
    assert result == ["t1 = 1"]


# ---------------------------------------------------------------------------
# Unary minus folding
# ---------------------------------------------------------------------------

def test_unary_negative_literal():
    result = opt(["t1 = -5", "x = t1"])
    assert result == ["t1 = -5", "x = -5"]


def test_unary_minus_propagation():
    result = opt(["t1 = -5", "t2 = t1 * 2"])
    assert result == ["t1 = -5", "t2 = -10"]


# ---------------------------------------------------------------------------
# Comparison folding
# ---------------------------------------------------------------------------

def test_comparison_gt_folded():
    result = opt(["t1 = 5 > 3"])
    assert result == ["t1 = True"]


def test_comparison_lt_folded():
    result = opt(["t1 = 3 < 2"])
    assert result == ["t1 = False"]


def test_comparison_eq_folded():
    result = opt(["t1 = 5 == 5"])
    assert result == ["t1 = True"]


def test_comparison_ne_folded():
    result = opt(["t1 = 5 != 3"])
    assert result == ["t1 = True"]


def test_comparison_le_folded():
    result = opt(["t1 = 4 <= 4"])
    assert result == ["t1 = True"]


def test_comparison_ge_folded():
    result = opt(["t1 = 7 >= 8"])
    assert result == ["t1 = False"]


# ---------------------------------------------------------------------------
# Boolean / logical folding
# ---------------------------------------------------------------------------

def test_bool_and_folded():
    result = opt(["t1 = True and False"])
    assert result == ["t1 = False"]


def test_bool_or_folded():
    result = opt(["t1 = False or True"])
    assert result == ["t1 = True"]


def test_bool_not_folded():
    result = opt(["t1 = not True"])
    assert result == ["t1 = False"]


def test_bool_not_false_folded():
    result = opt(["t1 = not False"])
    assert result == ["t1 = True"]


# ---------------------------------------------------------------------------
# String concatenation
# ---------------------------------------------------------------------------

def test_string_concatenation():
    result = opt(["t1 = 'hello' + ' world'", "print t1"])
    assert result == ["t1 = 'hello world'", "print 'hello world'"]


def test_string_concat_propagated():
    result = opt(["t1 = 'a' + 'b'", "x = t1"])
    assert result == ["t1 = 'ab'", "x = 'ab'"]


# ---------------------------------------------------------------------------
# Non-constant expressions preserved
# ---------------------------------------------------------------------------

def test_nonconstant_preserved():
    result = opt(["t1 = x + 5"])
    assert result == ["t1 = x + 5"]


def test_two_variables_preserved():
    result = opt(["t1 = x + y"])
    assert result == ["t1 = x + y"]


# ---------------------------------------------------------------------------
# Exponentiation safety
# ---------------------------------------------------------------------------

def test_huge_exponent_not_folded():
    """2 ** 9999 would OOM; optimizer must leave it unchanged."""
    result = opt(["t1 = 2 ** 9999"])
    assert result == ["t1 = 2 ** 9999"]


def test_zero_to_negative_not_folded():
    """0 ** -1 raises ZeroDivisionError; must not fold."""
    result = opt(["t1 = 0 ** -1"])
    assert result == ["t1 = 0 ** -1"]


# ---------------------------------------------------------------------------
# Print instruction handling
# ---------------------------------------------------------------------------

def test_print_with_constant_propagation():
    result = opt(["x = 42", "print x"])
    assert result == ["x = 42", "print 42"]


def test_print_non_constant_preserved():
    result = opt(["print x"])
    assert result == ["print x"]


# ---------------------------------------------------------------------------
# Multi-pass stability
# ---------------------------------------------------------------------------

def test_multi_pass_is_stable():
    """Running optimizer twice should give the same result."""
    tac = ["t1 = 2 + 3", "t2 = t1 * 4", "x = t2"]
    first = opt(tac)
    second = opt(first)
    assert first == second
