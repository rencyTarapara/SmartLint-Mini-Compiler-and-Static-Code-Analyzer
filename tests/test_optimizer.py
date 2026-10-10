
from compiler.optimizer import optimize_tac


def test_constant_folding():
    tac = [
        "t1 = 20 * 3",
        "t2 = 10 + t1",
        "x = t2",
    ]

    result = optimize_tac(tac)

    assert result == [
        "t1 = 60",
        "t2 = 70",
        "x = 70",
    ]


def test_constant_propagation():
    tac = [
        "x = 10",
        "y = x",
        "print y",
    ]

    result = optimize_tac(tac)

    assert result == [
        "x = 10",
        "y = 10",
        "print 10",
    ]


def test_variable_reassignment():
    tac = [
        "x = 10",
        "x = 20",
        "y = x + 5",
    ]

    result = optimize_tac(tac)

    assert result == [
        "x = 10",
        "x = 20",
        "y = 25",
    ]


def test_division_by_zero_is_not_folded():
    tac = ["x = 10 / 0"]

    result = optimize_tac(tac)

    assert result == ["x = 10 / 0"]


def test_string_concatenation():
    tac = [
        "t1 = 'hello' + ' world'",
        "print t1",
    ]

    result = optimize_tac(tac)

    assert result == [
        "t1 = 'hello world'",
        "print 'hello world'",
    ]


def test_unary_negative_literal():
    tac = [
        "t1 = -5",
        "x = t1",
    ]

    result = optimize_tac(tac)

    assert result == [
        "t1 = -5",
        "x = -5",
    ]


def test_nonconstant_expression_is_preserved():
    tac = ["t1 = x + 5"]

    result = optimize_tac(tac)

    assert result == ["t1 = x + 5"]
