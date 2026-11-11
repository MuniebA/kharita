"""Colour tokens to RGBA."""

import pytest

from kharita.palette import FAMILIES, SHADES, get_ramp, hex_to_rgba, parse_color, parse_opacity


@pytest.mark.parametrize(
    "text, expected",
    [
        ("indigo-600", (79, 70, 229, 255)),
        ("indigo-600/70", (79, 70, 229, 179)),
        ("emerald-500/80", (16, 185, 129, 204)),
        ("slate-800/90", (30, 41, 59, 230)),
        ("white", (255, 255, 255, 255)),
        ("black/50", (0, 0, 0, 128)),
        ("transparent", (0, 0, 0, 0)),
        ("red-500/0", (239, 68, 68, 0)),
    ],
)
def test_known_colours(text, expected):
    assert parse_color(text) == expected


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("shade", SHADES)
def test_every_family_and_shade_parses(family, shade):
    r, g, b, a = parse_color(f"{family}-{shade}")
    assert a == 255 and all(0 <= v <= 255 for v in (r, g, b))


@pytest.mark.parametrize(
    "text, phrase",
    [
        ("indgo-600", "Did you mean 'indigo'"),
        ("indigo-650", "Shade must be one of"),
        ("indigo", "not a colour"),
        ("whte", "Did you mean 'white'"),
        ("red-500/101", "0 to 100"),
        ("red-500/x", "0 to 100"),
    ],
)
def test_bad_colours_explain_themselves(text, phrase):
    with pytest.raises(ValueError, match=phrase):
        parse_color(text)


def test_opacity_rounding():
    assert [parse_opacity(str(p)) for p in (0, 50, 70, 100)] == [0, 128, 179, 255]


def test_hex_short_and_long():
    assert hex_to_rgba("#fff") == hex_to_rgba("#ffffff") == (255, 255, 255, 255)


def test_ramp_lookup_suggests():
    assert get_ramp("viridis")["kind"] == "sequential"
    with pytest.raises(ValueError, match="viridis"):
        get_ramp("virdis")
