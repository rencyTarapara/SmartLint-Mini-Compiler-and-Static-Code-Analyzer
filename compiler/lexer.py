
import ply.lex as lex

# Reserved keywords
reserved = {
    "print": "PRINT",
    "True": "TRUE",
    "False": "FALSE",
}

# All token types
tokens = (
    "NAME", "NUMBER", "STRING",
    "PLUS", "MINUS", "TIMES", "DIVIDE",
    "EQUALS", "EQ", "NE", "LT", "LE", "GT", "GE",
    "LPAREN", "RPAREN", "NEWLINE",
) + tuple(reserved.values())

# Operators
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_DIVIDE = r"/"

# Longer operators should be recognized correctly
t_EQ = r"=="
t_NE = r"!="
t_LE = r"<="
t_LT = r"<"
t_GE = r">="
t_GT = r">"

t_EQUALS = r"="
t_LPAREN = r"\("
t_RPAREN = r"\)"

# Ignore spaces and tabs
t_ignore = " \t"


def t_NUMBER(t):
    r"\d+(\.\d+)?"
    t.value = float(t.value) if "." in t.value else int(t.value)
    return t


def t_STRING(t):
    r'"([^\\\n]|(\\.))*?"|\'([^\\\n]|(\\.))*?\''
    t.value = t.value[1:-1]
    return t


def t_NAME(t):
    r"[A-Za-z_][A-Za-z0-9_]*"
    t.type = reserved.get(t.value, "NAME")
    return t


def t_COMMENT(t):
    r"\#[^\n]*"
    pass


def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)
    return t


def t_error(t):
    t.lexer.lexical_errors.append({
        "severity": "ERROR",
        "line": t.lineno,
        "message": f"Invalid character {t.value[0]!r}",
    })
    t.lexer.skip(1)


def build_lexer():
    lexer = lex.lex()
    lexer.lexical_errors = []
    return lexer


lexer = build_lexer()
