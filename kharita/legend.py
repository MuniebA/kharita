"""Builds self-contained HTML legends from a Scale."""

from dataclasses import replace
from html import escape

from kharita.classify import Scale

LIGHT = {"bg": "#ffffffee", "ink": "#111827", "quiet": "#6b7280", "line": "#00000022"}
DARK = {"bg": "#111827e6", "ink": "#f9fafb", "quiet": "#9ca3af", "line": "#ffffff33"}
SWATCH_BORDER = {"light": "#0000001f", "dark": "#ffffff40"}
LEGEND_OPTIONS = {"title", "fmt", "labels", "note"}


def _rgba_css(c) -> str:
    return f"rgba({c[0]},{c[1]},{c[2]},{c[3] / 255:.3f})"


def relabel(scale: Scale, fmt: str) -> Scale:
    """Rewrite numeric class labels with a format string such as '{:,.0f}'."""
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


def legend_block(scale: Scale, title=None, fmt=None, labels=None, note=None,
                 dark: bool = False) -> str:
    """One layer's legend: title, a row per class with its count, and a no-data row."""
    t = DARK if dark else LIGHT
    border = SWATCH_BORDER["dark" if dark else "light"]
    if fmt is not None:
        scale = relabel(scale, fmt)
    if labels is not None:
        labels = list(labels)
        if len(labels) != scale.k:
            raise ValueError(f"labels has {len(labels)} entries but the legend has {scale.k} "
                             "classes.")
        scale = replace(scale, labels=tuple(str(x) for x in labels))

    def row(color_css: str, text: str, count: int) -> str:
        return (
            '<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            '<span style="flex:none;width:14px;height:14px;border-radius:3px;'
            f'background:{color_css};border:1px solid {border}"></span>'
            f'<span style="flex:1">{escape(text)}</span>'
            f'<span style="color:{t["quiet"]};font-variant-numeric:tabular-nums">{count:,}</span>'
            "</div>"
        )

    rows = [row(c, lab, n) for c, lab, n in zip(scale.colors, scale.labels, scale.counts,
                                                  strict=True)]
    if scale.null_count:
        rows.append(row(_rgba_css(scale.null_color), "No data", scale.null_count))
    heading = escape(str(title if title is not None else scale.label))
    foot = (f'<div style="margin-top:6px;font-size:10.5px;color:{t["quiet"]};max-width:230px">'
            f"{escape(str(note))}</div>") if note else ""
    return (
        '<div class="kharita-legend-block" style="margin-bottom:8px">'
        f'<div style="font-weight:600;margin-bottom:5px">{heading}</div>'
        f'{"".join(rows)}{foot}</div>'
    )


def legend_panel(blocks: list[str], dark: bool = False) -> str:
    """Wrap one or more legend blocks in the floating card."""
    t = DARK if dark else LIGHT
    return (
        f'<div class="kharita-legend" style="font:12px/1.35 system-ui,-apple-system,Segoe UI,'
        f'Roboto,sans-serif;color:{t["ink"]};background:{t["bg"]};padding:10px 12px 4px;'
        f'border-radius:8px;box-shadow:0 1px 4px {t["line"]};min-width:170px;max-width:260px">'
        f'{"".join(blocks)}</div>'
    )
