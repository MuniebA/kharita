"""Browse colours and ramps, check them, and add your own palettes and themes."""

from dataclasses import replace
from html import escape

import numpy as np

from kharita import basemaps as kb
from kharita.palette import (
    FAMILIES,
    SHADES,
    USER_RAMPS,
    blend,
    get_ramp,
    hex_to_rgba,
    load_colors,
    load_ramps,
    parse_color,
    rgba_to_hex,
)
from kharita.spec import THEME_RAMPS

SOURCES = {
    "colorbrewer": ("ColorBrewer", "Apache 2.0"),
    "matplotlib": ("matplotlib", "CC0"),
    "matplotlib-turbo": ("Turbo, via matplotlib", "Apache 2.0"),
    "crameri": ("Crameri scientific colour maps", "MIT"),
    "cmocean": ("cmocean", "MIT"),
    "cartocolors": ("CARTOColors", "CC BY 4.0"),
    "kharita": ("kharita", "MIT"),
    "kharita-lbcs": ("kharita, LBCS land-use convention", "MIT"),
    "fews-net": ("IPC phases, FEWS NET colours", "standard colours"),
    "esa-worldcover": ("ESA WorldCover legend", "CC BY 4.0"),
    "tailwind": ("Tailwind CSS shades", "MIT"),
    "inline": ("your colours", ""),
    "user": ("kh.palette", ""),
}
# Machado, Oliveira and Fernandes (2009), full severity, applied in linear RGB
PROTAN = np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216],
                   [-0.003882, -0.048116, 1.051998]])
DEUTAN = np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413],
                   [-0.011820, 0.042940, 0.968881]])
# Neighbouring classes this far apart in CIE76 stay distinguishable
SAFE_DELTA = 10.0
# Lightness steps whose spread (std / mean) is under this read as even
EVEN_TOLERANCE = 0.3
FONT = "system-ui,-apple-system,Segoe UI,Roboto,sans-serif"


def _linear(hex_colour: str) -> np.ndarray:
    # sRGB hex to linear RGB 0-1
    v = np.array(hex_to_rgba(hex_colour)[:3], dtype=float) / 255
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def _from_linear(rgb: np.ndarray) -> str:
    # Linear RGB 0-1 back to sRGB hex
    v = np.clip(rgb, 0, 1)
    v = np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)
    return rgba_to_hex(tuple(int(round(x * 255)) for x in v))


def lab(hex_colour: str) -> tuple[float, float, float]:
    """CIELAB (D65) of an sRGB hex colour."""
    r, g, b = _linear(hex_colour)
    xyz = np.array([0.4124 * r + 0.3576 * g + 0.1805 * b, 0.2126 * r + 0.7152 * g + 0.0722 * b,
                    0.0193 * r + 0.1192 * g + 0.9505 * b]) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return (116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2]))


def delta_e(a: str, b: str) -> float:
    """CIE76 colour difference between two hex colours."""
    return float(np.linalg.norm(np.subtract(lab(a), lab(b))))


def simulate(hex_colour: str, kind: str) -> str:
    """How a colour looks with protanopia ('protan') or deuteranopia ('deutan')."""
    m = PROTAN if kind == "protan" else DEUTAN
    return _from_linear(m @ _linear(hex_colour))


def check_ramp(name: str, classes: int = 5) -> dict:
    """Lightness steps and colour-blind safety of a ramp, at the given number of classes."""
    from kharita.classify import ramp_colors

    rec = get_ramp(name)
    if rec["kind"] == "categorical":
        colours = list(rec.get("given", rec["colors"]))
        pairs = [(a, b) for i, a in enumerate(colours) for b in colours[i + 1:]]
    else:
        colours = ramp_colors(name, classes)
        pairs = list(zip(colours, colours[1:], strict=False))
    worst = min(min(delta_e(simulate(a, k), simulate(b, k)) for a, b in pairs)
                for k in ("protan", "deutan")) if pairs else 0.0
    out = {"name": name, "kind": rec["kind"], "source": rec["source"],
           "colour_blind_safe": worst >= SAFE_DELTA, "worst_difference": round(worst, 1)}
    if rec["kind"] == "sequential":
        # Judge the ramp's own stops, not a coarse sample that adds rounding jitter
        steps = np.diff([lab(c)[0] for c in rec["colors"]])
        monotonic = bool(np.all(steps > 0) or np.all(steps < 0))
        spread = float(np.std(steps) / abs(steps.mean())) if monotonic else 9.0
        out["lightness"] = "even" if monotonic and spread <= EVEN_TOLERANCE else (
            "uneven" if monotonic else "not monotonic")
    return out


def palette(name: str, colors: list, kind: str = "sequential") -> str:
    """Register your own ramp, then use it as ramp-<name>."""
    if not name.replace("_", "").isalnum() or not name.islower():
        raise ValueError(f"Palette names are lowercase letters and digits, got '{name}'.")
    if name in load_ramps() or name in FAMILIES:
        raise ValueError(f"'{name}' is a built-in ramp; choose another name.")
    if kind not in ("sequential", "diverging", "categorical"):
        raise ValueError(f"kind must be sequential, diverging or categorical, got '{kind}'.")
    hexes = [rgba_to_hex(parse_color(str(c))) for c in colors]
    if len(hexes) < 2:
        raise ValueError("A palette needs at least two colours.")
    if kind == "categorical":
        USER_RAMPS[name] = {"kind": kind, "source": "user", "colors": hexes}
    else:
        USER_RAMPS[name] = {"kind": kind, "source": "user", "colors": blend(hexes),
                            "given": hexes}
    return name


def theme(name: str, base: str = "paper", ramp: str | None = None, labels: bool | None = None,
          **elements) -> str:
    """Register your own theme from a base theme and element colours, then use theme-<name>."""
    if name in kb.HOSTED or name in kb.ALIASES or name == "none" or name in (
            "paper", "midnight", "mono", "neon", "muted", "topo"):
        raise ValueError(f"'{name}' is a built-in basemap; choose another name.")
    if not name.replace("_", "").isalnum() or not name.islower():
        raise ValueError(f"Theme names are lowercase letters and digits, got '{name}'.")
    base_name, _ = kb.resolve(base)
    unknown = set(elements) - set(kb.ELEMENT_FIELDS)
    if unknown:
        raise ValueError(f"Unknown map element {sorted(unknown)}; use "
                         f"{', '.join(kb.ELEMENT_FIELDS)}.")
    colours = {k: parse_color(str(v)) for k, v in elements.items()}
    if "land" in colours and colours["land"][3] != 255:
        raise ValueError("land must be an opaque colour.")
    t = kb.apply_elements(kb.get_theme(base_name), colours)
    ground = t.background
    dark = sum(hex_to_rgba(ground)[:3]) / 3 < 128
    kb.THEMES[name] = replace(t, name=name, dark=dark,
                              labels=t.labels if labels is None else labels)
    chosen = ramp or THEME_RAMPS.get(base_name, "viridis")
    get_ramp(chosen)
    THEME_RAMPS[name] = chosen
    return name


class Gallery:
    """Swatches that show themselves in a notebook; .names lists them, .to_html saves a page."""

    def __init__(self, title: str, rows: list[tuple[str, str, str]]):
        self.title = title
        self.rows = rows

    @property
    def names(self) -> list[str]:
        return [r[0] for r in self.rows]

    def __len__(self) -> int:
        return len(self.rows)

    def _repr_html_(self) -> str:
        body = "".join(
            f'<tr><td style="padding:3px 10px 3px 0;white-space:nowrap"><code>{escape(n)}</code>'
            f'</td><td style="padding:3px 10px 3px 0;color:#6b7280;white-space:nowrap">'
            f'{escape(info)}</td><td style="padding:3px 0;width:100%">{strip}</td></tr>'
            for n, info, strip in self.rows)
        return (f'<div style="font:12px/1.4 {FONT}"><div style="font-weight:600;margin:4px 0 6px">'
                f'{escape(self.title)} ({len(self.rows)})</div><table style="border-collapse:'
                f'collapse;width:100%;max-width:820px">{body}</table></div>')

    def to_html(self, path=None) -> str:
        """A standalone page of these swatches."""
        page = (f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(self.title)}"
                f"</title></head><body style='margin:24px'>{self._repr_html_()}</body></html>")
        if path is not None:
            from pathlib import Path

            Path(path).write_text(page, encoding="utf-8")
        return page


def _strip(rec: dict) -> str:
    # A ramp as a bar: blocks for categories, a gradient otherwise
    css = "height:16px;border-radius:3px;border:1px solid #0000001a;min-width:200px"
    if rec["kind"] == "categorical":
        cells = "".join(f'<span style="flex:1;background:{c}"></span>' for c in rec["colors"])
        return f'<div style="display:flex;overflow:hidden;{css}">{cells}</div>'
    gradient = ",".join(rec["colors"])
    return f'<div style="{css};background:linear-gradient(to right,{gradient})"></div>'


def ramps(kind: str | None = None, search: str | None = None, source: str | None = None,
          checks: bool = True) -> Gallery:
    """Every ramp as a swatch strip; filter by kind, a word in the name, or source."""
    names = sorted({*load_ramps(), *USER_RAMPS}) + list(FAMILIES)
    rows = []
    for name in names:
        rec = get_ramp(name)
        if kind and rec["kind"] != kind:
            continue
        if search and search.lower() not in name and search.lower() not in rec.get("alias", ""):
            continue
        if source and source.lower() not in rec["source"]:
            continue
        info = rec["kind"]
        if "alias" in rec:
            info += f", same as {rec['alias']}"
        info += f", {SOURCES.get(rec['source'], (rec['source'],))[0]}"
        if checks and "keys" not in rec:
            c = check_ramp(name)
            flags = ["colour-blind safe"] if c["colour_blind_safe"] else []
            if c.get("lightness") == "even":
                flags.append("even lightness")
            if flags:
                info += " | " + ", ".join(flags)
        rows.append((name, info, _strip(rec)))
    return Gallery("kharita ramps", rows)


def colors(family: str | None = None) -> Gallery:
    """Every Tailwind shade kharita knows, one family per row, with each shade's number."""
    data = load_colors()
    if family is not None and family not in FAMILIES:
        raise ValueError(f"Unknown colour family '{family}'; use one of {', '.join(FAMILIES)}.")
    rows = []
    for fam in [family] if family else FAMILIES:
        cells = "".join(
            f'<span title="{fam}-{s}" style="flex:1;background:{data[fam][s]};color:'
            f'{"#fff" if sum(hex_to_rgba(data[fam][s])[:3]) < 400 else "#111827"};font-size:10px;'
            f'text-align:center;padding:6px 0">{s}</span>' for s in SHADES)
        rows.append((fam, "", f'<div style="display:flex;border-radius:4px;overflow:hidden">'
                              f"{cells}</div>"))
    return Gallery("Tailwind colours: fill-<family>-<shade>", rows)
