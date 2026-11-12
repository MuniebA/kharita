"""Classification schemes, colour lookup tables and the Scale a legend is drawn from."""

import math
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from kharita.errors import KharitaWarning
from kharita.palette import RGBA, get_ramp, hex_to_rgba
from kharita.spec import Scheme

OTHER_HEX = "#9ca3af"
DIVERGING_CLASSES = 7
MAX_SEQUENTIAL_CATEGORIES = 12
# Extruded layers drop near-white stops (bright and low in colour), up to this share of the ramp
PALE_LUMINANCE = 0.85
PALE_MIN_CHANNEL = 0.6
MAX_TRIM_SHARE = 0.3


@dataclass(frozen=True)
class Scale:
    kind: str
    label: str
    scheme: str
    colors: tuple[str, ...]
    labels: tuple[str, ...]
    counts: tuple[int, ...]
    edges: tuple[float, ...] | None = None
    categories: tuple | None = None
    null_count: int = 0
    null_color: RGBA = (209, 213, 219, 255)
    notes: tuple[str, ...] = ()

    @property
    def k(self) -> int:
        # Number of colour classes
        return len(self.colors)


def _note(notes: list[str], message: str) -> None:
    # Record a note for the legend and raise it as a warning
    notes.append(message)
    warnings.warn(message, KharitaWarning, stacklevel=4)


def luminance(hex_colour: str) -> float:
    """Relative luminance from 0 (black) to 1 (white)."""
    r, g, b, _ = hex_to_rgba(hex_colour)
    return 0.2126 * r / 255 + 0.7152 * g / 255 + 0.0722 * b / 255


def is_pale(hex_colour: str) -> bool:
    """True for near-white colours that 3D lighting turns grey; strong yellows are not pale."""
    r, g, b, _ = hex_to_rgba(hex_colour)
    return luminance(hex_colour) > PALE_LUMINANCE and min(r, g, b) / 255 > PALE_MIN_CHANNEL


def ramp_stops(name: str, reverse: bool = False, trim_pale: bool = False) -> list[str]:
    """A ramp's stops in drawing order; trim_pale drops near-white stops from the light end."""
    ramp = get_ramp(name)
    stops = list(ramp["colors"][::-1] if reverse else ramp["colors"])
    if trim_pale and ramp["kind"] == "sequential":
        light_first = luminance(stops[0]) > luminance(stops[-1])
        ordered = stops if light_first else stops[::-1]
        cap = int(len(ordered) * MAX_TRIM_SHARE)
        n = 0
        while n < cap and is_pale(ordered[n]):
            n += 1
        ordered = ordered[n:]
        stops = ordered if light_first else ordered[::-1]
    return stops


def ramp_colors(name: str, k: int, reverse: bool = False, trim_pale: bool = False) -> list[str]:
    # k colours from a ramp: sampled evenly for continuous ramps, taken in order for categorical
    ramp = get_ramp(name)
    stops = ramp_stops(name, reverse, trim_pale)
    if ramp["kind"] == "categorical":
        if k > len(stops):
            raise ValueError(f"ramp-{name} has only {len(stops)} colours, {k} needed.")
        return list(stops[:k])
    if k == 1:
        return [stops[len(stops) // 2]]
    idx = np.linspace(0, len(stops) - 1, k).round().astype(int)
    return [stops[i] for i in idx]


def _decimals(edges: np.ndarray, integral: bool) -> int:
    # Fewest decimals that keep neighbouring edges distinguishable
    if integral and np.all(np.mod(edges, 1) == 0):
        return 0
    diffs = np.diff(edges)
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return 0
    smallest = float(diffs.min())
    return int(min(4, max(0, math.ceil(-math.log10(smallest)) + 1))) if smallest < 10 else 0


def fmt_number(x: float, decimals: int) -> str:
    # Thousands separators, fixed decimals, no negative zero
    text = f"{x:,.{decimals}f}"
    if text.startswith("-") and float(text[1:].replace(",", "")) == 0:
        return text[1:]
    return text


def _lut(hexes: list[str]) -> np.ndarray:
    return np.array([hex_to_rgba(h) for h in hexes], dtype=np.uint8)


def _continuous(values, ok, lo, hi, ramp, reverse, trim_pale, label, null, notes, integral):
    # Unclassed colour: each value placed on the ramp by where it sits between min and max
    stops = ramp_stops(ramp, reverse, trim_pale)
    lut = _lut(stops).astype(float)
    pos = np.linspace(0.0, 1.0, len(stops))
    t = np.clip((np.where(ok, values, lo) - lo) / (hi - lo), 0.0, 1.0)
    out = np.empty((values.size, 4), dtype=np.uint8)
    for ch in range(4):
        out[:, ch] = np.round(np.interp(t, pos, lut[:, ch])).astype(np.uint8)
    out[~ok] = null
    ticks = np.array([lo, (lo + hi) / 2, hi])
    d = _decimals(ticks, integral)
    scale = Scale(
        kind="continuous", label=label, scheme="continuous", colors=tuple(stops),
        labels=tuple(fmt_number(x, d) for x in ticks), counts=(int(ok.sum()),),
        edges=(lo, hi), null_count=int((~ok).sum()), null_color=null, notes=tuple(notes),
    )
    return out, scale


def classify_numeric(
    values: np.ndarray, scheme: Scheme, ramp: str, reverse: bool, label: str, null: RGBA,
    trim_pale: bool = False,
) -> tuple[np.ndarray, Scale]:
    """Colour numeric values by class, or along the ramp for scheme-linear; NaN gets null."""
    ok = np.isfinite(values)
    finite = values[ok]
    notes: list[str] = []
    integral = bool(np.all(np.mod(finite, 1) == 0))
    distinct = np.unique(finite)

    if distinct.size == 1:
        _note(notes, f"Every value of {label} is {distinct[0]:g}; showing one class.")
        edges = np.array([distinct[0], distinct[0]])
        classes = np.zeros(values.shape, dtype=np.int64)
        labels = [fmt_number(distinct[0], 0 if integral else 2)]
        colors = ramp_colors(ramp, 1, reverse, trim_pale)
        return _finish(values, ok, classes, colors, labels, edges, None, scheme, label, null, notes)

    lo, hi = float(finite.min()), float(finite.max())
    if scheme.kind == "linear":
        return _continuous(values, ok, lo, hi, ramp, reverse, trim_pale, label, null, notes,
                           integral)
    if scheme.kind == "quantiles":
        edges = np.unique(np.quantile(finite, np.linspace(0, 1, scheme.k + 1)))
        if edges.size - 1 < scheme.k:
            _note(notes, f"Tied values in {label} allow only {edges.size - 1} quantile classes, "
                         f"not {scheme.k}.")
        classes = np.searchsorted(edges[1:-1], values, side="right")
    elif scheme.kind == "equal":
        edges = np.linspace(lo, hi, scheme.k + 1)
        if distinct.size < scheme.k:
            _note(notes, f"{label} has {distinct.size} distinct values for {scheme.k} classes; "
                         "some classes are empty.")
        classes = np.clip(np.searchsorted(edges[1:-1], values, side="right"), 0, scheme.k - 1)
    elif scheme.kind == "breaks":
        breaks = np.asarray(scheme.breaks, dtype=float)
        classes = np.searchsorted(breaks, values, side="right")
        edges = np.concatenate([[min(lo, breaks[0])], breaks, [max(hi, breaks[-1])]])
    elif scheme.kind == "diverging":
        c = scheme.center
        reach = float(np.max(np.abs(finite - c)))
        edges = c + np.linspace(-reach, reach, DIVERGING_CLASSES + 1)
        classes = np.clip(np.searchsorted(edges[1:-1], values, side="right"),
                          0, DIVERGING_CLASSES - 1)
        if lo >= c or hi <= c:
            _note(notes, f"All values of {label} are on one side of {c:g}; "
                         "a diverging scheme may mislead.")
    else:
        raise ValueError(f"Scheme '{scheme.kind}' is not numeric.")

    k = edges.size - 1
    d = _decimals(edges, integral)
    if scheme.kind == "breaks":
        b = scheme.breaks
        # The user's own breaks decide the decimals, as many as they typed
        d = min(4, max(len(f"{x:g}".partition(".")[2]) for x in b))
        labels = [f"under {fmt_number(b[0], d)}"]
        labels += [f"{fmt_number(b[i], d)} to {fmt_number(b[i + 1], d)}" for i in range(len(b) - 1)]
        labels += [f"{fmt_number(b[-1], d)} and over"]
    else:
        labels = [f"{fmt_number(edges[i], d)} to {fmt_number(edges[i + 1], d)}" for i in range(k)]
    colors = ramp_colors(ramp, k, reverse, trim_pale)
    return _finish(values, ok, classes, colors, labels, edges, None, scheme, label, null, notes)


def classify_categorical(
    values, ramp: str, reverse: bool, label: str, null: RGBA
) -> tuple[np.ndarray, Scale]:
    """Colour values by category, most frequent first; extras become 'other'."""
    s = pd.Series(values, copy=False)
    missing = s.isna().to_numpy()
    counts = s[~missing].value_counts()
    order = sorted(counts.index, key=lambda c: (-counts[c], str(c)))
    notes: list[str] = []

    ramp_kind = get_ramp(ramp)["kind"]
    if ramp_kind == "categorical":
        room = len(get_ramp(ramp)["colors"])
    else:
        room = MAX_SEQUENTIAL_CATEGORIES
    if len(order) > room:
        kept = order[: room - 1]
        _note(notes, f"{label} has {len(order)} categories; the {len(order) - len(kept)} "
                     "least common are grouped as 'other'.")
    else:
        kept = order
    colors = ramp_colors(ramp, len(kept), reverse)
    codes = pd.Categorical(s, categories=kept).codes.astype(np.int64)
    labels = [_category_label(c) for c in kept]
    cat_counts = [int(counts[c]) for c in kept]
    other = len(order) > len(kept)
    if other:
        codes[(codes == -1) & ~missing] = len(kept)
        colors = colors + [OTHER_HEX]
        labels.append("other")
        cat_counts.append(int(counts[order[len(kept):]].sum()))

    lut = _lut(colors)
    out = lut[np.clip(codes, 0, len(colors) - 1)]
    out[missing] = null
    scale = Scale(
        kind="categorical", label=label, scheme="categorical", colors=tuple(colors),
        labels=tuple(labels), counts=tuple(cat_counts), categories=tuple(kept),
        null_count=int(missing.sum()), null_color=null, notes=tuple(notes),
    )
    return out, scale


def _category_label(value) -> str:
    # 3.0 shows as 3; everything else as text
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _finish(values, ok, classes, colors, labels, edges, cats, scheme, label, null, notes):
    # Lookup colours, paint nulls, count classes, build the Scale
    lut = _lut(colors)
    classes = np.clip(classes, 0, len(colors) - 1)
    out = lut[classes]
    out[~ok] = null
    counts = np.bincount(classes[ok], minlength=len(colors))
    scale = Scale(
        kind="classed", label=label, scheme=str(scheme), colors=tuple(colors),
        labels=tuple(labels), counts=tuple(int(c) for c in counts),
        edges=tuple(float(e) for e in edges), categories=cats,
        null_count=int((~ok).sum()), null_color=null, notes=tuple(notes),
    )
    return out, scale
