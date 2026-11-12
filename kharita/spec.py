"""The typed StyleSpec a style string compiles to."""

from dataclasses import dataclass, field

from kharita.expr import Expr
from kharita.palette import RGBA
from kharita.tokenizer import Token

DEFAULT_NULL = "gray-300"
DEFAULT_NUMERIC = ("viridis", "q5")
DEFAULT_TEXT = ("set2", "cat")
LEGEND_POSITIONS = {"tl": "top left", "tr": "top right", "bl": "bottom left", "br": "bottom right"}


@dataclass(frozen=True)
class Scheme:
    kind: str
    k: int | None = None
    breaks: tuple[float, ...] | None = None
    center: float | None = None

    def __str__(self) -> str:
        if self.kind == "quantiles":
            return f"quantiles, {self.k} classes"
        if self.kind == "equal":
            return f"equal interval, {self.k} classes"
        if self.kind == "breaks":
            return "breaks at " + ", ".join(f"{b:g}" for b in self.breaks)
        if self.kind == "diverging":
            return f"diverging around {self.center:g}"
        return "categorical"


@dataclass
class StyleSpec:
    fill: RGBA | None = None
    fill_by: Expr | None = None
    ramp: str | None = None
    ramp_reverse: bool = False
    scheme: Scheme | None = None
    stroke: RGBA | None = None
    stroke_by: Expr | None = None
    stroke_width: float | None = None
    size: float | None = None
    opacity: float | None = None
    highlight: RGBA | None = None
    null: RGBA | None = None
    tooltip: tuple[str, ...] | None = None
    extrude_by: Expr | None = None
    extrude_max: float | None = None
    basemap: str | None = None
    legend: bool = True
    legend_position: str | None = None
    origins: dict[str, list[Token]] = field(default_factory=dict, repr=False)

    def from_preset(self, group: str) -> bool:
        # True when a group was set only by a preset, so it may give way to the data
        tokens = self.origins.get(group, [])
        return bool(tokens) and all(t.via for t in tokens)

    @property
    def columns(self) -> tuple[str, ...]:
        # Every column the style reads, in first-seen order
        found: list[str] = []
        for expr in (self.fill_by, self.stroke_by, self.extrude_by):
            if expr:
                found.extend(expr.columns)
        found.extend(self.tooltip or ())
        return tuple(dict.fromkeys(found))
