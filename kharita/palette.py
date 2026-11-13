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


HEX_DIGITS = set("0123456789abcdefABCDEF")
# Shades used for a family's own sequential ramp, light to dark
FAMILY_RAMP_SHADES = ("100", "200", "300", "400", "500", "600", "700", "800", "900")
DIVERGING_SIDE = ("800", "600", "400", "200")
NEUTRAL_MIDDLE = "#f5f5f4"
RAMP_STOPS = 11
USER_RAMPS: dict[str, dict] = {}


def hex_to_rgba(hex_color: str, alpha: int = 255) -> RGBA:
    # '#abc', '#aabbcc' or '#aabbccdd' to (r, g, b, a)
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        alpha = int(h[6:8], 16)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def rgba_to_hex(c) -> str:
    """'#rrggbb' for an RGBA tuple; alpha is dropped."""
    return "#{:02x}{:02x}{:02x}".format(*c[:3])


def _parse_hex(text: str) -> RGBA:
    # '#0f766e', '#0f7', '#0f766e80' to RGBA, with a clear error otherwise
    h = text[1:]
    if len(h) not in (3, 6, 8) or not set(h) <= HEX_DIGITS:
        raise ValueError(f"'{text}' is not a hex colour; use 3, 6 or 8 hex digits like #0f766e.")
    return hex_to_rgba(text)


def parse_opacity(text: str) -> int:
    # '0' to '100' as a percentage, returned as alpha 0 to 255
    if not text.isdigit() or int(text) > 100:
        raise ValueError(f"Opacity must be a whole number from 0 to 100, got '{text}'.")
    return (int(text) * 255 + 50) // 100


def parse_color(text: str) -> RGBA:
    # 'indigo-600', 'white', 'transparent', '#0f766e' or '[#0f766e]', with an optional '/<0-100>'
    name, slash, opacity = text.partition("/")
    alpha = parse_opacity(opacity) if slash else None
    if name.startswith("[#") and name.endswith("]"):
        name = name[1:-1]
    if name.startswith("#"):
        r, g, b, a = _parse_hex(name)
        return (r, g, b, a if alpha is None else alpha)
    alpha = 255 if alpha is None else alpha
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


def _srgb_to_oklab(c) -> tuple[float, float, float]:
    # sRGB 0-255 to OKLab, for even blending between colours
    def lin(v):
        v = v / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in c[:3])
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def _oklab_to_hex(lab) -> str:
    # OKLab back to '#rrggbb', clipped into sRGB
    L, a, b = lab
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)

    def enc(v):
        v = min(1.0, max(0.0, v))
        v = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        return round(v * 255)

    return "#{:02x}{:02x}{:02x}".format(*(enc(v) for v in rgb))


def blend(hexes: list[str], n: int = RAMP_STOPS) -> list[str]:
    """n colours spread evenly through the given ones, blended in OKLab."""
    labs = [_srgb_to_oklab(hex_to_rgba(h)) for h in hexes]
    if len(labs) == 1:
        return [hexes[0]] * n
    out = []
    for i in range(n):
        t = i / (n - 1) * (len(labs) - 1)
        j = min(int(t), len(labs) - 2)
        f = t - j
        out.append(_oklab_to_hex(tuple(a + (b - a) * f for a, b in zip(labs[j], labs[j + 1],
                                                                          strict=True))))
    return out


def _family_ramp(family: str) -> dict:
    # A Tailwind family as a light-to-dark ramp
    shades = load_colors()[family]
    return {"kind": "sequential", "source": "tailwind",
            "colors": [shades[s] for s in FAMILY_RAMP_SHADES]}


def _two_family_ramp(left: str, right: str) -> dict:
    # Dark left family through a neutral to dark right family
    c = load_colors()
    colors = [c[left][s] for s in DIVERGING_SIDE] + [NEUTRAL_MIDDLE]
    colors += [c[right][s] for s in DIVERGING_SIDE[::-1]]
    return {"kind": "diverging", "source": "tailwind", "colors": colors}


def _inline_ramp(name: str) -> dict:
    # '[sky-100,indigo-500,#4c1d95]': exact colours for categories, blended stops for numbers
    parts = [p.strip() for p in name[1:-1].split(",") if p.strip()]
    if len(parts) < 2:
        raise ValueError("A ramp of your own needs at least two colours, like "
                         "ramp-[sky-100,indigo-700].")
    given = [rgba_to_hex(parse_color(p)) for p in parts]
    return {"kind": "sequential", "source": "inline", "colors": blend(given), "given": given}


def ramp_names() -> list[str]:
    """Every ramp name kharita knows: built in, your own, and the Tailwind families."""
    return sorted({*load_ramps(), *USER_RAMPS, *FAMILIES})


def get_ramp(name: str) -> dict:
    # Ramp record: your own, built in, a Tailwind family, two families, or an inline list
    if name in USER_RAMPS:
        return USER_RAMPS[name]
    ramps = load_ramps()
    if name in ramps:
        return ramps[name]
    if name in FAMILIES:
        return _family_ramp(name)
    left, dash, right = name.partition("-")
    if dash and left in FAMILIES and right in FAMILIES:
        return _two_family_ramp(left, right)
    if name.startswith("[") and name.endswith("]"):
        return _inline_ramp(name)
    raise ValueError(f"Unknown ramp '{name}'.{_suggest(name, ramp_names())}")
