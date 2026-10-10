"""
SmartLint Parser
================
Builds an AST from the token stream produced by the lexer.

Operator precedence (low → high)
---------------------------------
or          left
and         left
not         right (unary)
== != < <= > >=    left (non-chaining, handled by grammar)
+ -         left
* / // %    left
** (POW)    right
unary + -   right (Python-compatible: UMINUS lower than POW so -2**2 == -(2**2))
( )         grouping

AST node types
--------------
assign        : { type, name, value, line }
compound      : { type, name, operator, value, line }
print         : { type, value, line }
binary        : { type, operator, left, right, line }
compare       : { type, operator, left, right, line }
logical_and   : { type, left, right, line }
logical_or    : { type, left, right, line }
logical_not   : { type, value, line }
unary         : { type, operator, value, line }   operator ∈ {'-', '+'}
number        : { type, value, line }              value: int or float
string        : { type, value, line }
boolean       : { type, value, line }              value: bool
name          : { type, value, line }
"""

import ply.yacc as yacc

from compiler.lexer import tokens, build_lexer  # noqa: F401 (tokens consumed by PLY)


# ---------------------------------------------------------------------------
# Module-level syntax error list (cleared on each parse call)
# ---------------------------------------------------------------------------
syntax_errors: list[dict] = []


# ---------------------------------------------------------------------------
# Precedence table  (lowest → highest, left-to-right within same level)
# ---------------------------------------------------------------------------
precedence = (
    ("left",  "OR"),
    ("left",  "AND"),
    ("right", "NOT"),
    ("left",  "EQ", "NE", "LT", "LE", "GT", "GE"),
    ("left",  "PLUS", "MINUS"),
    ("left",  "TIMES", "DIVIDE", "FLOORDIV", "MOD"),
    ("right", "UMINUS", "UPLUS"),  # unary below POW → -2**2 == -(2**2)
    ("right", "POW"),
)


# ===========================================================================
# Grammar rules
# ===========================================================================

# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

def p_program(p):
    """program : lines"""
    p[0] = p[1]


def p_lines_empty(p):
    """lines : empty"""
    p[0] = []


def p_lines_blank(p):
    """lines : lines NEWLINE"""
    p[0] = p[1]


def p_lines_statement(p):
    """lines : lines statement NEWLINE"""
    p[0] = p[1] + [p[2]]


def p_empty(p):
    """empty :"""
    p[0] = None


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

def p_statement_assignment(p):
    """statement : NAME EQUALS expression"""
    p[0] = {
        "type": "assign",
        "name": p[1],
        "value": p[3],
        "line": p.lineno(1),
    }


def p_statement_compound_plus(p):
    """statement : NAME PLUS_EQ expression"""
    p[0] = {"type": "compound", "name": p[1], "operator": "+", "value": p[3], "line": p.lineno(1)}


def p_statement_compound_minus(p):
    """statement : NAME MINUS_EQ expression"""
    p[0] = {"type": "compound", "name": p[1], "operator": "-", "value": p[3], "line": p.lineno(1)}


def p_statement_compound_times(p):
    """statement : NAME TIMES_EQ expression"""
    p[0] = {"type": "compound", "name": p[1], "operator": "*", "value": p[3], "line": p.lineno(1)}


def p_statement_compound_divide(p):
    """statement : NAME DIVIDE_EQ expression"""
    p[0] = {"type": "compound", "name": p[1], "operator": "/", "value": p[3], "line": p.lineno(1)}


def p_statement_compound_floordiv(p):
    """statement : NAME FLOORDIV_EQ expression"""
    p[0] = {"type": "compound", "name": p[1], "operator": "//", "value": p[3], "line": p.lineno(1)}


def p_statement_compound_mod(p):
    """statement : NAME MOD_EQ expression"""
    p[0] = {"type": "compound", "name": p[1], "operator": "%", "value": p[3], "line": p.lineno(1)}


def p_statement_compound_pow(p):
    """statement : NAME POW_EQ expression"""
    p[0] = {"type": "compound", "name": p[1], "operator": "**", "value": p[3], "line": p.lineno(1)}


def p_statement_print(p):
    """statement : PRINT LPAREN expression RPAREN"""
    p[0] = {
        "type": "print",
        "value": p[3],
        "line": p.lineno(1),
    }


# ---------------------------------------------------------------------------
# Expressions — logical
# ---------------------------------------------------------------------------

def p_expression_or(p):
    """expression : expression OR expression"""
    p[0] = {
        "type": "logical_or",
        "left": p[1],
        "right": p[3],
        "line": p.lineno(2),
    }


def p_expression_and(p):
    """expression : expression AND expression"""
    p[0] = {
        "type": "logical_and",
        "left": p[1],
        "right": p[3],
        "line": p.lineno(2),
    }


def p_expression_not(p):
    """expression : NOT expression"""
    p[0] = {
        "type": "logical_not",
        "value": p[2],
        "line": p.lineno(1),
    }


# ---------------------------------------------------------------------------
# Expressions — comparison  (non-chaining)
# ---------------------------------------------------------------------------

def p_expression_compare(p):
    """expression : expression EQ expression
                  | expression NE expression
                  | expression LT expression
                  | expression LE expression
                  | expression GT expression
                  | expression GE expression"""
    p[0] = {
        "type": "compare",
        "operator": p[2],
        "left": p[1],
        "right": p[3],
        "line": p.lineno(2),
    }


# ---------------------------------------------------------------------------
# Expressions — arithmetic
# ---------------------------------------------------------------------------

def p_expression_binary_add(p):
    """expression : expression PLUS expression
                  | expression MINUS expression"""
    p[0] = {
        "type": "binary",
        "operator": p[2],
        "left": p[1],
        "right": p[3],
        "line": p.lineno(2),
    }


def p_expression_binary_mul(p):
    """expression : expression TIMES expression
                  | expression DIVIDE expression
                  | expression FLOORDIV expression
                  | expression MOD expression"""
    p[0] = {
        "type": "binary",
        "operator": p[2],
        "left": p[1],
        "right": p[3],
        "line": p.lineno(2),
    }


def p_expression_pow(p):
    """expression : expression POW expression"""
    p[0] = {
        "type": "binary",
        "operator": "**",
        "left": p[1],
        "right": p[3],
        "line": p.lineno(2),
    }


# ---------------------------------------------------------------------------
# Expressions — unary
# ---------------------------------------------------------------------------

def p_expression_unary_minus(p):
    """expression : MINUS expression %prec UMINUS"""
    p[0] = {
        "type": "unary",
        "operator": "-",
        "value": p[2],
        "line": p.lineno(1),
    }


def p_expression_unary_plus(p):
    """expression : PLUS expression %prec UPLUS"""
    p[0] = {
        "type": "unary",
        "operator": "+",
        "value": p[2],
        "line": p.lineno(1),
    }


# ---------------------------------------------------------------------------
# Expressions — primary
# ---------------------------------------------------------------------------

def p_expression_number(p):
    """expression : NUMBER"""
    p[0] = {
        "type": "number",
        "value": p[1],
        "line": p.lineno(1),
    }


def p_expression_string(p):
    """expression : STRING"""
    p[0] = {
        "type": "string",
        "value": p[1],
        "line": p.lineno(1),
    }


def p_expression_name(p):
    """expression : NAME"""
    p[0] = {
        "type": "name",
        "value": p[1],
        "line": p.lineno(1),
    }


def p_expression_boolean(p):
    """expression : TRUE
                  | FALSE"""
    p[0] = {
        "type": "boolean",
        "value": p[1] == "True",
        "line": p.lineno(1),
    }


def p_expression_group(p):
    """expression : LPAREN expression RPAREN"""
    p[0] = p[2]


# ---------------------------------------------------------------------------
# Error rule
# ---------------------------------------------------------------------------

def p_error(p):
    if p:
        syntax_errors.append({
            "severity": "ERROR",
            "category": "SYNTAX",
            "message": f"Syntax error near {p.value!r}",
            "line": p.lineno,
            "column": getattr(p, "column", None),
        })
    else:
        syntax_errors.append({
            "severity": "ERROR",
            "category": "SYNTAX",
            "message": "Unexpected end of input",
            "line": None,
            "column": None,
        })


# ---------------------------------------------------------------------------
# Build parser  (write_tables=False avoids stale parsetab.py issues)
# ---------------------------------------------------------------------------
parser = yacc.yacc(write_tables=False, debug=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_source(source: str) -> tuple[list, list]:
    """
    Parse *source* and return ``(ast, syntax_errors)``.

    The AST is a list of statement dicts (possibly empty).
    syntax_errors is a list of structured diagnostic dicts.
    Errors from earlier syntax_errors are not duplicated.
    """
    syntax_errors.clear()

    if not source:
        return [], []

    if not source.endswith("\n"):
        source += "\n"

    lexer = build_lexer()
    lexer.lineno = 1

    ast = parser.parse(source, lexer=lexer)

    # Collect lexical errors from the lexer as well
    lex_errors = list(lexer.lexical_errors)

    if ast is None:
        ast = []

    return ast, lex_errors + list(syntax_errors)
