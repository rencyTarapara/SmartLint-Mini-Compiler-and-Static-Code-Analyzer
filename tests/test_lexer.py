
from compiler.lexer import build_lexer


def test_basic_tokens():
    lexer = build_lexer()
    lexer.input("x = 10 + 20")

    result = [(token.type, token.value) for token in lexer]

    assert result == [
        ("NAME", "x"),
        ("EQUALS", "="),
        ("NUMBER", 10),
        ("PLUS", "+"),
        ("NUMBER", 20),
    ]


def test_reserved_words():
    lexer = build_lexer()
    lexer.input("print True False")

    result = [token.type for token in lexer]

    assert result == ["PRINT", "TRUE", "FALSE"]


def test_invalid_character():
    lexer = build_lexer()
    lexer.input("x = 10 @ 2")

    list(lexer)

    assert len(lexer.lexical_errors) == 1
    assert lexer.lexical_errors[0]["line"] == 1
