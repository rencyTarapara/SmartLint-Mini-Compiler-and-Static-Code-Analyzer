
import ply.yacc as yacc

from compiler.lexer import tokens, build_lexer


# Store syntax errors for the current parse
syntax_errors = []


# Operator precedence: multiplication/division before addition/subtraction
precedence = (
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDE"),
    ("right", "UMINUS"),
)


# -------------------------
# Program and statement rules
# -------------------------

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


def p_statement_assignment(p):
    """statement : NAME EQUALS expression"""
    p[0] = {
        "type": "assign",
        "name": p[1],
        "value": p[3],
        "line": p.lineno(1),
    }


def p_statement_print(p):
    """statement : PRINT LPAREN expression RPAREN"""
    p[0] = {
        "type": "print",
        "value": p[3],
        "line": p.lineno(1),
    }


# -------------------------
# Expression rules
# -------------------------

def p_expression_binary(p):
    """expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression"""
    p[0] = {
        "type": "binary",
        "operator": p[2],
        "left": p[1],
        "right": p[3],
        "line": p.lineno(2),
    }


def p_expression_unary_minus(p):
    """expression : MINUS expression %prec UMINUS"""
    p[0] = {
        "type": "unary",
        "operator": "-",
        "value": p[2],
        "line": p.lineno(1),
    }


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


# -------------------------
# Syntax error handling
# -------------------------

def p_error(p):
    if p:
        syntax_errors.append({
            "severity": "ERROR",
            "line": p.lineno,
            "message": f"Syntax error near {p.value!r}",
        })
    else:
        syntax_errors.append({
            "severity": "ERROR",
            "line": 1,
            "message": "Unexpected end of input",
        })


# Build the parser once
parser = yacc.yacc()


def parse_source(source):
    syntax_errors.clear()

    # Handle an empty program and ensure the last statement
    # is terminated by a newline.
    if not source:
        return [], []

    if not source.endswith("\n"):
        source += "\n"

    lexer = build_lexer()
    lexer.lineno = 1

    ast = parser.parse(source, lexer=lexer)

    return ast, list(syntax_errors)
