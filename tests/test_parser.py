
from compiler.parser import parse_source


def test_assignment():
    ast, errors = parse_source("x = 10 + 20\n")

    assert not errors
    assert ast[0]["type"] == "assign"
    assert ast[0]["name"] == "x"
    assert ast[0]["value"]["type"] == "binary"


def test_print():
    ast, errors = parse_source("print(42)\n")

    assert not errors
    assert ast[0]["type"] == "print"


def test_syntax_error():
    ast, errors = parse_source("x =\n")

    assert errors
    assert errors[0]["severity"] == "ERROR"
