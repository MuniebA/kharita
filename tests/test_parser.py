"""Parser: building the StyleSpec, conflicts, cross-checks, presets, explain, validate."""

import pytest

import kharita as kh
from kharita.expr import Expr
from kharita.registry import USER_PRESETS
from kharita.spec import Scheme


@pytest.fixture(autouse=True)
def clean_presets():
    USER_PRESETS.clear()
    yield
    USER_PRESETS.clear()


def test_full_style():
    s = kh.parse(
        "fill-[pop/area] ramp-ylorrd-r scheme-q7 stroke-1.5 stroke-white/40 null-zinc-200 "
        "highlight-amber-400 opacity-80 tooltip-[name,pop] extrude-[floors*3] extrude-max-500 "
        "basemap-dark legend-tl"
    )
    assert s.fill is None
    assert s.fill_by == Expr("pop", divisor="area")
    assert (s.ramp, s.ramp_reverse) == ("ylorrd", True)
    assert s.scheme == Scheme("quantiles", k=7)
    assert s.stroke_width == 1.5
    assert s.stroke == (255, 255, 255, 102)
    assert s.opacity == 0.8
    assert s.tooltip == ("name", "pop")
    assert s.extrude_by == Expr("floors", factor=3.0)
    assert s.extrude_max == 500
    assert (s.basemap, s.legend, s.legend_position) == ("dark", True, "tl")
    assert s.columns == ("pop", "area", "floors", "name")


def test_order_does_not_matter():
    a = kh.parse("fill-[pop] scheme-q5 stroke-1")
    b = kh.parse("stroke-1 scheme-q5 fill-[pop]")
    assert (a.fill_by, a.scheme, a.stroke_width) == (b.fill_by, b.scheme, b.stroke_width)


def test_empty_style_is_valid():
    assert kh.parse("") == kh.StyleSpec()


@pytest.mark.parametrize(
    "style, position",
    [
        ("fill-red-500 fill-[pop]", 13),
        ("stroke-1 stroke-2", 9),
        ("legend-none legend-tl", 12),
        ("scheme-q5 fill-[x] scheme-cat", 19),
    ],
)
def test_conflicts_point_at_second_token(style, position):
    with pytest.raises(kh.StyleSyntaxError, match="conflicts") as info:
        kh.parse(style)
    assert info.value.position == position


def test_stroke_colour_and_width_do_not_conflict():
    s = kh.parse("stroke-2 stroke-red-500")
    assert s.stroke_width == 2 and s.stroke[3] == 255


@pytest.mark.parametrize(
    "style, phrase",
    [
        ("ramp-viridis", "data-bound fill"),
        ("scheme-q5 fill-red-500", "data-bound fill"),
        ("extrude-max-100", "extrude-\\[column\\]"),
        ("fill-[x] ramp-set2 scheme-q5", "for categories"),
        ("fill-[x] ramp-viridis scheme-div", "diverging ramp"),
    ],
)
def test_cross_checks(style, phrase):
    with pytest.raises(kh.StyleSyntaxError, match=phrase):
        kh.parse(style)


def test_unknown_utility_suggests_fix():
    with pytest.raises(kh.StyleSyntaxError, match="Did you mean 'fill-red-500'"):
        kh.parse("fil-red-500")


def test_utility_without_value():
    with pytest.raises(kh.StyleSyntaxError, match="needs a value"):
        kh.parse("fill")


def test_error_shows_caret_under_token():
    with pytest.raises(kh.StyleSyntaxError) as info:
        kh.parse("stroke-1 fill-indgo-600")
    lines = str(info.value).splitlines()
    assert lines[-2].strip() == "stroke-1 fill-indgo-600"
    assert lines[-1] == "  " + " " * 9 + "^" * len("fill-indgo-600")


def test_preset_expands():
    s = kh.parse("preset-choropleth fill-[pop]")
    assert s.scheme == Scheme("quantiles", k=5)
    assert s.stroke_width == 1


def test_explicit_token_overrides_preset_in_any_order():
    styles = ("preset-choropleth scheme-e4 fill-[pop]", "fill-[pop] scheme-e4 preset-choropleth")
    for style in styles:
        assert kh.parse(style).scheme == Scheme("equal", k=4)


def test_override_clears_preset_values_in_the_group():
    kh.define("solid", "fill-red-500")
    s = kh.parse("preset-solid fill-[pop]")
    assert s.fill is None and s.fill_by == Expr("pop")


def test_preset_error_names_the_preset():
    kh.define("roads", "stroke-2 stroke-slate-400")
    with pytest.raises(kh.StyleSyntaxError, match="from preset-roads") as info:
        kh.parse("preset-roads preset-roads")
    assert info.value.token == "preset-roads"


def test_define_and_nested_presets():
    kh.define("base", "stroke-1 stroke-white")
    kh.define("map", "preset-base scheme-q5")
    s = kh.parse("preset-map fill-[pop]")
    assert s.stroke_width == 1 and s.scheme.k == 5


def test_define_rejects_bad_input():
    with pytest.raises(ValueError, match="built-in"):
        kh.define("choropleth", "stroke-1")
    with pytest.raises(ValueError, match="lowercase"):
        kh.define("My Style", "stroke-1")
    with pytest.raises(kh.StyleSyntaxError):
        kh.define("broken", "fill-indgo-600")
    assert "broken" not in USER_PRESETS


def test_preset_loop_is_caught():
    USER_PRESETS["a"] = "preset-b"
    USER_PRESETS["b"] = "preset-a"
    with pytest.raises(kh.StyleSyntaxError, match="loop"):
        kh.parse("preset-a")


def test_unknown_preset_suggests():
    with pytest.raises(kh.StyleSyntaxError, match="preset-choropleth"):
        kh.parse("preset-choropleh")


def test_validate_checks_columns():
    kh.validate("fill-[pop/area] tooltip-[name]", columns=["pop", "area", "name"])
    with pytest.raises(kh.BindingError, match="case-sensitive") as info:
        kh.validate("fill-[Pop]", columns=["pop"])
    assert info.value.column == "Pop"
    with pytest.raises(kh.BindingError, match="Closest: density"):
        kh.validate("fill-[densty]", columns=["density", "pop"])


def test_explain_lists_sources_and_defaults():
    text = kh.explain("preset-choropleth fill-[pop/area] ramp-ylorrd")
    assert "data: pop / area" in text
    assert "scheme-q5 (from preset-choropleth)" in text
    assert "basemap" in text and "default" in text
    assert repr(text) == str(text)


def test_help_prints(capsys):
    kh.help()
    assert "fill" in capsys.readouterr().out
    kh.help("scheme")
    assert "scheme-q5" in capsys.readouterr().out
    with pytest.raises(ValueError, match="Did you mean 'fill'"):
        kh.help("fil")


def test_utilities_list():
    names = [u.name for u in kh.utilities()]
    assert {"fill", "stroke", "scheme", "preset"} <= set(names)
