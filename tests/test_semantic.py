"""
Comprehensive semantic analysis tests for SmartLint.
"""
import pytest
from compiler.parser import parse_source
from compiler.semantic import analyze_ast


def analyze(source: str):
    """Parse and analyze source; return (symbol_table, diagnostics)."""
    if not source.endswith("\n"):
        source += "\n"
    ast, parse_errors = parse_source(source)
    assert not parse_errors, f"Unexpected parse errors: {parse_errors}"
    return analyze_ast(ast)


def errors_of(source: str):
    """Return only ERROR diagnostics."""
    _, diags = analyze(source)
    return [d for d in diags if d["severity"] == "ERROR"]


def warnings_of(source: str):
    """Return only WARNING diagnostics."""
    _, diags = analyze(source)
    return [d for d in diags if d["severity"] == "WARNING"]


# ---------------------------------------------------------------------------
# Symbol table
# ---------------------------------------------------------------------------

def test_symbol_table_int():
    sym, diags = analyze("x = 10\n")
    assert sym["x"]["type"] == "int"
    assert not diags


def test_symbol_table_float():
    sym, diags = analyze("x = 3.14\n")
    assert sym["x"]["type"] == "float"


def test_symbol_table_str():
    sym, diags = analyze('x = "hello"\n')
    assert sym["x"]["type"] == "str"


def test_symbol_table_bool():
    sym, diags = analyze("x = True\n")
    assert sym["x"]["type"] == "bool"


def test_symbol_table_multiple():
    sym, diags = analyze("x = 10\ny = 2.5\n")
    assert sym["x"]["type"] == "int"
    assert sym["y"]["type"] == "float"
    assert not diags


# ---------------------------------------------------------------------------
# Undefined variable
# ---------------------------------------------------------------------------

def test_undefined_variable():
    errs = errors_of("print(x)\n")
    assert any("used before it is defined" in e["message"] for e in errs)


def test_undefined_in_expression():
    errs = errors_of("x = y + 1\n")
    assert any("'y'" in e["message"] for e in errs)


def test_defined_then_used():
    sym, diags = analyze("x = 5\ny = x + 1\n")
    assert not errors_of("x = 5\ny = x + 1\n")


# ---------------------------------------------------------------------------
# Type checking — arithmetic
# ---------------------------------------------------------------------------

def test_string_subtraction_invalid():
    errs = errors_of('x = "hello" - 2\n')
    assert any("cannot be applied" in e["message"] for e in errs)


def test_string_multiplication_invalid():
    errs = errors_of('x = "hello" * 2\n')
    assert any("cannot be applied" in e["message"] for e in errs)


def test_string_concat_valid():
    sym, diags = analyze('x = "hello" + " world"\n')
    assert sym["x"]["type"] == "str"
    assert not [d for d in diags if d["severity"] == "ERROR"]


def test_numeric_arithmetic_int():
    sym, _ = analyze("x = 10 + 5\n")
    assert sym["x"]["type"] == "int"


def test_numeric_arithmetic_float():
    sym, _ = analyze("x = 10 + 5.0\n")
    assert sym["x"]["type"] == "float"


def test_division_always_float():
    sym, _ = analyze("x = 10 / 4\n")
    assert sym["x"]["type"] == "float"


def test_floor_division_int_int():
    sym, _ = analyze("x = 10 // 3\n")
    assert sym["x"]["type"] == "int"


def test_modulo_int_int():
    sym, _ = analyze("x = 10 % 3\n")
    assert sym["x"]["type"] == "int"


def test_exponentiation_int():
    sym, _ = analyze("x = 2 ** 3\n")
    assert sym["x"]["type"] == "int"


def test_exponentiation_float():
    sym, _ = analyze("x = 2.0 ** 3\n")
    assert sym["x"]["type"] == "float"


# ---------------------------------------------------------------------------
# Bool arithmetic rejection
# ---------------------------------------------------------------------------

def test_bool_plus_int_rejected():
    errs = errors_of("x = True + 1\n")
    assert errs


def test_bool_minus_rejected():
    errs = errors_of("x = True - 1\n")
    assert errs


def test_bool_times_rejected():
    errs = errors_of("x = False * 2\n")
    assert errs


def test_unary_minus_on_bool_rejected():
    errs = errors_of("x = -True\n")
    assert errs


# ---------------------------------------------------------------------------
# Division / modulo / floor-div by zero
# ---------------------------------------------------------------------------

def test_division_by_zero():
    errs = errors_of("x = 10 / 0\n")
    assert any("Division by zero" in e["message"] for e in errs)


def test_modulo_by_zero():
    errs = errors_of("x = 10 % 0\n")
    assert any("Modulo by zero" in e["message"] for e in errs)


def test_floor_division_by_zero():
    errs = errors_of("x = 10 // 0\n")
    assert any("Floor division by zero" in e["message"] for e in errs)


def test_division_by_nonzero_ok():
    sym, diags = analyze("x = 10 / 5\n")
    assert not errors_of("x = 10 / 5\n")


def test_division_by_variable_not_reported():
    """Can't statically detect division by a variable — must NOT report error."""
    errs = errors_of("y = 0\nx = 10 / y\n")
    # Division by variable: NOT a static error (the right operand is a name)
    assert not any("Division by zero" in e["message"] for e in errs)


# ---------------------------------------------------------------------------
# Compound assignments
# ---------------------------------------------------------------------------

def test_compound_assign_undefined():
    errs = errors_of("x += 5\n")
    assert any("used before it is defined" in e["message"] for e in errs)


def test_compound_assign_defined():
    sym, diags = analyze("x = 10\nx += 5\n")
    assert sym["x"]["type"] == "int"
    assert not [d for d in diags if d["severity"] == "ERROR"]


def test_compound_assign_floordiv():
    sym, diags = analyze("x = 10\nx //= 3\n")
    assert sym["x"]["type"] == "int"
    assert not [d for d in diags if d["severity"] == "ERROR"]


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------

def test_compare_int_int():
    sym, _ = analyze("x = 5 > 3\n")
    assert sym["x"]["type"] == "bool"


def test_compare_int_float():
    sym, _ = analyze("x = 5 >= 3.0\n")
    assert sym["x"]["type"] == "bool"


def test_compare_str_str():
    sym, _ = analyze('x = "a" == "b"\n')
    assert sym["x"]["type"] == "bool"


def test_compare_str_int_rejected():
    errs = errors_of('x = "hello" > 5\n')
    assert errs


# ---------------------------------------------------------------------------
# Logical operators
# ---------------------------------------------------------------------------

def test_logical_and_booleans():
    sym, _ = analyze("x = True and False\n")
    assert sym["x"]["type"] == "bool"


def test_logical_or_booleans():
    sym, _ = analyze("x = True or False\n")
    assert sym["x"]["type"] == "bool"


def test_logical_not_boolean():
    sym, _ = analyze("x = not True\n")
    assert sym["x"]["type"] == "bool"


def test_logical_complex():
    sym, diags = analyze("x = (5 > 3) and (2 < 4)\n")
    assert sym["x"]["type"] == "bool"
    assert not [d for d in diags if d["severity"] == "ERROR"]


# ---------------------------------------------------------------------------
# Type-change warning
# ---------------------------------------------------------------------------

def test_type_change_warning():
    warns = warnings_of('x = 10\nx = "hello"\n')
    assert any("changes type" in w["message"] for w in warns)


def test_no_type_change_warning_when_disabled():
    ast, _ = parse_source('x = 10\nx = "hello"\n')
    _, diags = analyze_ast(ast, warn_type_changes=False)
    warns = [d for d in diags if d["severity"] == "WARNING"]
    assert not warns


# ---------------------------------------------------------------------------
# Diagnostic structure
# ---------------------------------------------------------------------------

def test_diagnostic_has_category():
    _, diags = analyze("x = missing_var\n")
    assert all("category" in d for d in diags)


def test_diagnostic_has_severity():
    _, diags = analyze("x = missing_var\n")
    assert all("severity" in d for d in diags)


def test_diagnostic_has_line():
    _, diags = analyze("x = missing_var\n")
    assert all("line" in d for d in diags)
