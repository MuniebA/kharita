"""kh.Map and kh.map: basemaps, legend placement, notebook widget and HTML export."""

import pytest
from lonboard.basemap import MaplibreBasemap

import kharita as kh
from kharita.maps import OPENFREEMAP_POSITRON


def test_one_liner_builds_a_lonboard_map(polygons):
    m = kh.map(polygons, "preset-choropleth fill-[pop]")
    assert len(m.layers) == 1
    lm = m.lonboard
    assert isinstance(lm.basemap, MaplibreBasemap)
    assert lm.basemap.style == OPENFREEMAP_POSITRON
    assert lm.show_side_panel is False


def test_basemap_tokens(polygons):
    assert kh.map(polygons, "fill-red-500 basemap-none").lonboard.basemap is None
    dark = kh.map(polygons, "fill-[pop] basemap-dark")
    assert dark.dark and "#111827e6" in dark.legend_html()


def test_explicit_basemap_wins_over_style(polygons):
    m = kh.Map(basemap="none").add(polygons, "fill-red-500 basemap-dark")
    assert m.lonboard.basemap is None


def test_bad_basemap_and_legend_options(polygons):
    with pytest.raises(ValueError, match="basemap"):
        kh.Map(basemap="satellite")
    with pytest.raises(ValueError, match="Unknown legend option"):
        kh.map(polygons, "fill-[pop]", legend={"titel": "x"})
    with pytest.raises(ValueError, match="classes"):
        kh.map(polygons, "fill-[pop] scheme-q3", legend={"labels": ["a"]})


def test_legend_hidden_and_absent(polygons):
    assert kh.map(polygons, "fill-[pop] legend-none").legend_html() == ""
    assert kh.map(polygons, "fill-red-500").legend_html() == ""


def test_tooltip_switches_on_lonboard_tooltip(polygons):
    assert kh.map(polygons, "fill-[pop] tooltip-[name]").lonboard.show_tooltip
    assert not kh.map(polygons, "fill-[pop]").lonboard.show_tooltip


def test_extrusion_tilts_the_camera(polygons):
    vs = kh.map(polygons, "fill-[pop] extrude-[pop]").lonboard.view_state
    assert vs.pitch == 45


def test_layers_stack_and_legends_combine(polygons, lines):
    m = kh.Map().add(polygons, "fill-[pop]", legend={"title": "People"})
    m.add(lines, "stroke-[kind] stroke-3", legend={"title": "Roads"})
    assert len(m.layers) == 2
    html = m.legend_html()
    assert html.count("kharita-legend-block") == 2
    assert html.index("People") < html.index("Roads")


def test_widget_overlays_legend(polygons):
    w = kh.map(polygons, "fill-[pop] legend-tl").widget()
    css, grid = w.children
    assert "align-self:start;justify-self:start" in css.value
    assert "kh-overlay" in grid.children[1]._dom_classes


def test_widget_without_legend_is_plain_map(polygons):
    from lonboard import Map as LonboardMap

    assert isinstance(kh.map(polygons, "fill-red-500").widget(), LonboardMap)


def test_export_carries_legend_and_fills_window(polygons, tmp_path):
    m = kh.map(polygons, "fill-[pop] legend-bl", legend={"title": "People"}, height=420)
    path = tmp_path / "map.html"
    page = m.to_html(path, title="Sudan")
    assert path.read_text(encoding="utf-8") == page
    assert "kharita-legend" in page and "People" in page
    assert "bottom:48px;left:12px" in page
    assert page.rstrip().endswith("</html>")
    assert m.lonboard.height in (420, "420px")


def test_empty_map_raises():
    with pytest.raises(ValueError, match="no layers"):
        _ = kh.Map().lonboard
