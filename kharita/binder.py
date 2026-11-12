"""Binds a style to a table: evaluates bracket expressions and produces colour and height arrays."""

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from kharita.classify import Scale, classify_categorical, classify_numeric
from kharita.errors import BindingError, KharitaWarning
from kharita.expr import Expr
from kharita.palette import get_ramp, parse_color
from kharita.parser import check_columns, parse
from kharita.spec import (
    DEFAULT_NULL,
    DEFAULT_NUMERIC,
    DEFAULT_TEXT,
    THEME_RAMPS,
    Scheme,
    StyleSpec,
)

FEW_DISTINCT = 12
DEFAULT_HEIGHT_SHARE = 0.1


@dataclass(frozen=True)
class Bound:
    spec: StyleSpec
    n: int
    fill: np.ndarray | None = None
    fill_scale: Scale | None = None
    stroke: np.ndarray | None = None
    stroke_scale: Scale | None = None
    elevation: np.ndarray | None = None
    elevation_max: float | None = None


def _warn(message: str) -> None:
    warnings.warn(message, KharitaWarning, stacklevel=4)


def _column(data: pd.DataFrame, name: str, need_numeric: bool) -> tuple[np.ndarray, bool]:
    # One column as (values, is_numeric); text that is all numbers becomes numeric
    s = data[name]
    if pd.api.types.is_bool_dtype(s):
        if need_numeric:
            raise BindingError(f"Column '{name}' is true/false, not a number.", column=name)
        return s.to_numpy(dtype=object), False
    if pd.api.types.is_datetime64_any_dtype(s) or isinstance(s.dtype, pd.PeriodDtype):
        raise BindingError(f"Column '{name}' holds dates; date styling is not supported yet. "
                           "Convert it to a number such as the year first.", column=name)
    if pd.api.types.is_numeric_dtype(s):
        # Copy so later cleaning never writes into the user's table
        return s.to_numpy(dtype=float, na_value=np.nan, copy=True), True
    present = s.notna()
    coerced = pd.to_numeric(s, errors="coerce")
    if present.any() and coerced[present].notna().all():
        _warn(f"Column '{name}' stores numbers as text; kharita converted them. "
              f"Convert it once with df['{name}'] = pd.to_numeric(df['{name}']) to silence this.")
        return coerced.to_numpy(dtype=float, na_value=np.nan, copy=True), True
    if need_numeric:
        bad = s[present & coerced.isna()].iloc[0]
        raise BindingError(f"Column '{name}' must be numeric here, but holds text such as "
                           f"'{bad}'.", column=name)
    return s.to_numpy(dtype=object), False


def evaluate(data: pd.DataFrame, expr: Expr) -> tuple[np.ndarray, bool]:
    """Values of a bracket expression in row order, and whether they are numeric."""
    plain = expr.divisor is None and expr.factor is None
    values, numeric = _column(data, expr.column, need_numeric=not plain)
    if not numeric:
        return values, False
    if expr.divisor is not None:
        divisor, _ = _column(data, expr.divisor, need_numeric=True)
        zero = (divisor == 0) & np.isfinite(values)
        with np.errstate(divide="ignore", invalid="ignore"):
            values = values / divisor
        if zero.any():
            _warn(f"{int(zero.sum())} rows divide by zero in [{expr}]; they are shown as no data.")
    elif expr.factor is not None:
        values = values * expr.factor
    values = values.astype(float, copy=False)
    values[~np.isfinite(values)] = np.nan
    return values, True


def _colour(spec: StyleSpec, data: pd.DataFrame, expr: Expr) -> tuple[np.ndarray, Scale]:
    # Colour array and scale for fill-[...] or stroke-[...]
    label = str(expr)
    values, numeric = evaluate(data, expr)
    present = np.isfinite(values) if numeric else ~pd.isna(values)
    if not present.any():
        raise BindingError(f"[{label}] has no values to colour: every row is missing.",
                           column=expr.column)
    null = spec.null or parse_color(DEFAULT_NULL)
    ramp_kind = get_ramp(spec.ramp)["kind"] if spec.ramp else None

    scheme = spec.scheme
    if scheme is not None and not numeric and spec.from_preset("scheme"):
        # A preset's numeric scheme yields to text data
        scheme = None
    if scheme is None:
        if not numeric or ramp_kind == "categorical":
            scheme = Scheme("categorical")
        else:
            scheme = Scheme("quantiles", k=int(DEFAULT_NUMERIC[1][1:]))
            distinct = np.unique(values[present])
            if np.all(np.mod(distinct, 1) == 0) and distinct.size <= FEW_DISTINCT:
                _warn(f"[{label}] has only {distinct.size} whole-number values; if they are codes "
                      "or classes rather than amounts, add scheme-cat.")

    if scheme.kind == "categorical":
        ramp = spec.ramp or DEFAULT_TEXT[0]
        return classify_categorical(values, ramp, spec.ramp_reverse, label, null)
    if not numeric:
        raise BindingError(f"[{label}] is text, so it cannot use {scheme}; use scheme-cat.",
                           column=expr.column)
    themed = THEME_RAMPS.get(spec.theme, DEFAULT_NUMERIC[0])
    ramp = spec.ramp or ("rdbu" if scheme.kind == "diverging" else themed)
    return classify_numeric(values, scheme, ramp, spec.ramp_reverse, label, null)


def _default_height(data: pd.DataFrame) -> float:
    # Tallest feature: a tenth of the data's larger side, in metres
    try:
        from pyproj import Geod, Transformer

        x0, y0, x1, y1 = data.total_bounds
        if data.crs is not None and not data.crs.is_geographic:
            # Transform only the box corners, never every geometry
            t = Transformer.from_crs(data.crs, 4326, always_xy=True)
            xs, ys = t.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        geod = Geod(ellps="WGS84")
        mid_y = (y0 + y1) / 2
        width = geod.inv(x0, mid_y, x1, mid_y)[2]
        height = geod.inv(x0, y0, x0, y1)[2]
        side = max(width, height)
    except Exception:
        side = 0.0
    return side * DEFAULT_HEIGHT_SHARE if side > 0 else 1000.0


def _elevation(spec: StyleSpec, data: pd.DataFrame) -> tuple[np.ndarray, float]:
    # Heights in metres for extrude-[...], tallest equal to extrude-max or a default
    values, _ = evaluate(data, spec.extrude_by)
    if not np.isfinite(values).any():
        raise BindingError(f"[{spec.extrude_by}] has no values to extrude.",
                           column=spec.extrude_by.column)
    if (values < 0).any():
        _warn(f"{int((values < 0).sum())} negative values in [{spec.extrude_by}] are drawn flat.")
    clean = np.where(np.isfinite(values) & (values > 0), values, 0.0)
    top = float(clean.max())
    tallest = spec.extrude_max or _default_height(data)
    if top == 0:
        _warn(f"[{spec.extrude_by}] has no positive values; nothing is raised.")
        return np.zeros(len(values), dtype=np.float32), tallest
    return (clean / top * tallest).astype(np.float32), tallest


def bind(data: pd.DataFrame, style) -> Bound:
    """Compile a style against a table: colour and height arrays in the table's row order."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"Expected a GeoDataFrame or DataFrame, got {type(data).__name__}.")
    spec = parse(style) if isinstance(style, str) else style
    check_columns(spec, data.columns)
    fill, fill_scale = (_colour(spec, data, spec.fill_by) if spec.fill_by is not None
                        else (None, None))
    stroke, stroke_scale = (_colour(spec, data, spec.stroke_by) if spec.stroke_by is not None
                            else (None, None))
    elevation, tallest = (_elevation(spec, data) if spec.extrude_by is not None
                          else (None, None))
    return Bound(spec=spec, n=len(data), fill=fill, fill_scale=fill_scale, stroke=stroke,
                 stroke_scale=stroke_scale, elevation=elevation, elevation_max=tallest)
