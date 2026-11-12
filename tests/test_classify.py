"""Classification on raw arrays: schemes, ties, labels, colours."""

import numpy as np
import pytest

from kharita.classify import (
    OTHER_HEX,
    classify_categorical,
    classify_numeric,
    fmt_number,
    ramp_colors,
)
from kharita.errors import KharitaWarning
from kharita.palette import hex_to_rgba
from kharita.spec import Scheme

NULL = (209, 213, 219, 255)


def numeric(values, scheme, ramp="viridis", reverse=False):
    return classify_numeric(np.asarray(values, dtype=float), scheme, ramp, reverse, "v", NULL)


def test_quantiles_split_evenly():
    out, scale = numeric(range(1, 11), Scheme("quantiles", k=5))
    assert scale.counts == (2, 2, 2, 2, 2)
    assert scale.k == 5
    assert out.shape == (10, 4) and out.dtype == np.uint8


def test_quantile_ties_reduce_classes_with_warning():
    with pytest.warns(KharitaWarning, match="only 2 quantile classes"):
        _, scale = numeric([1, 1, 1, 1, 1, 1, 1, 1, 2, 3], Scheme("quantiles", k=5))
    assert scale.k == 2
    assert sum(scale.counts) == 10


def test_equal_interval_edges_and_empty_classes():
    _, scale = numeric([0, 0, 0, 100], Scheme("equal", k=4))
    assert scale.edges == (0, 25, 50, 75, 100)
    assert scale.counts == (3, 0, 0, 1)


def test_equal_interval_warns_on_few_values():
    with pytest.warns(KharitaWarning, match="distinct values"):
        numeric([1, 2, 1, 2], Scheme("equal", k=5))


def test_explicit_breaks_labels_and_counts():
    _, scale = numeric([5, 10, 49, 50, 500], Scheme("breaks", k=4, breaks=(10, 50, 100)))
    assert scale.labels == ("under 10", "10 to 50", "50 to 100", "100 and over")
    assert scale.counts == (1, 2, 1, 1)


def test_breaks_keep_typed_decimals():
    _, scale = numeric([1, 2, 3], Scheme("breaks", k=2, breaks=(2.5,)))
    assert scale.labels == ("under 2.5", "2.5 and over")


def test_diverging_is_symmetric_and_neutral_in_middle():
    _, scale = numeric([-10, -5, 0, 5, 20], Scheme("diverging", center=0.0), ramp="rdbu")
    assert scale.k == 7
    assert scale.edges[0] == -20 and scale.edges[-1] == 20
    middle = scale.colors[3]
    assert middle == ramp_colors("rdbu", 11)[5]


def test_diverging_warns_when_one_sided():
    with pytest.warns(KharitaWarning, match="one side"):
        numeric([1, 2, 3], Scheme("diverging", center=0.0), ramp="rdbu")


def test_constant_values_give_one_class():
    with pytest.warns(KharitaWarning, match="one class"):
        out, scale = numeric([7, 7, 7], Scheme("quantiles", k=5))
    assert scale.k == 1 and scale.counts == (3,)
    assert len({tuple(r) for r in out}) == 1


def test_nan_gets_null_colour_and_count():
    out, scale = numeric([1, 2, np.nan, 3, 4, 5], Scheme("quantiles", k=3))
    assert tuple(out[2]) == NULL
    assert scale.null_count == 1
    assert sum(scale.counts) == 5


def test_colours_match_scale():
    out, scale = numeric(range(10), Scheme("quantiles", k=5))
    lut = {tuple(hex_to_rgba(c)) for c in scale.colors}
    assert {tuple(r) for r in out} <= lut


def test_reverse_flips_ramp():
    assert ramp_colors("viridis", 5, reverse=True) == ramp_colors("viridis", 5)[::-1]


def test_labels_choose_sensible_decimals():
    _, small = numeric([0.01, 0.02, 0.03, 0.04, 0.05], Scheme("equal", k=4))
    _, big = numeric([1000, 25000, 70000, 1_000_000], Scheme("quantiles", k=3))
    _, ints = numeric([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], Scheme("equal", k=3))
    assert small.labels[0] == "0.010 to 0.020"
    assert "," in big.labels[-1] and "." not in big.labels[-1]
    assert ints.labels[0] == "1 to 4"


def test_fmt_number_has_no_negative_zero():
    assert fmt_number(-0.0001, 1) == "0.0"


def test_categorical_order_counts_and_nulls():
    out, scale = classify_categorical(
        np.array(["b", "a", "b", None, "c", "b", "a"], dtype=object), "set2", False, "v", NULL
    )
    assert scale.categories == ("b", "a", "c")
    assert scale.counts == (3, 2, 1)
    assert scale.null_count == 1
    assert tuple(out[3]) == NULL
    assert tuple(out[0]) == hex_to_rgba(scale.colors[0])


def test_categorical_ties_sort_by_name():
    _, scale = classify_categorical(np.array(["z", "y", "x"], dtype=object), "set2", False, "v",
                                    NULL)
    assert scale.categories == ("x", "y", "z")


def test_too_many_categories_become_other():
    values = np.array([f"c{i:02d}" for i in range(20)] + ["c00"], dtype=object)
    with pytest.warns(KharitaWarning, match="grouped as 'other'"):
        out, scale = classify_categorical(values, "set2", False, "v", NULL)
    assert scale.labels[-1] == "other"
    assert scale.k == 8
    assert sum(scale.counts) == 21
    assert scale.colors[-1] == OTHER_HEX


def test_numeric_categories_label_cleanly():
    _, scale = classify_categorical(np.array([1.0, 2.0, 2.0]), "set2", False, "v", NULL)
    assert scale.labels == ("2", "1")


def test_million_rows_is_fast():
    import time

    values = np.random.default_rng(0).lognormal(size=1_000_000)
    t0 = time.perf_counter()
    out, _ = numeric(values, Scheme("quantiles", k=5))
    assert time.perf_counter() - t0 < 3
    assert out.shape == (1_000_000, 4)
