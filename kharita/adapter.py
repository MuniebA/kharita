"""Turns a GeoDataFrame and a style into Lonboard layers."""

import warnings

import numpy as np
import pandas as pd

from kharita.binder import Bound, bind
from kharita.errors import BindingError, KharitaWarning
from kharita.palette import parse_color

POLYGONS = ("Polygon", "MultiPolygon")
LINES = ("LineString", "MultiLineString", "LinearRing")
POINTS = ("Point", "MultiPoint")

POLYGON_FILL = "slate-500/80"
POLYGON_STROKE = "white"
POLYGON_STROKE_WIDTH = 1.0
LINE_COLOR = "slate-600"
LINE_WIDTH = 2.0
POINT_FILL = "indigo-500/90"
POINT_SIZE = 4.0
# Halo: two faint bands, the outer wider and fainter, as share of the colour's alpha
HALO_BANDS = ((9.0, 0.15), (3.0, 0.30))


def _warn(message: str) -> None:
    warnings.warn(message, KharitaWarning, stacklevel=4)


def _rgba(value) -> list[int]:
    # Spec colour or palette token to a plain list Lonboard accepts
    return list(parse_color(value)) if isinstance(value, str) else list(value)


def _format_column(s: pd.Series) -> pd.Series:
    # Tooltip text: thousands separators and at most two decimals
    if pd.api.types.is_bool_dtype(s) or not pd.api.types.is_numeric_dtype(s):
        return s.astype("string")
    values = s.astype(float)
    whole = values.dropna().mod(1).eq(0).all()

    def one(v: float) -> str | None:
        if pd.isna(v):
            return None
        if whole:
            return f"{v:,.0f}"
        return f"{v:,.2f}" if abs(v) < 1000 else f"{v:,.0f}"

    return values.map(one).astype("string")


def check_geodata(gdf) -> None:
    """Raise a clear error unless gdf is a GeoDataFrame with a CRS."""
    import geopandas as gpd

    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError(f"Expected a GeoDataFrame, got {type(gdf).__name__}.")
    if gdf.crs is None:
        raise BindingError(
            "The GeoDataFrame has no CRS, so kharita cannot place it on the map. If the "
            "coordinates are longitude and latitude, run gdf = gdf.set_crs('EPSG:4326'); "
            "otherwise set the CRS the data was made in."
        )


def _subset(gdf, rows: np.ndarray, columns: list[str]):
    # Only the geometry and the columns the style shows, in EPSG:4326
    sub = gdf.iloc[rows][[*columns, gdf.geometry.name]]
    sub = sub.rename_geometry("geometry") if gdf.geometry.name != "geometry" else sub
    if not sub.crs.equals("EPSG:4326"):
        sub = sub.to_crs(4326)
    for col in columns:
        sub[col] = _format_column(sub[col])
    return sub.reset_index(drop=True)


def _pick(array, rows: np.ndarray):
    return None if array is None else array[rows]


def _common(spec) -> dict:
    # Interaction and opacity settings shared by every layer type
    kw = {"pickable": bool(spec.tooltip) or spec.highlight is not None}
    if spec.highlight is not None:
        kw.update(auto_highlight=True, highlight_color=list(spec.highlight))
    if spec.opacity is not None:
        kw["opacity"] = spec.opacity
    return kw


EDGE_SHADE = 0.7


def _edges(fill, spec) -> np.ndarray | list:
    # Wireframe colour for extruded polygons: the fill a shade darker, never default white
    if spec.stroke is not None:
        return _rgba(spec.stroke)
    if isinstance(fill, np.ndarray):
        out = fill.copy()
        out[:, :3] = (out[:, :3] * EDGE_SHADE).astype(np.uint8)
        return out
    r, g, b, a = fill
    return [int(r * EDGE_SHADE), int(g * EDGE_SHADE), int(b * EDGE_SHADE), a]


def _polygon_layer(sub, spec, b: Bound, rows):
    from lonboard import PolygonLayer

    fill = _pick(b.fill, rows)
    stroke = _pick(b.stroke, rows)
    kw = _common(spec)
    kw.update(
        get_fill_color=fill if fill is not None else _rgba(spec.fill or POLYGON_FILL),
        get_line_color=stroke if stroke is not None else _rgba(spec.stroke or POLYGON_STROKE),
        get_line_width=spec.stroke_width or POLYGON_STROKE_WIDTH,
        line_width_units="pixels",
        stroked=True,
    )
    if b.elevation is not None:
        kw.update(extruded=True, get_elevation=_pick(b.elevation, rows), wireframe=True)
        if stroke is None:
            kw["get_line_color"] = _edges(kw["get_fill_color"], spec)
    return PolygonLayer.from_geopandas(sub, **kw)


def _line_layer(sub, spec, b: Bound, rows):
    from lonboard import PathLayer

    data = b.stroke if b.stroke is not None else b.fill
    color = _pick(data, rows)
    if color is None:
        color = _rgba(spec.stroke or spec.fill or LINE_COLOR)
    kw = _common(spec)
    kw.update(get_color=color, get_width=spec.stroke_width or LINE_WIDTH, width_units="pixels",
              cap_rounded=True, joint_rounded=True)
    return PathLayer.from_geopandas(sub, **kw)


def _point_layer(sub, spec, b: Bound, rows):
    from lonboard import ScatterplotLayer

    fill = _pick(b.fill, rows)
    stroke = _pick(b.stroke, rows)
    kw = _common(spec)
    kw.update(
        get_fill_color=fill if fill is not None else _rgba(spec.fill or POINT_FILL),
        get_radius=spec.size or POINT_SIZE,
        radius_units="pixels",
    )
    if stroke is not None or spec.stroke is not None or spec.stroke_width is not None:
        kw.update(
            stroked=True,
            get_line_color=stroke if stroke is not None else _rgba(spec.stroke or "white"),
            get_line_width=spec.stroke_width or 1.0,
            line_width_units="pixels",
        )
    return ScatterplotLayer.from_geopandas(sub, **kw)


def _halo_layers(sub, spec, kind: str) -> list:
    # Faint wide bands drawn under the layer: along outlines, lines or around points
    from lonboard import PathLayer, ScatterplotLayer

    r, g, b, a = spec.halo
    out = []
    if kind == "points":
        base = spec.size or POINT_SIZE
        for extra, share in HALO_BANDS:
            color = [r, g, b, round(a * share)]
            out.append(ScatterplotLayer.from_geopandas(
                sub[["geometry"]], get_fill_color=color, get_radius=base + extra,
                radius_units="pixels", pickable=False))
        return out
    edges = sub[["geometry"]]
    if kind == "polygons":
        edges = edges.set_geometry(edges.boundary)
        base = spec.stroke_width or POLYGON_STROKE_WIDTH
    else:
        base = spec.stroke_width or LINE_WIDTH
    for extra, share in HALO_BANDS:
        color = [r, g, b, round(a * share)]
        out.append(PathLayer.from_geopandas(edges, get_color=color, get_width=base + extra,
                                            width_units="pixels", cap_rounded=True,
                                            joint_rounded=True, pickable=False))
    return out


BUILDERS = (("polygons", POLYGONS, _polygon_layer), ("lines", LINES, _line_layer),
            ("points", POINTS, _point_layer))


def build(gdf, style, colors: dict | None = None, order: list | None = None) -> tuple[list, Bound]:
    """Lonboard layers for a GeoDataFrame and a style, plus the bound arrays and scales."""
    check_geodata(gdf)
    b = bind(gdf, style, colors=colors, order=order)
    spec = b.spec
    geom = gdf.geometry
    present = (geom.notna() & ~geom.is_empty).to_numpy()
    if not present.all():
        _warn(f"{int((~present).sum())} rows have no geometry and are not drawn.")
    types = geom.geom_type.to_numpy()
    tooltip = list(spec.tooltip or ())

    layers, drawn = [], np.zeros(len(gdf), dtype=bool)
    for kind, names, builder in BUILDERS:
        mask = present & np.isin(types, names)
        if not mask.any():
            continue
        rows = np.flatnonzero(mask)
        sub = _subset(gdf, rows, tooltip)
        if spec.halo is not None:
            layers.extend(_halo_layers(sub, spec, kind))
        layers.append(builder(sub, spec, b, rows))
        drawn |= mask
    skipped = present & ~drawn
    if skipped.any():
        kinds = ", ".join(sorted(set(types[skipped])))
        _warn(f"{int(skipped.sum())} rows of type {kinds} are not drawn; explode them into "
              "polygons, lines or points first.")
    if not layers:
        raise BindingError("Nothing to draw: no row has a polygon, line or point geometry.")
    return layers, b


def layer(gdf, style, colors: dict | None = None, order: list | None = None) -> list:
    """Native Lonboard layers for a style: one per geometry type present."""
    return build(gdf, style, colors=colors, order=order)[0]
