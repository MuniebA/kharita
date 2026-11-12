"""Binding styles to tables: expressions, type detection, defaults, safety, heights."""

import warnings

import numpy as np
import pandas as pd
import pytest

import kharita as kh


def test_numeric_column_defaults_to_viridis_quantiles(polygons):
    b = kh.bind(polygons, "fill-[pop]")
    assert b.fill.shape == (10, 4) and b.fill.dtype == np.uint8
    assert b.fill_scale.scheme == "quantiles, 5 classes"
    assert b.fill_scale.colors[0] == "#440154"
    assert b.fill_scale.null_count == 1


def test_text_column_defaults_to_categories(polygons):
    b = kh.bind(polygons, "fill-[region]")
    assert b.fill_scale.kind == "categorical"
    assert b.fill_scale.null_count == 1
    assert set(b.fill_scale.categories) == {"north", "east", "west", "south"}


def test_columns_with_spaces(polygons):
    assert kh.bind(polygons, "fill-[median income]").fill_scale.k == 5


def test_rate_with_division_by_zero_becomes_missing(polygons):
    with pytest.warns(kh.KharitaWarning, match="divide by zero"):
        b = kh.bind(polygons, "fill-[pop/area] scheme-q4")
    # Row 2 divides by zero, row 9 has no population
    assert b.fill_scale.null_count == 2
    assert tuple(b.fill[2]) == b.fill_scale.null_color


def test_factor(polygons):
    a = kh.bind(polygons, "fill-[pop] scheme-e4").fill_scale.edges
    b = kh.bind(polygons, "fill-[pop*2] scheme-e4").fill_scale.edges
    assert b == tuple(2 * x for x in a)


def test_all_null_column_raises(polygons):
    with pytest.raises(kh.BindingError, match="every row is missing"):
        kh.bind(polygons, "fill-[all_null]")


def test_constant_column_warns(polygons):
    with pytest.warns(kh.KharitaWarning, match="one class"):
        assert kh.bind(polygons, "fill-[constant]").fill_scale.k == 1


def test_integer_codes_warn_to_use_categories(polygons):
    with pytest.warns(kh.KharitaWarning, match="scheme-cat"):
        kh.bind(polygons, "fill-[class_id]")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert kh.bind(polygons, "fill-[class_id] scheme-cat").fill_scale.k == 3


def test_numbers_stored_as_text_are_converted(polygons):
    df = polygons.assign(pop_text=polygons["pop"].map(lambda v: None if pd.isna(v) else str(v)))
    with pytest.warns(kh.KharitaWarning, match="numbers as text"):
        b = kh.bind(df, "fill-[pop_text] scheme-q4")
    assert b.fill_scale.kind == "classed"


def test_text_in_a_ratio_raises(polygons):
    with pytest.raises(kh.BindingError, match="must be numeric"):
        kh.bind(polygons, "fill-[region/area]")


def test_numeric_scheme_on_text_raises(polygons):
    with pytest.raises(kh.BindingError, match="use scheme-cat"):
        kh.bind(polygons, "fill-[region] scheme-q5")


def test_categorical_ramp_implies_categories(polygons):
    assert kh.bind(polygons, "fill-[class_id] ramp-set2").fill_scale.kind == "categorical"


def test_booleans_are_categories(polygons):
    df = polygons.assign(big=polygons["pop"] > 500)
    assert kh.bind(df, "fill-[big]").fill_scale.kind == "categorical"


def test_dates_raise(polygons):
    df = polygons.assign(when=pd.date_range("2020-01-01", periods=10))
    with pytest.raises(kh.BindingError, match="dates"):
        kh.bind(df, "fill-[when]")


def test_missing_column_suggests(polygons):
    with pytest.raises(kh.BindingError, match="Did you mean 'pop'"):
        kh.bind(polygons, "fill-[Pop]")


def test_row_order_follows_table_not_index(polygons):
    shuffled = polygons.iloc[[9, 0, 8]].set_index(pd.Index([100, 5, 7]))
    b = kh.bind(shuffled, "fill-[pop] scheme-[1000]")
    assert tuple(b.fill[0]) == b.fill_scale.null_color
    assert b.fill_scale.counts == (1, 1)


def test_user_table_is_not_changed(polygons):
    df = polygons.assign(x=[1.0, np.inf, 3, 4, 5, 6, 7, 8, 9, 10])
    before = df.copy()
    kh.bind(df, "fill-[x] scheme-q3 extrude-[x]")
    pd.testing.assert_frame_equal(df.drop(columns="geometry"), before.drop(columns="geometry"))


def test_spec_object_is_accepted(polygons):
    spec = kh.parse("fill-[pop] scheme-q3")
    assert kh.bind(polygons, spec).fill_scale.k == 3


def test_no_data_binding_means_no_arrays(polygons):
    b = kh.bind(polygons, "fill-indigo-600 stroke-1")
    assert b.fill is None and b.fill_scale is None and b.elevation is None


def test_elevation_scales_to_max(polygons):
    b = kh.bind(polygons, "extrude-[pop] extrude-max-1000")
    assert b.elevation.dtype == np.float32
    assert b.elevation.max() == pytest.approx(1000)
    assert b.elevation[9] == 0


def test_default_height_is_a_tenth_of_extent(polygons):
    b = kh.bind(polygons, "extrude-[pop]")
    # Squares span 10 degrees of longitude at about 15.5 N, roughly 1,070 km
    assert 90_000 < b.elevation_max < 120_000


def test_negative_heights_are_flat(polygons):
    df = polygons.assign(change=[-5, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    with pytest.warns(kh.KharitaWarning, match="negative"):
        b = kh.bind(df, "extrude-[change] extrude-max-100")
    assert b.elevation[0] == 0


def test_not_a_dataframe():
    with pytest.raises(TypeError):
        kh.bind([1, 2, 3], "fill-red-500")


def test_preset_scheme_yields_to_text_data(polygons):
    assert kh.bind(polygons, "preset-choropleth fill-[region]").fill_scale.kind == "categorical"


def test_elevation_top_is_the_largest_value(polygons):
    b = kh.bind(polygons, "extrude-[pop]")
    assert b.elevation_top == pytest.approx(float(polygons["pop"].max()))
