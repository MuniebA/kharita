"""Phase 0 checks: package imports, bundled data and fixtures are sound."""

import re

import numpy as np

import kharita
from kharita.errors import BindingError, KharitaError, StyleSyntaxError
from kharita.palette import FAMILIES, SHADES, load_colors, load_ramps

HEX = re.compile(r"^#[0-9a-f]{6}$")


def test_version():
    assert kharita.__version__ == "0.0.3"


def test_errors_share_a_base():
    assert issubclass(StyleSyntaxError, KharitaError)
    assert issubclass(BindingError, KharitaError)
    err = StyleSyntaxError("bad token", token="fil-red-500", position=0)
    assert err.token == "fil-red-500"


def test_palette_has_every_family_and_shade():
    colors = load_colors()
    for family in FAMILIES:
        assert set(colors[family]) == set(SHADES), family
        assert all(HEX.match(v) for v in colors[family].values()), family
    assert colors["white"] == "#fff"


def test_known_palette_value():
    assert load_colors()["indigo"]["600"] == "#4f46e5"


def test_ramps_are_well_formed():
    ramps = load_ramps()
    assert {"viridis", "ylorrd", "rdbu", "set2"} <= set(ramps)
    for name, ramp in ramps.items():
        assert ramp["kind"] in {"sequential", "diverging", "categorical"}, name
        assert all(HEX.match(c) for c in ramp["colors"]), name
        if ramp["kind"] != "categorical":
            assert len(ramp["colors"]) == 11, name


def test_polygon_fixture_has_the_awkward_cases(polygons):
    assert len(polygons) == 10
    assert polygons["pop"].isna().sum() == 1
    assert polygons["all_null"].isna().all()
    assert polygons["constant"].nunique() == 1
    assert (polygons["area"] == 0).any()
    assert polygons["region"].isna().sum() == 1


def test_mixed_fixture(mixed):
    types = set(mixed.geometry.dropna().geom_type)
    assert types == {"Polygon", "Point"}
    assert mixed.geometry.isna().sum() == 1


def test_no_crs_fixture(no_crs):
    assert no_crs.crs is None


def test_lonboard_draws_the_fixture(polygons):
    from lonboard import PolygonLayer

    colors = np.tile(np.array([79, 70, 229, 255], dtype=np.uint8), (len(polygons), 1))
    layer = PolygonLayer.from_geopandas(polygons[["geometry"]], get_fill_color=colors)
    assert layer is not None
