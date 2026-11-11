"""Bracket expressions: column, ratio, scaled column, column lists."""

import pytest

from kharita.expr import Expr, parse_columns, parse_expr


@pytest.mark.parametrize(
    "text, expected",
    [
        ("pop", Expr("pop")),
        (" pop ", Expr("pop")),
        ("median income", Expr("median income")),
        ("pop/area", Expr("pop", divisor="area")),
        ("pop / area", Expr("pop", divisor="area")),
        ("pop*1000", Expr("pop", factor=1000.0)),
        ("pop * 0.5", Expr("pop", factor=0.5)),
        ("'pop/km2'", Expr("pop/km2")),
        ('"a*b"', Expr("a*b")),
        ("'pop/km2'/area", Expr("pop/km2", divisor="area")),
    ],
)
def test_valid(text, expected):
    assert parse_expr(text) == expected


@pytest.mark.parametrize(
    "text, phrase",
    [
        ("", "missing"),
        ("a/b/c", "Only"),
        ("a/b*2", "Only"),
        ("pop*x", "not a number"),
        ("1000*pop", "column first"),
        ("pop*0", "other than 0"),
        ("pop*inf", "finite"),
        ("''", "empty"),
        ("po'p", "Quotes must wrap"),
        ("/area", "missing"),
    ],
)
def test_invalid(text, phrase):
    with pytest.raises(ValueError, match=phrase):
        parse_expr(text)


def test_columns_and_str():
    assert parse_expr("pop/area").columns == ("pop", "area")
    assert str(parse_expr("pop*1000")) == "pop * 1000"


def test_column_lists():
    assert parse_columns("name, pop") == ("name", "pop")
    assert parse_columns("'a,b',c") == ("a,b", "c")
    with pytest.raises(ValueError, match="twice"):
        parse_columns("a,a")
