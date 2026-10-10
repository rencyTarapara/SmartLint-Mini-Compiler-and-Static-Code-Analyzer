
from compiler.parser import parse_source
from compiler.tac import generate_tac


def get_tac(source):
    ast, errors = parse_source(source)
    assert not errors, f"Unexpected syntax errors: {errors}"
    return generate_tac(ast)


def test_simple_assignment():
    tac = get_tac("x = 10\n")
    assert tac == ["x = 10"]


def test_operator_precedence():
    tac = get_tac("x = 10 + 20 * 3\n")

    assert tac == [
        "t1 = 20 * 3",
        "t2 = 10 + t1",
        "x = t2",
    ]


def test_print_variable():
    tac = get_tac("x = 5\nprint(x)\n")

    assert tac == [
        "x = 5",
        "print x",
    ]


def test_blank_lines():
    tac = get_tac("\nx = 10\n\nprint(x)\n")
    assert tac == ["x = 10", "print x"]


def test_unary_minus():
    tac = get_tac("x = -5\n")

    assert tac == [
        "t1 = -5",
        "x = t1",
    ]
