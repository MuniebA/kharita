"""Loads the bundled colour palette and ramp tables."""

import json
from functools import cache
from importlib.resources import files

FAMILIES = (
    "slate", "gray", "zinc", "neutral", "stone", "red", "orange", "amber", "yellow", "lime",
    "green", "emerald", "teal", "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia",
    "pink", "rose",
)
SHADES = ("50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950")


@cache
def load_colors() -> dict:
    # UI palette: family -> shade -> hex, plus white and black
    return json.loads(files("kharita.data").joinpath("colors.json").read_text(encoding="utf-8"))


@cache
def load_ramps() -> dict:
    # Data ramps: name -> {kind, source, colors}
    return json.loads(files("kharita.data").joinpath("ramps.json").read_text(encoding="utf-8"))
