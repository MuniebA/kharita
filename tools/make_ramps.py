"""Builds kharita/data/ramps.json from open colour collections, keeping existing entries.

Run with matplotlib, cmcrameri, cmocean and palettable installed:
    python tools/make_ramps.py kharita/data/ramps.json
"""

import json
import sys
from pathlib import Path

import cmcrameri.cm as crameri
import cmocean
import matplotlib
import numpy as np
from matplotlib.colors import to_hex
from palettable import cartocolors
from palettable.colorbrewer import qualitative as brewer_qual

STOPS = 11
TAILWIND_FAMILIES = {
    "slate", "gray", "zinc", "neutral", "stone", "red", "orange", "amber", "yellow", "lime",
    "green", "emerald", "teal", "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia",
    "pink", "rose",
}


def sample(cmap) -> list[str]:
    # 11 evenly spaced stops, as the original 24 ramps were made
    return [to_hex(cmap(x)) for x in np.linspace(0, 1, STOPS)]


def entry(kind, source, colors, **extra):
    return {"kind": kind, "source": source, "colors": colors, **extra}


out = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
original = set(out)


def add(name, record):
    # Never overwrite an existing ramp, never take a Tailwind family name
    assert name not in TAILWIND_FAMILIES, name
    if name not in original:
        out[name] = record


# ColorBrewer, through matplotlib, plus the qualitative sets at their largest size
for name in ("BuGn", "GnBu", "Greys", "PuBu", "PuBuGn", "PuRd", "RdPu", "YlOrBr"):
    add(name.lower(), entry("sequential", "colorbrewer", sample(matplotlib.colormaps[name])))
for name in ("PRGn", "RdGy", "RdYlGn", "Spectral"):
    add(name.lower(), entry("diverging", "colorbrewer", sample(matplotlib.colormaps[name])))
for name, n in (("Accent", 8), ("Pastel1", 9), ("Pastel2", 8), ("Set3", 12)):
    pal = getattr(brewer_qual, f"{name}_{n}")
    add(name.lower(), entry("categorical", "colorbrewer", [c.lower() for c in pal.hex_colors]))

# matplotlib extras
add("turbo", entry("sequential", "matplotlib-turbo", sample(matplotlib.colormaps["turbo"])))

# Crameri scientific colour maps
SEQ = ("acton", "bamako", "batlow", "batlowK", "batlowW", "bilbao", "buda", "davos", "devon",
       "glasgow", "grayC", "hawaii", "imola", "lajolla", "lapaz", "lipari", "navia", "nuuk",
       "oslo", "tokyo", "turku")
DIV = ("bam", "berlin", "broc", "cork", "lisbon", "managua", "roma", "tofino", "vanimo", "vik",
       "bukavu", "fes", "oleron")
for name in SEQ:
    add(name.lower(), entry("sequential", "crameri", sample(crameri.cmaps[name])))
for name in DIV:
    add(name.lower(), entry("diverging", "crameri", sample(crameri.cmaps[name])))

# cmocean
for name in ("algae", "amp", "deep", "dense", "haline", "ice", "matter", "rain", "solar", "speed",
             "tempo", "thermal", "turbid"):
    add(name, entry("sequential", "cmocean", sample(cmocean.cm.cmap_d[name])))
for name in ("balance", "curl", "delta", "diff", "tarn", "topo"):
    add(name, entry("diverging", "cmocean", sample(cmocean.cm.cmap_d[name])))

# CARTOColors at their largest class count
for kind, mod in (("sequential", cartocolors.sequential), ("diverging", cartocolors.diverging),
                  ("categorical", cartocolors.qualitative)):
    names = sorted({n.rsplit("_", 1)[0] for n in dir(mod)
                    if n[0].isupper() and n.rsplit("_", 1)[-1].isdigit()})
    for base in names:
        sizes = [int(n.rsplit("_", 1)[1]) for n in dir(mod) if n.rsplit("_", 1)[0] == base
                 and n.rsplit("_", 1)[-1].isdigit()]
        pal = getattr(mod, f"{base}_{max(sizes)}")
        name = base.lower()
        if name in TAILWIND_FAMILIES:
            name = f"carto-{name}"
        add(name, entry(kind, "cartocolors", [c.lower() for c in pal.hex_colors]))

# kharita originals and standards
add("terrain", entry("sequential", "kharita", ["#2e6b34", "#5f9a44", "#a7c46a", "#e3dd9c",
                                               "#d8b276", "#b0815a", "#86644f", "#f4f1ec"]))
add("ndvi", entry("sequential", "kharita", ["#8c5a2b", "#b8875a", "#dcc48e", "#e9edb0",
                                            "#b5d97b", "#73b45a", "#2f8a3c", "#0b5d2a"]))
add("aurora", entry("sequential", "kharita", ["#2e1065", "#4338ca", "#0891b2", "#2dd4bf",
                                              "#a7f3d0"]))
add("ember", entry("sequential", "kharita", ["#1c0a06", "#5b1a0b", "#9a2f0c", "#d9541a",
                                             "#f59e3b", "#fde68a"]))
add("ipc", entry("categorical", "fews-net", ["#cdfacd", "#fae61e", "#e67800", "#c80000", "#640000"],
                 keys=[{"value": "1", "color": "#cdfacd", "label": "1 Minimal"},
                       {"value": "2", "color": "#fae61e", "label": "2 Stressed"},
                       {"value": "3", "color": "#e67800", "label": "3 Crisis"},
                       {"value": "4", "color": "#c80000", "label": "4 Emergency"},
                       {"value": "5", "color": "#640000", "label": "5 Famine"}]))
WORLDCOVER = [("10", "#006400", "Tree cover"), ("20", "#ffbb22", "Shrubland"),
              ("30", "#ffff4c", "Grassland"), ("40", "#f096ff", "Cropland"),
              ("50", "#fa0000", "Built-up"), ("60", "#b4b4b4", "Bare / sparse vegetation"),
              ("70", "#f0f0f0", "Snow and ice"), ("80", "#0064c8", "Permanent water bodies"),
              ("90", "#0096a0", "Herbaceous wetland"), ("95", "#00cf75", "Mangroves"),
              ("100", "#fae6a0", "Moss and lichen")]
add("worldcover", entry("categorical", "esa-worldcover", [c for _, c, _ in WORLDCOVER],
                        keys=[{"value": v, "color": c, "label": lab} for v, c, lab in WORLDCOVER]))
LANDUSE = [("residential", "#fcd34d"), ("commercial", "#ef4444"), ("retail", "#ef4444"),
           ("industrial", "#a855f7"), ("institutional", "#3b82f6"), ("education", "#3b82f6"),
           ("medical", "#3b82f6"), ("civic", "#3b82f6"), ("religious", "#6366f1"),
           ("park", "#22c55e"), ("recreation", "#86efac"), ("agriculture", "#a3a635"),
           ("transportation", "#9ca3af"), ("utilities", "#6b7280"), ("mixed", "#f97316"),
           ("vacant", "#e7e5e4"), ("water", "#7dd3fc")]
add("landuse", entry("categorical", "kharita-lbcs", list(dict.fromkeys(c for _, c in LANDUSE)),
                     keys=[{"value": v, "color": c, "label": v} for v, c in LANDUSE]))

# Friendly names point at another ramp
for name, target, reverse in (("heatwave", "rdbu", True), ("ocean", "deep", False),
                              ("forest", "ylgn", False), ("desert", "ylorbr", False),
                              ("hypsometric", "terrain", False)):
    record = dict(out[target])
    record["colors"] = record["colors"][::-1] if reverse else record["colors"]
    add(name, {**record, "alias": target + ("-r" if reverse else "")})

Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
kinds = {}
for v in out.values():
    kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
print(len(out), "ramps", kinds)
