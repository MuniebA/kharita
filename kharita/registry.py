"""Every utility kharita understands: its handler, documentation and test examples."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from kharita.expr import is_number, parse_columns, parse_expr
from kharita.palette import get_ramp, parse_color
from kharita.spec import LEGEND_POSITIONS, Scheme


@dataclass(frozen=True)
class Utility:
    name: str
    syntax: str
    description: str
    examples: tuple[str, ...]
    bad_examples: tuple[str, ...]
    handler: Callable | None


def _bracket(rest: str) -> str:
    # Inside of '[...]', with nothing after the closing bracket
    if not rest.startswith("["):
        raise ValueError("Expected '[' to start a data expression.")
    if not rest.endswith("]"):
        raise ValueError("Unexpected text after the closing bracket.")
    inner = rest[1:-1]
    if not inner.strip():
        raise ValueError("Brackets are empty.")
    return inner


def _positive(text: str, what: str) -> float:
    # A number greater than zero
    if not is_number(text) or not float(text) > 0 or float(text) == float("inf"):
        raise ValueError(f"{what} must be a number greater than 0, got '{text}'.")
    return float(text)


def _numbers(text: str) -> tuple[float, ...]:
    # '10,50,100' to a strictly increasing tuple
    parts = [p.strip() for p in text.split(",")]
    if not all(is_number(p) for p in parts):
        raise ValueError("Breaks must be numbers separated by commas, like scheme-[10,50,100].")
    values = tuple(float(p) for p in parts)
    if any(b <= a for a, b in zip(values, values[1:], strict=False)):
        raise ValueError("Breaks must increase from left to right.")
    return values


def _fill(b, rest: str) -> None:
    if rest.startswith("["):
        b.set("fill", fill_by=parse_expr(_bracket(rest)))
    else:
        b.set("fill", fill=parse_color(rest))


def _stroke(b, rest: str) -> None:
    if rest.startswith("["):
        b.set("stroke", stroke_by=parse_expr(_bracket(rest)))
    elif is_number(rest):
        b.set("stroke_width", stroke_width=_positive(rest, "Stroke width"))
    else:
        b.set("stroke", stroke=parse_color(rest))


def _size(b, rest: str) -> None:
    b.set("size", size=_positive(rest, "Size"))


def _opacity(b, rest: str) -> None:
    if not rest.isdigit() or int(rest) > 100:
        raise ValueError(f"Opacity must be a whole number from 0 to 100, got '{rest}'.")
    b.set("opacity", opacity=int(rest) / 100)


def _ramp(b, rest: str) -> None:
    reverse = rest.endswith("-r")
    name = rest[:-2] if reverse else rest
    get_ramp(name)
    b.set("ramp", ramp=name, ramp_reverse=reverse)


def _scheme(b, rest: str) -> None:
    m = re.fullmatch(r"([qe])(\d+)", rest)
    if m:
        k = int(m.group(2))
        if not 3 <= k <= 9:
            raise ValueError(
                f"Use 3 to 9 classes; readers cannot match more than about 7, got {k}."
            )
        b.set("scheme", scheme=Scheme("quantiles" if m.group(1) == "q" else "equal", k=k))
    elif rest == "cat":
        b.set("scheme", scheme=Scheme("categorical"))
    elif rest == "div":
        b.set("scheme", scheme=Scheme("diverging", center=0.0))
    elif rest.startswith("div-"):
        inner = _bracket(rest[4:]).strip()
        if not is_number(inner):
            raise ValueError(f"Diverging centre must be a number, got '{inner}'.")
        b.set("scheme", scheme=Scheme("diverging", center=float(inner)))
    elif rest.startswith("["):
        breaks = _numbers(_bracket(rest))
        b.set("scheme", scheme=Scheme("breaks", k=len(breaks) + 1, breaks=breaks))
    else:
        raise ValueError("Use scheme-q5, scheme-e5, scheme-cat, scheme-div, scheme-div-[50] "
                         "or scheme-[10,50,100].")


def _null(b, rest: str) -> None:
    b.set("null", null=parse_color(rest))


def _highlight(b, rest: str) -> None:
    b.set("highlight", highlight=parse_color(rest))


def _basemap(b, rest: str) -> None:
    if rest not in ("light", "dark", "none"):
        raise ValueError(f"Basemap must be light, dark or none, got '{rest}'.")
    b.set("basemap", basemap=rest)


def _legend(b, rest: str) -> None:
    if rest == "none":
        b.set("legend", legend=False)
    elif rest in LEGEND_POSITIONS:
        b.set("legend", legend_position=rest)
    else:
        raise ValueError(f"Use legend-none or a corner: {', '.join(LEGEND_POSITIONS)}.")


def _tooltip(b, rest: str) -> None:
    b.set("tooltip", tooltip=parse_columns(_bracket(rest)))


def _extrude(b, rest: str) -> None:
    if rest.startswith("max-"):
        b.set("extrude_max", extrude_max=_positive(rest[4:], "Maximum height"))
    else:
        b.set("extrude", extrude_by=parse_expr(_bracket(rest)))


UTILITIES: dict[str, Utility] = {
    u.name: u
    for u in (
        Utility("fill", "fill-<colour> | fill-[<expr>]",
                "Constant fill colour, or colour by data",
                ("fill-indigo-600", "fill-indigo-600/70", "fill-white", "fill-[pop]",
                 "fill-[pop/area]", "fill-[pop*1000]", "fill-[median income]", "fill-['pop/km2']"),
                ("fill-indgo-600", "fill-indigo-650", "fill-red-500/120", "fill-[]",
                 "fill-[a/b*2]", "fill-[pop]x"),
                _fill),
        Utility("stroke", "stroke-<colour> | stroke-<pixels> | stroke-[<expr>]",
                "Outline or line colour, its width in pixels, or line colour by data",
                ("stroke-white", "stroke-slate-300/50", "stroke-1", "stroke-1.5", "stroke-[speed]"),
                ("stroke-0", "stroke--1", "stroke-whte", "stroke-[]"),
                _stroke),
        Utility("size", "size-<pixels>", "Point radius in pixels",
                ("size-6", "size-2.5"), ("size-0", "size-big"), _size),
        Utility("opacity", "opacity-<0-100>", "Whole-layer opacity",
                ("opacity-80", "opacity-0", "opacity-100"), ("opacity-150", "opacity-0.5"),
                _opacity),
        Utility("ramp", "ramp-<name>[-r]", "Colour ramp for data; -r reverses it",
                ("ramp-viridis", "ramp-viridis-r", "ramp-ylorrd", "ramp-set2"),
                ("ramp-virdis", "ramp-rainbow"),
                _ramp),
        Utility("scheme", "scheme-q<k> | scheme-e<k> | scheme-[b1,b2] | scheme-cat | scheme-div",
                "How data values are grouped into colour classes",
                ("scheme-q5", "scheme-e4", "scheme-[10,50,100]", "scheme-cat", "scheme-div",
                 "scheme-div-[50]"),
                ("scheme-q12", "scheme-q2", "scheme-[50,10]", "scheme-[a,b]", "scheme-jenks",
                 "scheme-div-[x]"),
                _scheme),
        Utility("null", "null-<colour>", "Colour for missing values (default gray-300)",
                ("null-gray-300", "null-zinc-200/60"), ("null-grey-300",), _null),
        Utility("highlight", "highlight-<colour>", "Colour of the feature under the mouse",
                ("highlight-amber-400", "highlight-amber-400/80"), ("highlight-amber",),
                _highlight),
        Utility("basemap", "basemap-light | basemap-dark | basemap-none", "Basemap theme",
                ("basemap-light", "basemap-dark", "basemap-none"), ("basemap-satellite",),
                _basemap),
        Utility("legend", "legend-none | legend-tl | legend-tr | legend-bl | legend-br",
                "Hide the legend or choose its corner",
                ("legend-none", "legend-br", "legend-tl"), ("legend-top",), _legend),
        Utility("tooltip", "tooltip-[<col>,<col>]", "Columns shown when hovering",
                ("tooltip-[name]", "tooltip-[name,pop]", "tooltip-['a,b',pop]"),
                ("tooltip-[name,name]", "tooltip-name", "tooltip-[]"),
                _tooltip),
        Utility("extrude", "extrude-[<expr>] | extrude-max-<metres>",
                "3D height from data, and the height of the tallest feature",
                ("extrude-[pop]", "extrude-[floors*3]", "extrude-max-5000"),
                ("extrude-pop", "extrude-max-0", "extrude-max-tall"),
                _extrude),
        Utility("preset", "preset-<name>", "Expand a built-in or kh.define() style",
                ("preset-choropleth", "preset-outline", "preset-points"), ("preset-nothing",),
                None),
    )
}

BUILTIN_PRESETS: dict[str, str] = {
    "choropleth": "scheme-q5 stroke-1 stroke-white null-gray-300 highlight-amber-400",
    "outline": "fill-transparent stroke-2 stroke-slate-700",
    "points": "size-4 stroke-1 stroke-white highlight-amber-400",
}
USER_PRESETS: dict[str, str] = {}
