"""Phase 5d: hex colours, the ramp catalogue, category colours, palettes, themes, map elements."""

import warnings

import numpy as np
import pytest

import kharita as kh
from kharita import basemaps as kb
from kharita.classify import classify_categorical, ramp_colors
from kharita.legend import compact
from kharita.palette import USER_RAMPS, get_ramp, load_ramps, parse_color
from kharita.spec import THEME_RAMPS

NULL = (209, 213, 219, 255)


@pytest.fixture(autouse=True)
def _clean_registries():
    # Palettes and themes registered by a test never leak into the next
    themes, ramps = dict(kb.THEMES), dict(THEME_RAMPS)
    yield
    USER_RAMPS.clear()
    kb.THEMES.clear()
    kb.THEMES.update(themes)
    THEME_RAMPS.clear()
    THEME_RAMPS.update(ramps)


# Hex colours

@pytest.mark.parametrize("text, expected", [
    ("#0f766e", (15, 118, 110, 255)),
    ("[#0f766e]", (15, 118, 110, 255)),
    ("[#0f766e]/50", (15, 118, 110, 128)),
    ("#fff", (255, 255, 255, 255)),
    ("#0f766e80", (15, 118, 110, 128)),
])
def test_hex_colours(text, expected):
    assert parse_color(text) == expected


def test_bad_hex_explains():
    with pytest.raises(ValueError, match="hex colour"):
        parse_color("#12345")


def test_hex_in_utilities_is_a_colour_not_a_column():
    s = kh.parse("fill-[#0f766e]/70 stroke-[#111] halo-[#fde047]")
    assert s.fill == (15, 118, 110, 179) and s.fill_by is None
    assert s.stroke == (17, 17, 17, 255) and s.halo[:3] == (253, 224, 71)
    assert kh.parse("fill-['#col']").fill_by.column == "#col"


# Ramp catalogue

def test_catalogue_size_and_kinds():
    ramps = load_ramps()
    assert len(ramps) >= 130
    kinds = {r["kind"] for r in ramps.values()}
    assert kinds == {"sequential", "diverging", "categorical"}
    for name in ("batlow", "vik", "thermal", "balance", "sunset", "prism", "spectral", "turbo"):
        assert name in ramps


def test_friendly_names_point_at_real_ramps():
    assert get_ramp("heatwave")["colors"] == get_ramp("rdbu")["colors"][::-1]
    assert get_ramp("ocean")["colors"] == get_ramp("deep")["colors"]
    assert get_ramp("heatwave")["alias"] == "rdbu-r"


def test_family_and_two_family_ramps():
    teal = get_ramp("teal")
    assert teal["kind"] == "sequential" and teal["colors"][0] == "#ccfbf1"
    div = get_ramp("teal-rose")
    assert div["kind"] == "diverging" and len(div["colors"]) % 2 == 1
    assert div["colors"][len(div["colors"]) // 2] == "#f5f5f4"
    assert kh.parse("fill-[pop] ramp-teal-rose-r").ramp_reverse


def test_inline_ramp_blends_for_numbers_and_keeps_colours_for_text(polygons):
    rec = get_ramp("[sky-100,indigo-500,#4c1d95]")
    assert rec["colors"][0] == "#e0f2fe" and rec["colors"][-1] == "#4c1d95"
    assert len(rec["colors"]) == 11
    b = kh.bind(polygons, "fill-[region] ramp-[emerald-600,rose-500,sky-500,amber-400]")
    assert b.fill_scale.colors[:4] == ("#059669", "#f43f5e", "#0ea5e9", "#fbbf24")


def test_unknown_ramp_suggests():
    with pytest.raises(kh.StyleSyntaxError, match="batlow"):
        kh.parse("fill-[pop] ramp-batlo")


def test_short_ramps_blend_instead_of_repeating():
    colours = ramp_colors("sunset", 9)
    assert len(set(colours)) == 9


@pytest.mark.parametrize("name", sorted(load_ramps()))
def test_every_ramp_can_be_checked(name):
    out = kh.check_ramp(name)
    assert out["kind"] in ("sequential", "diverging", "categorical")
    assert isinstance(out["colour_blind_safe"], bool)


def test_checks_agree_with_known_ramps():
    assert kh.check_ramp("viridis")["lightness"] == "even"
    assert kh.check_ramp("viridis")["colour_blind_safe"]
    assert kh.check_ramp("turbo")["lightness"] == "not monotonic"
    assert not kh.check_ramp("set2")["colour_blind_safe"]


# Category colours, order and standard palettes

def test_ipc_maps_phases_to_fixed_colours():
    out, scale = classify_categorical(np.array([3, 1, 5, 3, 7, np.nan], dtype=object), "ipc",
                                      False, "phase", NULL)
    assert scale.labels == ("1 Minimal", "3 Crisis", "5 Famine", "other")
    assert tuple(out[0][:3]) == (230, 120, 0)
    assert tuple(out[2][:3]) == (100, 0, 0)
    assert tuple(out[5]) == NULL


def test_worldcover_codes():
    _, scale = classify_categorical(np.array([10, 80, 10]), "worldcover", False, "lc", NULL)
    assert scale.labels == ("Tree cover", "Permanent water bodies")
    assert scale.colors == ("#006400", "#0064c8")


def test_fixed_colours_and_order(polygons):
    b = kh.bind(polygons, "fill-[region] ramp-set2", colors={"west": "rose-500"},
                order=["south", "west"])
    s = b.fill_scale
    assert s.categories[:2] == ("south", "west")
    assert s.colors[1] == "#f43f5e"


def test_colors_need_categories(polygons):
    with pytest.raises(kh.BindingError, match="scheme-cat"):
        kh.bind(polygons, "fill-[pop] scheme-q4", colors={"1": "red-500"})


def test_unknown_category_in_colors_warns(polygons):
    with pytest.warns(kh.KharitaWarning, match="no value 'nowhere'"):
        kh.bind(polygons, "fill-[region]", colors={"nowhere": "red-500"})


def test_map_passes_colors_through(polygons):
    m = kh.map(polygons, "fill-[region]", colors={"north": "#000000"})
    assert "#000000" in m.bounds[0].fill_scale.colors


# Your own palettes and themes

def test_palette_registers_and_works(polygons):
    kh.palette("brand", ["teal-700", "amber-400", "rose-600", "sky-600"], kind="categorical")
    b = kh.bind(polygons, "fill-[region] ramp-brand")
    assert b.fill_scale.colors == ("#0f766e", "#fbbf24", "#e11d48", "#0284c7")
    kh.palette("glow", ["#000000", "fuchsia-400"])
    assert get_ramp("glow")["kind"] == "sequential" and len(get_ramp("glow")["colors"]) == 11


def test_palette_refuses_builtin_names():
    with pytest.raises(ValueError, match="built-in"):
        kh.palette("viridis", ["red-500", "blue-500"])


def test_theme_registers_with_elements_and_ramp(polygons):
    kh.theme("desert", base="paper", land="[#f3e5c8]", water="sky-200", ramp="lajolla")
    assert "desert" in kb.basemap_names()
    m = kh.map(polygons, "fill-[pop] theme-desert")
    assert m.basemap_name == "desert" and not m.dark
    assert m.bounds[0].fill_scale.colors[0] == get_ramp("lajolla")["colors"][0]
    style = kb.style("desert")
    assert style["layers"][0]["paint"]["background-color"] == "#f3e5c8"


def test_dark_theme_is_detected():
    kh.theme("deepsea", base="midnight", land="slate-950")
    assert kb.is_dark("deepsea")


def test_theme_refuses_builtin_names():
    with pytest.raises(ValueError, match="built-in"):
        kh.theme("paper", land="red-100")


# Map elements

def test_element_utilities_parse():
    s = kh.parse("water-sky-200 roads-none land-[#f5f5f4] buildings-amber-100 labels-slate-700")
    assert s.elements["water"][:3] == (186, 230, 253)
    assert s.elements["roads"] == "none"
    assert s.elements["buildings"][:3] == (254, 243, 199)
    assert s.buildings is None
    with pytest.raises(kh.StyleSyntaxError, match="cannot be hidden"):
        kh.parse("land-none")
    with pytest.raises(kh.StyleSyntaxError, match="conflicts"):
        kh.parse("water-sky-200 water-sky-300")


def test_elements_change_only_their_layers():
    plain = kb.style("paper")
    styled = kb.style("paper", elements={"water": (186, 230, 253, 255), "roads": "none"})
    ids = [lyr["id"] for lyr in styled["layers"]]
    assert "road-major" not in ids and "road-minor" in ids
    water = next(lyr for lyr in styled["layers"] if lyr["id"] == "water")
    assert water["paint"]["fill-color"] == "#bae6fd"
    assert len(plain["layers"]) == len(styled["layers"]) + 1


def test_land_colour_also_sets_label_halo():
    s = kb.style("paper", elements={"land": (245, 245, 244, 255)})
    halo = next(lyr for lyr in s["layers"] if lyr["id"] == "label-city")["paint"]
    assert halo["text-halo-color"] == "#f5f5f4"


def test_elements_need_a_kharita_basemap(polygons):
    with pytest.raises(kh.StyleSyntaxError, match="not one"):
        kh.parse("water-sky-200 basemap-light")
    with pytest.raises(ValueError, match="kharita basemap"):
        kh.Map(basemap="dark").add(polygons, "fill-[pop] roads-none")


def test_elements_reach_the_map(polygons):
    m = kh.map(polygons, "fill-[pop] basemap-muted water-sky-200")
    assert m.elements["water"][:3] == (186, 230, 253)
    assert m.lonboard.basemap.style.startswith("data:")


def test_relief_steps_are_flat_bands():
    s = kb.style("paper", relief="steps")
    paint = next(lyr for lyr in s["layers"] if lyr["id"] == "relief-tint")["paint"]
    stops = paint["color-relief-color"][3:]
    heights, colours = stops[0::2], stops[1::2]
    assert colours[0] == colours[1] and heights[1] == kb.TINT_STOPS[1] - 0.01


def test_ground_warning_when_a_class_matches_the_land(polygons):
    with pytest.warns(kh.KharitaWarning, match="ground"):
        _ = kh.map(polygons, "fill-[pop] basemap-mono ramp-greys scheme-q5").lonboard
    with warnings.catch_warnings():
        warnings.simplefilter("error", kh.KharitaWarning)
        _ = kh.map(polygons, "fill-[pop] scheme-q5 basemap-mono ramp-viridis").lonboard


# Browsers

def test_ramp_gallery_filters_and_renders():
    every = kh.ramps(checks=False)
    assert len(every) >= 150 and "teal" in every.names
    div = kh.ramps(kind="diverging", checks=False)
    assert all(get_ramp(n)["kind"] == "diverging" for n in div.names)
    assert kh.ramps(search="heat", checks=False).names == ["heatwave"]
    html = kh.ramps(source="crameri")._repr_html_()
    assert "batlow" in html and "linear-gradient" in html


def test_colour_gallery():
    g = kh.colors()
    assert len(g) == 22 and "teal" in g.names
    assert "#14b8a6" in kh.colors("teal")._repr_html_()
    page = kh.colors("teal").to_html()
    assert page.startswith("<!doctype html>")
    with pytest.raises(ValueError, match="family"):
        kh.colors("tael")


def test_compact_numbers():
    assert [compact(x) for x in (553515, 1271390, 5274321, 999, 12.5)] == [
        "554K", "1.27M", "5.27M", "999", "12.5"]


def test_diverging_middle_does_not_trigger_the_ground_warning(polygons):
    with warnings.catch_warnings():
        warnings.simplefilter("error", kh.KharitaWarning)
        _ = kh.map(polygons, "fill-[pop] basemap-paper ramp-teal-rose scheme-div-[500]").lonboard
