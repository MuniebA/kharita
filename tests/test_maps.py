"""kh.Map and kh.map: basemaps, legend placement, notebook widget and HTML export."""

import pytest
from lonboard.basemap import MaplibreBasemap

import kharita as kh
from kharita import basemaps as kb
from kharita.basemaps import HOSTED


def test_one_liner_builds_a_lonboard_map(polygons):
    m = kh.map(polygons, "preset-choropleth fill-[pop]")
    assert len(m.layers) == 1
    lm = m.lonboard
    assert isinstance(lm.basemap, MaplibreBasemap)
    assert lm.basemap.style == HOSTED["light"]
    assert lm.show_side_panel is False


def test_basemap_tokens(polygons):
    assert kh.map(polygons, "fill-red-500 basemap-none").lonboard.basemap is None
    dark = kh.map(polygons, "fill-[pop] basemap-dark")
    assert dark.dark and "#111827e6" in dark.legend_html()
    # Keyless OpenFreeMap dark replaced CARTO Dark Matter after the design spike
    assert dark.lonboard.basemap.style == HOSTED["dark"]


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


def test_bottom_right_legend_clears_corner_button(polygons):
    # Lonboard's bottom-right button is about 60px tall with its margin
    m = kh.map(polygons, "fill-[pop]")
    assert "bottom:72px;right:12px" in m.to_html()
    assert "72px" in m.widget().children[0].value


def test_theme_sets_basemap_legend_and_ramp(polygons):
    m = kh.map(polygons, "fill-[pop] theme-midnight")
    assert m.basemap_name == "midnight" and m.dark
    assert m.lonboard.basemap.style.startswith("data:application/json;base64,")
    assert m.bounds[0].fill_scale.colors[0] == "#440154"
    paper = kh.map(polygons, "fill-[pop] theme-paper")
    assert not paper.dark and paper.bounds[0].fill_scale.colors[0] == "#ffffcc"
    # A typed ramp still wins over the theme's
    typed = kh.map(polygons, "fill-[pop] theme-paper ramp-blues")
    assert typed.bounds[0].fill_scale.colors[0] != "#ffffcc"


def test_themed_layers_sit_under_labels(polygons):
    m = kh.map(polygons, "fill-[pop] basemap-paper")
    assert m.lonboard.basemap.mode == "interleaved"
    assert all(x.before_id == kb.FIRST_LABEL for x in m.lonboard.layers)
    hidden = kh.map(polygons, "fill-[pop] basemap-paper labels-none")
    assert hidden.lonboard.basemap.mode == "overlaid"
    assert all(x.before_id is None for x in hidden.lonboard.layers)
    hosted = kh.map(polygons, "fill-[pop] basemap-light")
    assert all(x.before_id is None for x in hosted.lonboard.layers)


def test_relief_and_buildings_pick_paper_by_default(polygons):
    m = kh.map(polygons, "fill-[pop] relief-tint")
    assert m.basemap_name == "paper"
    style = m.lonboard.basemap.style
    assert style.startswith("data:")
    tall = kh.map(polygons, "fill-[pop] basemap-midnight buildings-3d")
    assert tall.lonboard.view_state.pitch == 45


def test_relief_on_a_hosted_basemap_raises(polygons):
    with pytest.raises(kh.StyleSyntaxError, match="not one"):
        kh.parse("relief-soft basemap-light")
    with pytest.raises(ValueError, match="kharita basemap"):
        kh.Map(basemap="dark").add(polygons, "fill-[pop] buildings-3d")


def test_glow_sets_map_parameters_and_warns_on_light(polygons):
    m = kh.map(polygons, "fill-[pop] basemap-neon glow")
    assert m.lonboard.parameters["blendColorDstFactor"] == "one"
    with pytest.warns(kh.KharitaWarning, match="glow"):
        _ = kh.map(polygons, "fill-[pop] glow").lonboard
    assert kh.map(polygons, "fill-[pop]").lonboard.parameters is None


def test_first_layer_settings_win(polygons):
    m = kh.Map().add(polygons, "fill-gray-200 theme-neon").add(polygons, "fill-[pop] theme-paper")
    assert m.theme == "neon"


def test_terrain_export(polygons):
    page = kh.map(polygons, "fill-[pop] basemap-terrain").to_html()
    assert "data:application/json;base64," in page and "kharita-legend" in page
