"""kharita: classified, legended Lonboard maps from one style string."""

from kharita.adapter import layer
from kharita.binder import Bound, bind
from kharita.classify import Scale
from kharita.errors import BindingError, KharitaError, KharitaWarning, StyleSyntaxError
from kharita.maps import Map, legend, map
from kharita.parser import define, explain, help, parse, utilities, validate
from kharita.spec import StyleSpec

__version__ = "0.0.6"

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
    "define",
    "explain",
    "help",
    "layer",
    "legend",
    "map",
    "parse",
    "utilities",
    "validate",
]
