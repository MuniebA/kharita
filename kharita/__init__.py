"""kharita: classified, legended Lonboard maps from one style string."""

from kharita.adapter import layer
from kharita.basemaps import imagery
from kharita.binder import Bound, bind
from kharita.catalog import check_ramp, colors, palette, ramps, theme
from kharita.classify import Scale
from kharita.errors import BindingError, KharitaError, KharitaWarning, StyleSyntaxError
from kharita.maps import Map, compare, legend, map
from kharita.parser import define, explain, help, parse, utilities, validate
from kharita.spec import StyleSpec
from kharita.terrain import contours

__version__ = "0.0.10"

__all__ = [
    "BindingError",
    "Bound",
    "KharitaError",
    "KharitaWarning",
    "Map",
    "Scale",
    "StyleSpec",
    "StyleSyntaxError",
    "__version__",
    "bind",
    "check_ramp",
    "colors",
    "compare",
    "contours",
    "define",
    "explain",
    "help",
    "imagery",
    "layer",
    "legend",
    "map",
    "palette",
    "parse",
    "ramps",
    "theme",
    "utilities",
    "validate",
]
