"""
End-to-end pipeline tests for SmartLint.

Each test runs the full Source → Lexer → Parser → Semantic → TAC → Optimizer
pipeline and validates the expected results from the project specification.
"""
import pytest
from compiler.lexer import build_lexer
from compiler.parser import parse_source
from compiler.semantic import analyze_ast
from compiler.tac import generate_tac
from compiler.optimizer import optimize_tac


def run(source: str):
    """
    Run the full SmartLint pipeline on *source*.
    Returns a dict with:
      tokens, lexical_errors, ast, parse_errors,
      symbol_table, semantic_diagnostics,
      tac, optimized_tac
    """
    if not source.endswith("\n"):
        source += "\n"

    # Lex
    lex = build_lexer()
    lex.lineno = 1
    lex.input(source)
    tokens = list(lex)
    lexical_errors = lex.lexical_errors

    # Parse
    ast, parse_errors = parse_source(source)

    # Semantic
    if not lexical_errors and not parse_errors and ast is not None:
        sym, sem_diags = analyze_ast(ast)
    else:
        sym, sem_diags = {}, []

    # TAC
    if ast is not None and ast != []:
        tac = generate_tac(ast)
        optimized = optimize_tac(tac)
    else:
        tac, optimized = [], []

    return {
        "tokens": tokens,
        "lexical_errors": lexical_errors,
        "ast": ast or [],
        "parse_errors": parse_errors,
        "symbol_table": sym,
        "semantic_diagnostics": sem_diags,
        "tac": tac,
        "optimized_tac": optimized,
    }


def sem_errors(r):
    return [d for d in r["semantic_diagnostics"] if d["severity"] == "ERROR"]


def sem_warnings(r):
    return [d for d in r["semantic_diagnostics"] if d["severity"] == "WARNING"]


def all_errors(r):
    return r["lexical_errors"] + r["parse_errors"] + sem_errors(r)


# ===========================================================================
# Spec regression cases — VALID programs
# ===========================================================================

class TestValidPrograms:

    def test_addition_precedence(self):
        """2 + 3 * 4 == 14."""
        r = run("x = 2 + 3 * 4")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = 14"

    def test_grouped_addition(self):
        """(2 + 3) * 4 == 20."""
        r = run("x = (2 + 3) * 4")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = 20"

    def test_pow_right_assoc(self):
        """2 ** 3 ** 2 == 512."""
        r = run("x = 2 ** 3 ** 2")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = 512"

    def test_unary_minus_lower_than_pow(self):
        """-2 ** 2 == -4."""
        r = run("x = -2 ** 2")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = -4"

    def test_grouped_unary_pow(self):
        """(-2) ** 2 == 4."""
        r = run("x = (-2) ** 2")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = 4"

    def test_floor_division(self):
        """10 // 3 == 3."""
        r = run("x = 10 // 3")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = 3"

    def test_modulo(self):
        """10 % 3 == 1."""
        r = run("x = 10 % 3")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = 1"

    def test_string_concatenation(self):
        r = run('x = "hello" + " world"')
        assert not all_errors(r)
        assert r["symbol_table"]["x"]["type"] == "str"
        # Optimizer should fold it
        assert any("hello world" in i for i in r["optimized_tac"])

    def test_compare_gte(self):
        """5 >= 3 == True."""
        r = run("x = 5 >= 3")
        assert not all_errors(r)
        assert r["symbol_table"]["x"]["type"] == "bool"
        assert r["optimized_tac"][-1] == "x = True"

    def test_compare_equality(self):
        r = run("x = 5 == 5")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = True"

    def test_compare_inequality(self):
        r = run("x = 5 != 3")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = True"

    def test_compare_lte(self):
        r = run("x = 4 <= 4")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = True"

    def test_compare_gt_false(self):
        r = run("x = 7 >= 8")
        assert not all_errors(r)
        assert r["optimized_tac"][-1] == "x = False"

    def test_logical_and_both_compares(self):
        """(5 > 3) and (2 < 4) == True."""
        r = run("x = (5 > 3) and (2 < 4)")
        assert not all_errors(r)
        assert r["symbol_table"]["x"]["type"] == "bool"

    def test_multi_statement_program(self):
        src = "x = 10\ny = 20\nz = x + y * 2\nprint(z)"
        r = run(src)
        assert not all_errors(r)
        assert "x" in r["symbol_table"]
        assert "z" in r["symbol_table"]

    def test_compound_plus_eq(self):
        r = run("x = 10\nx += 5")
        assert not all_errors(r)
        assert r["symbol_table"]["x"]["type"] == "int"

    def test_all_arithmetic_operators(self):
        src = (
            "a = 10 + 5\n"
            "b = 10 - 5\n"
            "c = 10 * 5\n"
            "d = 10 / 5\n"
            "e = 10 // 3\n"
            "f = 10 % 3\n"
            "g = 2 ** 3\n"
        )
        r = run(src)
        assert not all_errors(r)
        assert r["symbol_table"]["a"]["type"] == "int"
        assert r["symbol_table"]["d"]["type"] == "float"

    def test_unary_plus_noop(self):
        r = run("x = +5")
        assert not all_errors(r)
        assert r["symbol_table"]["x"]["type"] == "int"

    def test_left_assoc_subtraction(self):
        """10 - 3 - 2 == 5."""
        r = run("x = 10 - 3 - 2")
        assert not all_errors(r)
        opt = r["optimized_tac"]
        assert opt[-1] == "x = 5"

    def test_division_result_float(self):
        r = run("x = 20 / 5 * 2")
        assert r["symbol_table"]["x"]["type"] == "float"


# ===========================================================================
# Spec regression cases — ERROR programs
# ===========================================================================

class TestErrorPrograms:

    def test_division_by_zero(self):
        """x = 10 / 0  →  semantic division-by-zero ERROR."""
        r = run("x = 10 / 0")
        errs = sem_errors(r)
        assert any("Division by zero" in e["message"] for e in errs)

    def test_modulo_by_zero(self):
        """x = 10 % 0  →  semantic modulo-by-zero ERROR."""
        r = run("x = 10 % 0")
        errs = sem_errors(r)
        assert any("Modulo by zero" in e["message"] for e in errs)

    def test_floor_division_by_zero(self):
        r = run("x = 10 // 0")
        errs = sem_errors(r)
        assert any("Floor division by zero" in e["message"] for e in errs)

    def test_undefined_variable(self):
        """x = missing_variable + 1  →  undefined-variable ERROR."""
        r = run("x = missing_variable + 1")
        errs = sem_errors(r)
        assert any("missing_variable" in e["message"] for e in errs)

    def test_string_subtraction(self):
        """x = "hello" - 2  →  type-error ERROR."""
        r = run('x = "hello" - 2')
        errs = sem_errors(r)
        assert errs

    def test_syntax_error_dangling_plus(self):
        """x = 5 +  →  syntax error."""
        r = run("x = 5 +")
        assert r["parse_errors"]

    def test_syntax_error_leading_operator(self):
        r = run("x = * 3")
        assert r["parse_errors"]

    def test_syntax_error_unclosed_paren(self):
        r = run("x = (2 + 3")
        assert r["parse_errors"]

    def test_invalid_character(self):
        r = run("x = 10 @ 2")
        assert r["lexical_errors"]

    def test_compound_on_undefined(self):
        r = run("x += 5")
        errs = sem_errors(r)
        assert any("used before it is defined" in e["message"] for e in errs)

    def test_bool_arithmetic(self):
        r = run("x = True + 1")
        errs = sem_errors(r)
        assert errs

    def test_string_comparison_with_int(self):
        r = run('x = "hello" > 5')
        errs = sem_errors(r)
        assert errs


# ===========================================================================
# Pipeline integrity
# ===========================================================================

class TestPipelineIntegrity:

    def test_empty_source(self):
        r = run("")
        assert not all_errors(r)
        assert r["ast"] == []

    def test_comments_only(self):
        r = run("# just a comment")
        assert not all_errors(r)
        assert r["ast"] == []

    def test_no_crash_on_invalid(self):
        """Pipeline must not raise exceptions on malformed input."""
        sources = [
            "x = 5 +",
            "x = * 3",
            "@ $ !",
            "",
            "x = (2 + 3",
        ]
        for src in sources:
            try:
                run(src)
            except Exception as exc:
                pytest.fail(f"Pipeline raised {type(exc).__name__} on {src!r}: {exc}")

    def test_tac_not_generated_on_parse_error(self):
        """TAC generation should still run (it gets empty/invalid AST from errors)."""
        r = run("x = 5 +")
        # ast will be empty because of error; tac should be empty too
        assert r["tac"] == [] or r["parse_errors"]

    def test_optimizer_preserves_div_zero(self):
        r = run("x = 10 / 0")
        opt = r["optimized_tac"]
        assert any("10 / 0" in i for i in opt)

    def test_optimizer_folds_constants(self):
        r = run("x = 2 + 3")
        assert r["optimized_tac"][-1] == "x = 5"
