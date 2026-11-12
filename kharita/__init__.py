"""kharita: classified, legended Lonboard maps from one style string."""

from kharita.binder import Bound, bind
from kharita.classify import Scale
from kharita.errors import BindingError, KharitaError, KharitaWarning, StyleSyntaxError
from kharita.parser import define, explain, help, parse, utilities, validate
from kharita.spec import StyleSpec

__version__ = "0.0.3"

__all__ = [
    "BindingError",
    "Bound",
    "KharitaError",
    "KharitaWarning",
    "Scale",
    "StyleSpec",
    "StyleSyntaxError",
    "__version__",
    "bind",
    "define",
    "explain",
    "help",
    "parse",
    "utilities",
    "validate",
]
