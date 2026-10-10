
from compiler.parser import parse_source
from compiler.semantic import analyze_ast


def analyze(source):
    ast, syntax_errors = parse_source(source)
    assert not syntax_errors
    return analyze_ast(ast)


def test_symbol_table():
    symbols, diagnostics = analyze("x = 10\ny = 2.5\n")

    assert symbols["x"]["type"] == "int"
    assert symbols["y"]["type"] == "float"
    assert not diagnostics


def test_undefined_variable():
    symbols, diagnostics = analyze("print(x)\n")

    assert any(
        "used before it is defined" in item["message"]
        for item in diagnostics
    )


def test_invalid_arithmetic():
    symbols, diagnostics = analyze('x = "hello" - 2\n')

    assert any(
        item["severity"] == "ERROR"
        and "cannot be applied" in item["message"]
        for item in diagnostics
    )


def test_type_change_warning():
    symbols, diagnostics = analyze('x = 10\nx = "hello"\n')

    assert any(
        item["severity"] == "WARNING"
        and "changes type" in item["message"]
        for item in diagnostics
    )


def test_string_concatenation():
    symbols, diagnostics = analyze('x = "hello" + " world"\n')

    assert symbols["x"]["type"] == "str"
    assert not diagnostics


def test_undefined_variable_in_expression():
    symbols, diagnostics = analyze("x = y + 1\n")

    assert any(
        item["severity"] == "ERROR"
        and "'y'" in item["message"]
        for item in diagnostics
    )
