"""Tokenizer: whitespace splitting that keeps brackets and quotes whole."""

import pytest

from kharita.errors import StyleSyntaxError
from kharita.tokenizer import tokenize


def texts(style):
    return [t.text for t in tokenize(style)]


@pytest.mark.parametrize(
    "style, expected",
    [
        ("", []),
        ("   ", []),
        ("fill-red-500", ["fill-red-500"]),
        ("fill-red-500  stroke-1\tsize-4\n", ["fill-red-500", "stroke-1", "size-4"]),
        ("fill-[median income]", ["fill-[median income]"]),
        ("fill-[pop / area] stroke-1", ["fill-[pop / area]", "stroke-1"]),
        ("fill-['odd ] name'] size-2", ["fill-['odd ] name']", "size-2"]),
        ('tooltip-["a b",c]', ['tooltip-["a b",c]']),
    ],
)
def test_splits(style, expected):
    assert texts(style) == expected


def test_positions_point_at_token_start():
    toks = tokenize("  fill-red-500   stroke-1")
    assert [t.start for t in toks] == [2, 17]


@pytest.mark.parametrize(
    "style, position, phrase",
    [
        ("fill-[pop", 5, "never closed"),
        ("fill-pop]", 8, "without an opening"),
        ("fill-[[pop]]", 6, "nested"),
        ("fill-['pop]", 6, "Quote is never closed"),
    ],
)
def test_errors_carry_position(style, position, phrase):
    with pytest.raises(StyleSyntaxError) as info:
        tokenize(style)
    assert info.value.position == position
    assert phrase.lower() in str(info.value).lower()


def test_non_string_rejected():
    with pytest.raises(StyleSyntaxError):
        tokenize(None)
