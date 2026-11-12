"""Adapter: layer types, units, columns sent, CRS, alignment of colours with rows."""

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from lonboard import PathLayer, PolygonLayer, ScatterplotLayer
from shapely.geometry import LineString, Point

import kharita as kh
from kharita.adapter import _subset, build


def colours(layer, attr="get_fill_color"):
    # Per-row colours a layer holds, as a list of tuples
    import pyarrow as pa

    value = getattr(layer, attr)
    if isinstance(value, (list, tuple, np.ndarray)):
        arr = np.asarray(value)
    else:
        arr = pa.chunked_array(value).combine_chunks().flatten().to_numpy(zero_copy_only=False)
    return [tuple(int(v) for v in row) for row in arr.reshape(-1, 4)]


def test_polygons_use_pixel_outlines(polygons):
    (layer,) = kh.layer(polygons, "fill-[pop] stroke-2")
    assert isinstance(layer, PolygonLayer)
    assert layer.line_width_units == "pixels"
    assert layer.get_line_width == 2


def test_lines_and_points_get_their_own_layers(lines, points):
    (path,) = kh.layer(lines, "stroke-[kind] stroke-3")
    assert isinstance(path, PathLayer) and path.width_units == "pixels"
    (dots,) = kh.layer(points, "fill-[value] size-6 stroke-white")
    assert isinstance(dots, ScatterplotLayer)
    assert dots.radius_units == "pixels" and dots.get_radius == 6 and dots.stroked


def test_only_style_columns_are_sent(polygons):
    (plain,) = kh.layer(polygons, "fill-[pop]")
    assert plain.table.schema.names == ["geometry"]
    (tip,) = kh.layer(polygons, "fill-[pop] tooltip-[name,pop]")
    assert tip.table.schema.names == ["name", "pop", "geometry"]
    assert tip.pickable


def test_tooltip_numbers_are_formatted(polygons):
    sub = _subset(polygons, np.arange(10), ["pop", "area", "name"])
    assert sub["pop"].iloc[8] == "20,000"
    assert pd.isna(sub["pop"].iloc[9])
    assert sub["area"].iloc[1] == "2"
    assert sub["name"].iloc[0] == "state 0"


def test_mixed_geometries_keep_colours_aligned(polygons, points):
    frame = gpd.GeoDataFrame(
        {"v": [1.0, 2.0, 3.0, 4.0, 5.0]},
        geometry=[polygons.geometry[0], points.geometry[0], polygons.geometry[1], None,
                  points.geometry[1]],
        crs="EPSG:4326",
    )
    with pytest.warns(kh.KharitaWarning, match="no geometry"):
        layers, b = build(frame, "fill-[v] scheme-[1.5,2.5,3.5,4.5]")
    poly, pts = layers
    expected = [tuple(int(v) for v in b.fill[i]) for i in (0, 2)]
    assert colours(poly) == expected
    assert colours(pts) == [tuple(int(v) for v in b.fill[i]) for i in (1, 4)]


def test_index_order_does_not_matter(polygons):
    shuffled = polygons.iloc[::-1].set_index(pd.Index(range(100, 110)))
    layers, b = build(shuffled, "fill-[pop] scheme-q3")
    assert colours(layers[0]) == [tuple(int(v) for v in r) for r in b.fill]


def test_missing_crs_explains_the_fix(no_crs):
    with pytest.raises(kh.BindingError, match="set_crs"):
        kh.layer(no_crs, "fill-red-500")


def test_projected_data_is_reprojected(polygons):
    sub = _subset(polygons.to_crs(3857), np.arange(10), [])
    assert sub.crs.equals("EPSG:4326")
    assert sub.total_bounds == pytest.approx(polygons.total_bounds)
    assert list(sub.columns) == ["geometry"]


def test_user_frame_is_untouched(polygons):
    before = polygons.copy()
    kh.layer(polygons.to_crs(3857), "fill-[pop] tooltip-[pop]")
    kh.layer(polygons, "fill-[pop] tooltip-[pop,name]")
    pd.testing.assert_frame_equal(polygons, before)


def test_highlight_and_opacity(polygons):
    (layer,) = kh.layer(polygons, "fill-[pop] highlight-amber-400 opacity-70")
    assert layer.auto_highlight and layer.pickable
    assert list(layer.highlight_color) == [251, 191, 36, 255]
    assert layer.opacity == pytest.approx(0.7)


def test_extrusion_sets_heights_and_edges(polygons):
    (layer,) = kh.layer(polygons, "fill-[pop] extrude-[pop] extrude-max-500")
    assert layer.extruded and layer.wireframe


def test_constant_defaults(polygons, lines):
    (poly,) = kh.layer(polygons, "")
    assert list(poly.get_fill_color) == [100, 116, 139, 204]
    (path,) = kh.layer(lines, "")
    assert path.get_width == 2


def test_geometry_collections_are_skipped(polygons):
    from shapely.geometry import GeometryCollection

    frame = gpd.GeoDataFrame(
        geometry=[polygons.geometry[0], GeometryCollection([Point(0, 0), LineString([(0, 0),
                                                                                   (1, 1)])])],
        crs="EPSG:4326",
    )
    with pytest.warns(kh.KharitaWarning, match="GeometryCollection"):
        assert len(kh.layer(frame, "fill-red-500")) == 1


def test_nothing_drawable_raises():
    frame = gpd.GeoDataFrame(geometry=[None, None], crs="EPSG:4326")
    with pytest.raises(kh.BindingError, match="Nothing to draw"), pytest.warns(kh.KharitaWarning):
        kh.layer(frame, "")


def test_not_a_geodataframe(polygons):
    with pytest.raises(TypeError, match="GeoDataFrame"):
        kh.layer(pd.DataFrame(polygons.drop(columns="geometry")), "")


def test_stroke_by_data_on_lines(lines):
    layers, b = build(lines, "stroke-[kind]")
    assert b.stroke_scale.kind == "categorical"
    assert colours(layers[0], "get_color") == [tuple(int(v) for v in r) for r in b.stroke]


def test_fill_and_stroke_from_data_conflict(lines):
    with pytest.raises(kh.StyleSyntaxError, match="Only one colour"):
        kh.layer(lines, "fill-[kind] stroke-[kind]")
