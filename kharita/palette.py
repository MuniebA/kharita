"""Bundled colour palette and ramps, and conversion of colour tokens to RGBA."""

import json
from difflib import get_close_matches
from functools import cache
from importlib.resources import files

FAMILIES = (
    "slate", "gray", "zinc", "neutral", "stone", "red", "orange", "amber", "yellow", "lime",
    "green", "emerald", "teal", "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia",
    "pink", "rose",
)
SHADES = ("50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950")
NAMED = ("white", "black", "transparent")

RGBA = tuple[int, int, int, int]


@cache
def load_colors() -> dict:
    # UI palette: family -> shade -> hex, plus white and black
    return json.loads(files("kharita.data").joinpath("colors.json").read_text(encoding="utf-8"))


@cache
def load_ramps() -> dict:
    # Data ramps: name -> {kind, source, colors}
    return json.loads(files("kharita.data").joinpath("ramps.json").read_text(encoding="utf-8"))


def _suggest(word: str, options) -> str:
    # " Did you mean 'x'?" or an empty string
    match = get_close_matches(word, list(options), n=1, cutoff=0.6)
    return f" Did you mean '{match[0]}'?" if match else ""


def hex_to_rgba(hex_color: str, alpha: int = 255) -> RGBA:
    # '#abc' or '#aabbcc' to (r, g, b, a)
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def parse_opacity(text: str) -> int:
    # '0' to '100' as a percentage, returned as alpha 0 to 255
    if not text.isdigit() or int(text) > 100:
        raise ValueError(f"Opacity must be a whole number from 0 to 100, got '{text}'.")
    return (int(text) * 255 + 50) // 100


def parse_color(text: str) -> RGBA:
    # 'indigo-600', 'white' or 'transparent', each with an optional '/<0-100>' opacity
    name, slash, opacity = text.partition("/")
    alpha = parse_opacity(opacity) if slash else 255
    if name == "transparent":
        return (0, 0, 0, 0)
    colors = load_colors()
    if name in ("white", "black"):
        return hex_to_rgba(colors[name], alpha)
    family, dash, shade = name.rpartition("-")
    if not dash:
        hint = _suggest(name, FAMILIES + NAMED)
        raise ValueError(
            f"'{name}' is not a colour; use a family and shade like 'indigo-600'.{hint}"
        )
    if family not in FAMILIES:
        raise ValueError(f"Unknown colour family '{family}'.{_suggest(family, FAMILIES)}")
    if shade not in SHADES:
        raise ValueError(f"Shade must be one of {', '.join(SHADES)}, got '{shade}'.")
    return hex_to_rgba(colors[family][shade], alpha)


def get_ramp(name: str) -> dict:
    # Ramp record by name, with a suggestion when unknown
    ramps = load_ramps()
    if name not in ramps:
        raise ValueError(f"Unknown ramp '{name}'.{_suggest(name, ramps)}")
    return ramps[name]
