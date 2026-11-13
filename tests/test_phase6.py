"""Phase 6a: size and width by data, dashes, data labels, the topo theme and contours."""

import base64
import json
import math

import numpy as np
import pytest
from lonboard import PathLayer, PolygonLayer, ScatterplotLayer

import kharita as kh
from kharita import basemaps as kb
from kharita import terrain


def style_of(m) -> dict:
    # The MapLibre style JSON a kh.Map hands to Lonboard
    return json.loads(base64.b64decode(m.lonboard.basemap.style.split(",", 1)[1]))


# Size by data

def test_size_by_data_scales_area_not_radius(points):
    (layer,) = kh.layer(points, "size-[value] size-max-20")
    radii = np.asarray(layer.get_radius)
    assert radii.max() == pytest.approx(20)
    # Value 1 of 5 has a fifth of the area, so sqrt(1/5) of the radius
    assert radii[0] == pytest.approx(20 * math.sqrt(1 / 5), rel=1e-5)


def test_size_on_polygons_explains_the_fix(polygons):
    with pytest.raises(kh.BindingError, match="representative_point"):
        kh.layer(polygons, "size-[pop]")


def test_negative_sizes_warn_and_vanish(points):
    df = points.assign(change=[-3, 1, 2, 3, 4])
    with pytest.warns(kh.KharitaWarning, match="negative"):
        b = kh.bind(df, "size-[change]")
    assert b.radius[0] == 0


def test_size_legend_shows_nested_circles(points):
    html = kh.map(points, "size-[value] fill-rose-500").legend_html()
    assert "Circle size shows" in html and html.count("<circle") == 3


def test_size_max_needs_size_by():
    with pytest.raises(kh.StyleSyntaxError, match="size-max needs"):
        kh.parse("size-max-30")


# Width by data

def test_width_by_data_on_lines(lines):
    df = lines.assign(rank=[3, 2, 1])
    (layer,) = kh.layer(df, "width-[rank] width-max-6 stroke-slate-700")
    widths = np.asarray(layer.get_width)
    assert widths.tolist() == pytest.approx([6, 4, 2])


def test_width_never_below_half_a_pixel(lines):
    df = lines.assign(rank=[100, 1, 0])
    (layer,) = kh.layer(df, "width-[rank]")
    assert np.asarray(layer.get_width).min() == pytest.approx(0.5)


def test_width_on_polygon_outlines(polygons):
    (layer,) = kh.layer(polygons.assign(w=range(1, 11)), "fill-white width-[w]")
    assert isinstance(layer, PolygonLayer) and len(np.asarray(layer.get_line_width)) == 10


def test_width_legend(lines):
    html = kh.map(lines.assign(rank=[3, 2, 1]), "width-[rank]").legend_html()
    assert "Line width shows" in html


def test_width_constant_points_to_stroke():
    with pytest.raises(kh.StyleSyntaxError, match="stroke-3"):
        kh.parse("width-3")


# Dashes

def test_dash_on_lines_and_outlines(lines, polygons):
    (path,) = kh.layer(lines, "dash-4-2")
    assert isinstance(path, PathLayer) and path.get_dash_array == [4.0, 2.0]
    (poly,) = kh.layer(polygons, "fill-transparent dash-3")
    assert poly.get_dash_array == [3.0, 3.0]


def test_dash_on_points_warns(points):
    with pytest.warns(kh.KharitaWarning, match="dash"):
        (layer,) = kh.layer(points, "dash-2")
    assert isinstance(layer, ScatterplotLayer)


@pytest.mark.parametrize("bad", ["dash-0", "dash-a", "dash-1-2-3"])
def test_bad_dashes(bad):
    with pytest.raises(kh.StyleSyntaxError):
        kh.parse(bad)


# Data labels

def test_labels_go_into_the_theme_style(polygons):
    m = kh.map(polygons.assign(name=[f"s{i}" for i in range(10)]), "fill-[pop] basemap-paper "
               "label-[name]")
    s = style_of(m)
    layer = next(lyr for lyr in s["layers"] if lyr["id"] == f"{kb.DATA_LABEL}-0")
    assert s["layers"][-1] is layer or s["layers"][-1]["id"].startswith(kb.DATA_LABEL)
    feats = s["sources"][f"{kb.DATA_LABEL}-0"]["data"]["features"]
    assert len(feats) == 10 and feats[0]["geometry"]["type"] == "Point"


def test_labels_without_theme_labels_still_sit_above_data(polygons):
    m = kh.map(polygons.assign(name="x"), "fill-[pop] basemap-muted label-[name]")
    assert m.lonboard.basemap.mode == "interleaved"
    assert m.lonboard.layers[0].before_id == f"{kb.DATA_LABEL}-0"
    assert "glyphs" in style_of(m)


def test_line_and_point_label_placement(lines, points):
    s = style_of(kh.map(lines, "basemap-paper label-[kind]"))
    layer = next(lyr for lyr in s["layers"] if lyr["id"].startswith(kb.DATA_LABEL))
    assert layer["layout"]["symbol-placement"] == "line"
    s = style_of(kh.map(points, "basemap-paper label-[value]"))
    layer = next(lyr for lyr in s["layers"] if lyr["id"].startswith(kb.DATA_LABEL))
    assert "text-variable-anchor" in layer["layout"]


def test_label_numbers_are_formatted(points):
    df = points.assign(v=[1200.0, 50.5, 3.0, np.nan, 7.0])
    s = style_of(kh.map(df, "basemap-paper label-[v]"))
    texts = [f["properties"]["t"] for f in s["sources"][f"{kb.DATA_LABEL}-0"]["data"]["features"]]
    assert texts == ["1,200", "50.5", "3", "7"]


def test_labels_need_a_kharita_basemap(polygons):
    with pytest.raises(kh.StyleSyntaxError, match="not one"):
        kh.parse("label-[name] basemap-light")
    with pytest.raises(ValueError, match="kharita basemap"):
        kh.Map(basemap="light").add(polygons.assign(name="x"), "fill-[pop] label-[name]")


def test_too_many_labels_warn(points, monkeypatch):
    from kharita import maps

    monkeypatch.setattr(maps, "LABEL_LIMIT", 2)
    with pytest.warns(kh.KharitaWarning, match="labels"):
        kh.map(points, "basemap-paper label-[value]")


# The topo theme

def test_topo_theme():
    assert "topo" in kb.THEMES and not kb.is_dark("topo")
    assert kh.explain("fill-[pop] theme-topo").count("terrain") >= 1


# Contours

def _cone(z, x, y):
    # A 3,000 m cone centred on global pixel (centre, centre), drawn tile by tile
    centre = 256 * 2 ** z / 2 + 300
    cols, rows = np.meshgrid(np.arange(256) + x * 256, np.arange(256) + y * 256)
    dist = np.hypot(cols - centre, rows - centre)
    return np.maximum(3000 - 12 * dist, 0).astype(np.float32)


@pytest.fixture
def cone(monkeypatch):
    monkeypatch.setattr(terrain, "_fetch_tile", _cone)
    z = 10
    c = 256 * 2 ** z / 2 + 300
    lon, lat = terrain._to_lonlat(np.array([c - 300, c + 300]), np.array([c + 300, c - 300]), z)
    return (float(lon[0]), float(lat[0]), float(lon[1]), float(lat[1]))


def test_contours_from_tiles(cone):
    c = kh.contours(cone, zoom=10, interval=250)
    assert c.crs.to_epsg() == 4326
    assert sorted(c["elevation"].unique()) == [250.0 * i for i in range(1, 12)]
    assert set(c.loc[c["index"], "elevation"]) == {1250.0, 2500.0}
    assert (c.loc[c["index"], "weight"] == 2).all() and (c.loc[~c["index"], "weight"] == 1).all()
    w, s, e, n = cone
    xmin, ymin, xmax, ymax = c.total_bounds
    assert xmin >= w - 1e-9 and xmax <= e + 1e-9 and ymin >= s - 1e-9 and ymax <= n + 1e-9


def test_contour_interval_is_chosen_for_you(cone):
    c = kh.contours(cone, zoom=10)
    assert c.attrs["interval"] in (100, 200, 250, 500)


def test_contours_style_with_preset_topo(cone):
    c = kh.contours(cone, zoom=10, interval=500)
    (layer,) = kh.layer(c, "preset-topo")
    widths = np.asarray(layer.get_width)
    assert widths.max() == pytest.approx(1.6) and widths.min() == pytest.approx(0.8)


def test_auto_zoom_keeps_tiles_few():
    bbox = (21.8, 8.7, 38.6, 22.2)
    z = terrain.auto_zoom(bbox)
    tx0, ty0, tx1, ty1 = terrain._tile_range(bbox, z)
    assert (tx1 - tx0 + 1) * (ty1 - ty0 + 1) <= terrain.MAX_TILES
    assert terrain.auto_zoom((24.2, 12.9, 24.3, 13.0)) == terrain.MAX_ZOOM


@pytest.mark.parametrize("span, expected", [(3000, 200), (450, 25), (95, 5), (0, 1)])
def test_nice_interval(span, expected):
    assert terrain.nice_interval(span) == expected


def test_smoothing_keeps_flat_ground_flat():
    flat = np.full((20, 20), 400.0)
    assert np.allclose(terrain._smooth(flat, 1.5), 400.0)


def test_bad_bounds():
    with pytest.raises(ValueError, match="west, south, east, north"):
        kh.contours((40, 10, 30, 20))


# Phase 6b: cleaner contours

def _noisy_cone(z, x, y):
    # The cone with bumps, like real elevation tiles
    rng = np.random.default_rng(x * 1000 + y)
    return _cone(z, x, y) + rng.normal(0, 15, (256, 256)).astype(np.float32)


@pytest.fixture
def noisy(cone, monkeypatch):
    monkeypatch.setattr(terrain, "_fetch_tile", _noisy_cone)
    return cone


def test_lower_detail_keeps_fewer_lines(noisy):
    counts = {d: len(kh.contours(noisy, zoom=10, interval=100, detail=d))
              for d in ("high", "medium", "low")}
    raw = len(kh.contours(noisy, zoom=10, interval=100, smooth=0))
    assert raw > counts["high"] >= counts["medium"] >= counts["low"] > 0


def test_contour_settings_are_recorded(noisy):
    c = kh.contours(noisy, zoom=10, interval=250, detail="low")
    assert c.attrs["detail"] == "low" and c.attrs["smooth"] >= terrain.DETAIL["low"][0]


def test_bad_detail():
    with pytest.raises(ValueError, match="detail"):
        terrain.blur_metres((24, 12, 25, 13), "fine")


def test_wider_areas_blur_more():
    assert terrain.blur_metres((20, 10, 30, 20), "medium") > terrain.blur_metres(
        (24, 12, 24.1, 12.1), "medium")


def test_rounding_keeps_rings_closed_and_ends_fixed():
    ring = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], dtype=float)
    out = terrain._chaikin(ring, closed=True)
    assert np.allclose(out[0], out[-1]) and len(out) > len(ring)
    line = np.array([[0, 0], [5, 5], [10, 0]], dtype=float)
    out = terrain._chaikin(line, closed=False)
    assert np.allclose(out[0], line[0]) and np.allclose(out[-1], line[-1])


def test_short_lines_are_dropped():
    assert terrain._clean(np.array([[0, 0], [1, 1]], dtype=float), 10, 0.5) is None


# Phase 6b: satellite and hybrid

@pytest.fixture
def default_imagery():
    saved = dict(kb.IMAGERY)
    yield
    kb.IMAGERY.update(saved)


def test_satellite_is_imagery_only():
    s = kb.style("satellite")
    assert s["sources"]["imagery"]["tiles"][0].startswith("https://tiles.maps.eox.at")
    assert "2016" in s["sources"]["imagery"]["attribution"]
    types = [lyr["type"] for lyr in s["layers"]]
    assert types == ["background", "raster"]


def test_hybrid_adds_roads_borders_and_labels():
    s = kb.style("hybrid")
    ids = [lyr["id"] for lyr in s["layers"]]
    assert ids[:2] == ["background", "imagery"]
    assert {"road-major", "boundary-country", "label-city"} <= set(ids)
    assert "water" not in ids and "park" not in ids


def test_satellite_takes_relief_over_imagery_and_skips_flat_buildings():
    s = kb.style("satellite", relief="soft")
    ids = [lyr["id"] for lyr in s["layers"]]
    assert ids.index("imagery") < ids.index("relief-shade")
    assert "buildings" not in ids
    assert "buildings" in [lyr["id"] for lyr in kb.style("satellite", buildings="3d")["layers"]]


def test_satellite_maps_are_dark_and_skip_the_ground_warning(polygons):
    import warnings

    assert kb.is_dark("satellite") and kb.is_dark("hybrid")
    with warnings.catch_warnings():
        warnings.simplefilter("error", kh.KharitaWarning)
        _ = kh.map(polygons, "fill-[pop] basemap-hybrid ramp-greys scheme-q5").lonboard


def test_imagery_years_and_urls(default_imagery):
    kh.imagery(2024)
    assert "s2cloudless-2024" in kb.style("satellite")["sources"]["imagery"]["tiles"][0]
    kh.imagery("https://example.com/{z}/{x}/{y}.png", attribution="Example")
    src = kb.style("hybrid")["sources"]["imagery"]
    assert src["tiles"] == ["https://example.com/{z}/{x}/{y}.png"]
    assert src["attribution"] == "Example"


@pytest.mark.parametrize("source, kw, match", [
    (2019, {}, "years"),
    ("https://example.com/tiles.png", {"attribution": "x"}, r"\{z\}"),
    ("https://example.com/{z}/{x}/{y}.png", {}, "attribution"),
])
def test_bad_imagery(source, kw, match, default_imagery):
    with pytest.raises(ValueError, match=match):
        kh.imagery(source, **kw)


# Phase 6b: side by side

def test_compare_lays_maps_side_by_side(polygons):
    a = kh.map(polygons, "fill-[pop] basemap-paper")
    b = kh.map(polygons, "fill-[pop] basemap-hybrid")
    box = kh.compare(a, b)
    assert len(box.children) == 2 and "repeat(2" in box.layout.grid_template_columns


def test_compare_links_pan_and_zoom(polygons):
    from dataclasses import replace

    a = kh.map(polygons, "fill-[pop] basemap-paper")
    b = kh.map(polygons, "fill-[pop] basemap-midnight")
    kh.compare(a, b)
    a.lonboard.view_state = replace(a.lonboard.view_state, zoom=9.5, longitude=31.0)
    assert b.lonboard.view_state.zoom == 9.5 and b.lonboard.view_state.longitude == 31.0
    b.lonboard.view_state = replace(b.lonboard.view_state, zoom=4.0)
    assert a.lonboard.view_state.zoom == 4.0


def test_compare_needs_two_maps(polygons):
    with pytest.raises(ValueError, match="two or more"):
        kh.compare(kh.map(polygons, "fill-[pop]"))
    with pytest.raises(TypeError, match="kh.Map"):
        kh.compare(kh.map(polygons, "fill-[pop]"), "not a map")
