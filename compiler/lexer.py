"""
SmartLint Lexer
===============
Tokenises the supported Python-like language.

Supported tokens
----------------
Literals   : INTEGER, FLOAT, STRING, TRUE, FALSE
Identifiers: NAME (and reserved keywords)
Arithmetic : + - * / // % **
Compound   : += -= *= /= //= %= **=
Comparison : == != < <= > >=
Logical    : and or not
Assignment : =
Delimiters : ( )
Other      : NEWLINE, COMMENT (discarded)
"""

import ply.lex as lex

# ---------------------------------------------------------------------------
# Reserved keywords
# ---------------------------------------------------------------------------
reserved = {
    "print": "PRINT",
    "True": "TRUE",
    "False": "FALSE",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
}

# ---------------------------------------------------------------------------
# Token list
# ---------------------------------------------------------------------------
tokens = (
    "NAME",
    "NUMBER",
    "STRING",
    # Arithmetic
    "PLUS",
    "MINUS",
    "TIMES",
    "DIVIDE",
    "FLOORDIV",   # //
    "MOD",        # %
    "POW",        # **
    # Compound assignments
    "PLUS_EQ",    # +=
    "MINUS_EQ",   # -=
    "TIMES_EQ",   # *=
    "DIVIDE_EQ",  # /=
    "FLOORDIV_EQ",# //=
    "MOD_EQ",     # %=
    "POW_EQ",     # **=
    # Simple assignment
    "EQUALS",
    # Comparison
    "EQ",   # ==
    "NE",   # !=
    "LE",   # <=
    "LT",   # <
    "GE",   # >=
    "GT",   # >
    # Delimiters
    "LPAREN",
    "RPAREN",
    # Structure
    "NEWLINE",
) + tuple(reserved.values())


# ---------------------------------------------------------------------------
# Helper: build a structured diagnostic
# ---------------------------------------------------------------------------
def _make_error(severity, category, message, line, column):
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "line": line,
        "column": column,
    }


def _column(t):
    """Return the column number of a token (1-indexed)."""
    last_nl = t.lexer.lexdata.rfind("\n", 0, t.lexpos)
    return t.lexpos - last_nl  # already 1-indexed because rfind returns -1 if absent


# ---------------------------------------------------------------------------
# Multi-character operators  (MUST be functions or long strings so PLY orders
# them by string length, matching longer patterns first)
# ---------------------------------------------------------------------------

# Compound assignments — must come before simple operators
def t_POW_EQ(t):
    r"\*\*="
    return t


def t_FLOORDIV_EQ(t):
    r"//="
    return t


def t_PLUS_EQ(t):
    r"\+="
    return t


def t_MINUS_EQ(t):
    r"-="
    return t


def t_TIMES_EQ(t):
    r"\*="
    return t


def t_DIVIDE_EQ(t):
    r"/="
    return t


def t_MOD_EQ(t):
    r"%="
    return t


# Two-character arithmetic
def t_POW(t):
    r"\*\*"
    return t


def t_FLOORDIV(t):
    r"//"
    return t


# Two-character comparisons
def t_EQ(t):
    r"=="
    return t


def t_NE(t):
    r"!="
    return t


def t_LE(t):
    r"<="
    return t


def t_GE(t):
    r">="
    return t


# Single-character operators (after all multi-char alternatives above)
t_PLUS   = r"\+"
t_MINUS  = r"-"
t_TIMES  = r"\*"
t_DIVIDE = r"/"
t_MOD    = r"%"
t_LT     = r"<"
t_GT     = r">"
t_EQUALS = r"="
t_LPAREN = r"\("
t_RPAREN = r"\)"

# Ignore spaces and tabs
t_ignore = " \t"


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------

def t_NUMBER(t):
    r"\d+(\.\d+)?"
    if "." in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    t.column = _column(t)
    return t


def t_STRING(t):
    r'"([^\\"\n]|\\.)*"|\'([^\\\'\n]|\\.)*\''
    t.column = _column(t)
    # Strip surrounding quotes and preserve the raw content
    t.value = t.value[1:-1]
    return t


def t_UNTERMINATED_STRING(t):
    r'"([^\\"\n]|\\.)*$|\'([^\\\'\n]|\\.)*$'
    col = _column(t)
    t.lexer.lexical_errors.append(
        _make_error(
            "ERROR",
            "LEXICAL",
            "Unterminated string literal",
            t.lineno,
            col,
        )
    )
    t.lexer.skip(len(t.value))


# ---------------------------------------------------------------------------
# Identifiers and keywords
# ---------------------------------------------------------------------------

def t_NAME(t):
    r"[A-Za-z_][A-Za-z0-9_]*"
    t.type = reserved.get(t.value, "NAME")
    t.column = _column(t)
    return t


# ---------------------------------------------------------------------------
# Comment and newline
# ---------------------------------------------------------------------------

def t_COMMENT(t):
    r"\#[^\n]*"
    pass  # silently discard


def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    t.column = 0
    return t


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

def t_error(t):
    col = _column(t)
    t.lexer.lexical_errors.append(
        _make_error(
            "ERROR",
            "LEXICAL",
            f"Invalid character {t.value[0]!r}",
            t.lineno,
            col,
        )
    )
    t.lexer.skip(1)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_lexer():
    """Create and return a fresh lexer instance."""
    lexer = lex.lex()
    lexer.lexical_errors = []
    return lexer


# Module-level instance (used by PLY's parser internally)
lexer = build_lexer()
