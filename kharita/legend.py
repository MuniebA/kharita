"""Builds self-contained HTML legends from a Scale."""

from dataclasses import replace
from html import escape

import numpy as np

from kharita.classify import Scale, _decimals, fmt_number

LIGHT = {"bg": "#ffffffee", "ink": "#111827", "quiet": "#6b7280", "line": "#00000022"}
DARK = {"bg": "#111827e6", "ink": "#f9fafb", "quiet": "#9ca3af", "line": "#ffffff33"}
SWATCH_BORDER = {"light": "#0000001f", "dark": "#ffffff40"}
LEGEND_OPTIONS = {"title", "fmt", "labels", "note", "style"}
LEGEND_STYLES = ("list", "bar")
FONT = "system-ui,-apple-system,Segoe UI,Roboto,sans-serif"
THREE_D_NOTE = "3D shading darkens colours slightly."


def _rgba_css(c) -> str:
    return f"rgba({c[0]},{c[1]},{c[2]},{c[3] / 255:.3f})"


def relabel(scale: Scale, fmt: str) -> Scale:
    """Rewrite numeric class labels with a format string such as '{:,.0f}'."""
    if scale.kind == "continuous":
        lo, hi = scale.edges
        return replace(scale, labels=tuple(fmt.format(x) for x in (lo, (lo + hi) / 2, hi)))
    if scale.kind != "classed" or scale.edges is None:
        raise ValueError("fmt only applies to numeric classes; use labels= for categories.")
    e = scale.edges
    f = fmt.format
    if scale.k == 1:
        labels = [f(e[0])]
    elif scale.scheme.startswith("breaks"):
        inner = e[1:-1]
        labels = [f"under {f(inner[0])}"]
        labels += [f"{f(inner[i])} to {f(inner[i + 1])}" for i in range(len(inner) - 1)]
        labels += [f"{f(inner[-1])} and over"]
    else:
        labels = [f"{f(e[i])} to {f(e[i + 1])}" for i in range(scale.k)]
    return replace(scale, labels=tuple(labels))


# Bar legend sizing: inner width of the card and an average tick character, in pixels
BAR_WIDTH = 236
TICK_GAP = 4


def _text_width(text: str) -> float:
    # Approximate pixel width at 10.5px: digits, narrow punctuation, wide capitals
    return sum(3.0 if ch in ".,: " else 8.5 if ch.isupper() else 6.0 for ch in text)
COMPACT_FROM = 10_000


def compact(x: float) -> str:
    """Short number for tight legends: 553,515 as 554K, 5,274,321 as 5.27M."""
    a = abs(x)
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            text = f"{x / div:.3g}"
            return (f"{x / div:.0f}" if "e" in text else text) + suffix
    return fmt_number(x, 0 if float(x).is_integer() else 1)


def _ticks(scale: Scale, fmt) -> list[str]:
    # Class edge values for the bar legend: your format, else short numbers when large
    edges = np.asarray(scale.edges, dtype=float)
    if fmt is not None:
        return [fmt.format(x) for x in edges]
    if np.max(np.abs(edges)) >= COMPACT_FROM:
        return [compact(x) for x in edges]
    d = _decimals(edges, bool(np.all(np.mod(edges, 1) == 0)))
    return [fmt_number(x, d) for x in edges]


def _tick_row(texts: list[str], quiet: str) -> str:
    # Labels spread evenly under a bar, first flush left and last flush right
    spans = "".join(f"<span>{escape(t)}</span>" for t in texts)
    return (f'<div style="display:flex;justify-content:space-between;gap:6px;margin-top:3px;'
            f'color:{quiet};font-size:10.5px;font-variant-numeric:tabular-nums">{spans}</div>')


def _crowded(texts: list[str], step: int = 1) -> bool:
    # True when labels `step` edges apart would overlap; end labels hang fully inside the bar
    n = len(texts) - 1
    slot = BAR_WIDTH / max(n, 1) * step

    def reach(i: int, side: str) -> float:
        # Pixels a label extends towards its neighbour
        whole = _text_width(texts[i])
        if (i == 0 and side == "right") or (i == n and side == "left"):
            return whole
        return whole / 2

    return any(reach(i, "right") + reach(i + step, "left") + TICK_GAP > slot
               for i in range(0, n - step + 1))


def _edge_ticks(texts: list[str], quiet: str) -> str:
    # Each label sits exactly under its class edge; crowded labels alternate between two rows
    n = len(texts) - 1
    stagger = _crowded(texts)
    spans = []
    for i, text in enumerate(texts):
        shift = "0" if i == 0 else "-100%" if i == n else "-50%"
        top = "13px" if stagger and i % 2 else "0"
        spans.append(f'<span style="position:absolute;left:{i / n * 100:.2f}%;top:{top};'
                     f'transform:translateX({shift});white-space:nowrap">{escape(text)}</span>')
    height = 27 if stagger else 14
    return (f'<div style="position:relative;width:{BAR_WIDTH}px;height:{height}px;'
            f'margin-top:3px;color:{quiet};'
            f'font-size:10.5px;font-variant-numeric:tabular-nums">{"".join(spans)}</div>')


def legend_block(scale: Scale, title=None, fmt=None, labels=None, note=None, style="list",
                 dark: bool = False, notes: tuple[str, ...] = ()) -> str:
    """One layer's legend: a list of classes with counts, a bar, or a gradient for scheme-linear."""
    t = DARK if dark else LIGHT
    border = SWATCH_BORDER["dark" if dark else "light"]
    if style not in LEGEND_STYLES:
        raise ValueError(f"Legend style must be one of {', '.join(LEGEND_STYLES)}, got '{style}'.")
    if style == "bar" and scale.kind == "categorical":
        raise ValueError("style='bar' needs numeric classes; categories use the list legend.")
    if fmt is not None:
        scale = relabel(scale, fmt)
    expected = 3 if scale.kind == "continuous" else scale.k
    if labels is not None:
        labels = [str(x) for x in labels]
        if scale.kind == "continuous" and len(labels) == 2:
            labels = [labels[0], "", labels[1]]
        if len(labels) != expected:
            what = "ticks (low, middle, high)" if scale.kind == "continuous" else "classes"
            raise ValueError(f"labels has {len(labels)} entries but the legend has {expected} "
                             f"{what}.")
        scale = replace(scale, labels=tuple(labels))

    def row(color_css: str, text: str, count) -> str:
        right = (f'<span style="color:{t["quiet"]};font-variant-numeric:tabular-nums">'
                 f"{count:,}</span>") if count is not None else ""
        return (
            '<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            '<span style="flex:none;width:14px;height:14px;border-radius:3px;'
            f'background:{color_css};border:1px solid {border}"></span>'
            f'<span style="flex:1">{escape(text)}</span>{right}</div>'
        )

    bar_css = f"height:12px;border-radius:3px;border:1px solid {border}"
    if scale.kind == "continuous":
        gradient = ",".join(scale.colors)
        body = (f'<div style="{bar_css};background:linear-gradient(to right,{gradient})"></div>'
                + _tick_row(list(scale.labels), t["quiet"]))
    elif style == "bar":
        cells = "".join(f'<span style="flex:1;background:{c}"></span>' for c in scale.colors)
        bar = (f'<div style="display:flex;overflow:hidden;width:{BAR_WIDTH}px;{bar_css}">'
               f"{cells}</div>")
        if labels is not None:
            body = bar + _tick_row(list(scale.labels), t["quiet"])
        else:
            texts = _ticks(scale, fmt)
            if _crowded(texts, step=2):
                # Too long even on two rows: fall back to short numbers like 2.64M
                texts = [compact(x) for x in scale.edges]
            body = bar + _edge_ticks(texts, t["quiet"])
    else:
        body = "".join(row(c, lab, n) for c, lab, n in zip(scale.colors, scale.labels,
                                                             scale.counts, strict=True))
    if scale.null_count:
        count = scale.null_count if style == "list" and scale.kind != "continuous" else None
        gap = "" if style == "list" and scale.kind != "continuous" else "margin-top:6px"
        body += f'<div style="{gap}">{row(_rgba_css(scale.null_color), "No data", count)}</div>'
    heading = escape(str(title if title is not None else scale.label))
    foot_lines = [str(note)] if note else []
    foot_lines += list(notes)
    foot = "".join(f'<div style="margin-top:6px;font-size:10.5px;color:{t["quiet"]};'
                   f'max-width:230px">{escape(x)}</div>' for x in foot_lines)
    return (
        '<div class="kharita-legend-block" style="margin-bottom:8px">'
        f'<div style="font-weight:600;margin-bottom:5px">{heading}</div>{body}{foot}</div>'
    )


def _metres(m: float) -> str:
    # 850 m, 1.2 km, 120 km
    if m < 1000:
        return f"{m:,.0f} m"
    km = m / 1000
    text = f"{km:,.1f}" if km < 10 else f"{km:,.0f}"
    return f"{text.removesuffix('.0')} km"


def height_block(label: str, top: float, tallest: float, fmt=None, dark: bool = False) -> str:
    """Height key for an extruded layer: what height shows and how tall the tallest is."""
    t = DARK if dark else LIGHT
    value = fmt.format(top) if fmt else fmt_number(top, 0 if float(top).is_integer() or top >= 100
                                                  else 2 if top < 10 else 1)
    bars = "".join(f'<span style="width:5px;height:{h}px;background:{t["quiet"]};'
                   'border-radius:1px"></span>' for h in (5, 10, 16))
    icon = f'<span style="display:flex;align-items:flex-end;gap:2px;flex:none">{bars}</span>'
    return (
        '<div class="kharita-legend-block" style="margin-bottom:8px">'
        f'<div style="display:flex;align-items:center;gap:8px">{icon}'
        f'<span>Height shows <b>{escape(label)}</b></span></div>'
        f'<div style="color:{t["quiet"]};font-size:10.5px;margin-top:4px">Tallest: '
        f"{escape(value)} drawn {_metres(tallest)} high. {THREE_D_NOTE}</div></div>"
    )


def frame_card(title=None, subtitle=None, source=None, dark: bool = False) -> str:
    """The title card: title, subtitle and a source line."""
    if not (title or subtitle or source):
        return ""
    t = DARK if dark else LIGHT
    parts = []
    if title:
        parts.append(f'<div style="font-size:17px;font-weight:650;line-height:1.25;'
                     f'letter-spacing:-0.01em">{escape(str(title))}</div>')
    if subtitle:
        parts.append(f'<div style="margin-top:3px;color:{t["quiet"]};font-size:12.5px">'
                     f"{escape(str(subtitle))}</div>")
    if source:
        rule = f"border-top:1px solid {t['line']};padding-top:5px;margin-top:7px" if (
            title or subtitle) else ""
        parts.append(f'<div style="{rule};color:{t["quiet"]};font-size:10.5px">'
                     f"Source: {escape(str(source))}</div>")
    return (
        f'<div class="kharita-frame" style="font:12px/1.35 {FONT};color:{t["ink"]};'
        f'background:{t["bg"]};padding:10px 14px;border-radius:8px;'
        f'box-shadow:0 1px 4px {t["line"]};max-width:340px">{"".join(parts)}</div>'
    )


def legend_panel(blocks: list[str], dark: bool = False) -> str:
    """Wrap one or more legend blocks in the floating card."""
    t = DARK if dark else LIGHT
    return (
        f'<div class="kharita-legend" style="font:12px/1.35 {FONT};'
        f'color:{t["ink"]};background:{t["bg"]};padding:10px 12px 4px;'
        f'border-radius:8px;box-shadow:0 1px 4px {t["line"]};min-width:170px;max-width:260px">'
        f'{"".join(blocks)}</div>'
    )
