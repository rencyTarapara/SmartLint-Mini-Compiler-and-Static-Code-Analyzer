"""
Comprehensive lexer tests for SmartLint.
"""
import pytest
from compiler.lexer import build_lexer


def tokenize(source):
    """Return (token_list, lexical_errors) for source."""
    lex = build_lexer()
    lex.lineno = 1
    lex.input(source)
    tokens = [(t.type, t.value) for t in lex]
    return tokens, lex.lexical_errors


# ---------------------------------------------------------------------------
# Basic tokens
# ---------------------------------------------------------------------------

def test_basic_tokens():
    tokens, errors = tokenize("x = 10 + 20")
    assert not errors
    assert tokens == [
        ("NAME", "x"),
        ("EQUALS", "="),
        ("NUMBER", 10),
        ("PLUS", "+"),
        ("NUMBER", 20),
    ]


def test_reserved_words():
    tokens, errors = tokenize("print True False and or not")
    types = [t for t, _ in tokens]
    assert types == ["PRINT", "TRUE", "FALSE", "AND", "OR", "NOT"]


# ---------------------------------------------------------------------------
# Arithmetic operators
# ---------------------------------------------------------------------------

def test_arithmetic_operators():
    tokens, errors = tokenize("+ - * / // % **")
    types = [t for t, _ in tokens]
    assert not errors
    assert types == ["PLUS", "MINUS", "TIMES", "DIVIDE", "FLOORDIV", "MOD", "POW"]


def test_pow_not_split():
    """** must be a single POW token, not two TIMES tokens."""
    tokens, errors = tokenize("2 ** 3")
    types = [t for t, _ in tokens]
    assert "POW" in types
    assert types.count("TIMES") == 0


def test_floordiv_not_split():
    """// must be FLOORDIV, not two DIVIDE tokens."""
    tokens, errors = tokenize("10 // 3")
    types = [t for t, _ in tokens]
    assert "FLOORDIV" in types
    assert types.count("DIVIDE") == 0


# ---------------------------------------------------------------------------
# Compound assignment tokens
# ---------------------------------------------------------------------------

def test_compound_assignments():
    src = "+= -= *= /= //= %= **="
    tokens, errors = tokenize(src)
    types = [t for t, _ in tokens]
    assert not errors
    assert types == [
        "PLUS_EQ", "MINUS_EQ", "TIMES_EQ", "DIVIDE_EQ",
        "FLOORDIV_EQ", "MOD_EQ", "POW_EQ",
    ]


def test_compound_plus_eq():
    tokens, errors = tokenize("x += 5")
    assert not errors
    types = [t for t, _ in tokens]
    assert types == ["NAME", "PLUS_EQ", "NUMBER"]


def test_compound_pow_eq_not_split():
    """**= must be POW_EQ, not POW + EQUALS."""
    tokens, errors = tokenize("x **= 2")
    types = [t for t, _ in tokens]
    assert "POW_EQ" in types
    assert "POW" not in types


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------

def test_comparison_operators():
    src = "== != <= >= < >"
    tokens, errors = tokenize(src)
    types = [t for t, _ in tokens]
    assert not errors
    assert types == ["EQ", "NE", "LE", "GE", "LT", "GT"]


def test_eq_not_split():
    """== must not be split into two EQUALS tokens."""
    tokens, errors = tokenize("x == y")
    types = [t for t, _ in tokens]
    assert types == ["NAME", "EQ", "NAME"]
    assert "EQUALS" not in types


# ---------------------------------------------------------------------------
# Numeric literals
# ---------------------------------------------------------------------------

def test_integer_literal():
    tokens, _ = tokenize("42")
    assert tokens == [("NUMBER", 42)]


def test_float_literal():
    tokens, _ = tokenize("3.14")
    assert tokens == [("NUMBER", 3.14)]


def test_integer_value_type():
    tokens, _ = tokenize("100")
    assert isinstance(tokens[0][1], int)


def test_float_value_type():
    tokens, _ = tokenize("1.5")
    assert isinstance(tokens[0][1], float)


# ---------------------------------------------------------------------------
# String literals
# ---------------------------------------------------------------------------

def test_double_quoted_string():
    tokens, errors = tokenize('"hello"')
    assert not errors
    assert tokens == [("STRING", "hello")]


def test_single_quoted_string():
    tokens, errors = tokenize("'world'")
    assert not errors
    assert tokens == [("STRING", "world")]


def test_unterminated_string_double():
    tokens, errors = tokenize('"unterminated')
    assert len(errors) >= 1
    assert any("Unterminated" in e["message"] for e in errors)


def test_unterminated_string_single():
    tokens, errors = tokenize("'bad")
    assert len(errors) >= 1
    assert any("Unterminated" in e["message"] for e in errors)


# ---------------------------------------------------------------------------
# Invalid characters
# ---------------------------------------------------------------------------

def test_invalid_character():
    tokens, errors = tokenize("x = 10 @ 2")
    assert len(errors) == 1
    assert errors[0]["line"] == 1
    assert errors[0]["category"] == "LEXICAL"
    assert "@" in errors[0]["message"]


def test_invalid_character_column():
    tokens, errors = tokenize("x = 10 @ 2")
    assert errors[0]["column"] is not None
    assert errors[0]["column"] > 0


# ---------------------------------------------------------------------------
# Line tracking
# ---------------------------------------------------------------------------

def test_newline_increments_line():
    lex = build_lexer()
    lex.input("x = 1\ny = 2\n")
    toks = list(lex)
    names = [t for t in toks if t.type == "NAME"]
    assert names[0].lineno == 1
    assert names[1].lineno == 2


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def test_comment_discarded():
    tokens, errors = tokenize("# this is a comment\nx = 1")
    # Only x = 1 tokens should appear (no COMMENT token)
    types = [t for t, _ in tokens]
    assert "NAME" in types
    assert "NUMBER" in types
    # newline from end of comment line may appear
    assert len([t for t in types if t not in ("NAME", "EQUALS", "NUMBER", "NEWLINE")]) == 0


# ---------------------------------------------------------------------------
# Boolean literals
# ---------------------------------------------------------------------------

def test_true_false_tokens():
    tokens, _ = tokenize("True False")
    types = [t for t, _ in tokens]
    assert types == ["TRUE", "FALSE"]


# ---------------------------------------------------------------------------
# Delimiters
# ---------------------------------------------------------------------------

def test_parens():
    tokens, _ = tokenize("()")
    types = [t for t, _ in tokens]
    assert types == ["LPAREN", "RPAREN"]
