"""Legend HTML: rows, counts, no-data row, relabelling, escaping, themes."""

import re

import numpy as np
import pytest

import kharita as kh
from kharita.classify import classify_categorical, classify_numeric
from kharita.legend import legend_block, legend_panel, relabel
from kharita.spec import Scheme

NULL = (209, 213, 219, 255)


def numeric_scale(values, scheme):
    return classify_numeric(np.asarray(values, dtype=float), scheme, "viridis", False, "pop",
                            NULL)[1]


def texts(html):
    # Visible text pieces in order
    return [t for t in re.split(r"<[^>]+>", html) if t.strip()]


def test_rows_labels_and_counts():
    scale = numeric_scale([1, 2, 3, 4, 5, 6, np.nan], Scheme("equal", k=3))
    html = legend_block(scale)
    t = texts(html)
    assert t[0] == "pop"
    assert t[1:3] == ["1.0 to 2.7", "2"]
    assert t[-2:] == ["No data", "1"]
    assert html.count("background:") == 4


def test_no_data_row_only_when_needed():
    scale = numeric_scale([1, 2, 3, 4], Scheme("quantiles", k=2))
    assert "No data" not in legend_block(scale)


def test_title_note_and_escaping():
    scale = numeric_scale([1, 2, 3, 4], Scheme("quantiles", k=2))
    html = legend_block(scale, title="<b>Pop</b>", note="Source & credit")
    assert "&lt;b&gt;Pop&lt;/b&gt;" in html
    assert "Source &amp; credit" in html


def test_fmt_relabels_classes():
    scale = numeric_scale([1000, 2000, 3000, 4000], Scheme("equal", k=2))
    assert relabel(scale, "{:,.0f}").labels == ("1,000 to 2,500", "2,500 to 4,000")


def test_fmt_keeps_break_wording():
    scale = numeric_scale([5, 50, 500], Scheme("breaks", k=3, breaks=(10, 100)))
    assert relabel(scale, "{:.1f}").labels == ("under 10.0", "10.0 to 100.0", "100.0 and over")


def test_custom_labels_must_match_class_count():
    scale = numeric_scale([1, 2, 3, 4, 5, 6], Scheme("equal", k=3))
    assert "Low" in legend_block(scale, labels=["Low", "Mid", "High"])
    with pytest.raises(ValueError, match="3 classes"):
        legend_block(scale, labels=["Low", "High"])


def test_categorical_legend_and_fmt_refused():
    _, scale = classify_categorical(np.array(["a", "b", "a"], dtype=object), "set2", False, "kind",
                                    NULL)
    assert texts(legend_block(scale))[1:] == ["a", "2", "b", "1"]
    with pytest.raises(ValueError, match="labels="):
        legend_block(scale, fmt="{:.0f}")


def test_dark_panel_uses_dark_card():
    scale = numeric_scale([1, 2, 3, 4], Scheme("quantiles", k=2))
    assert "#111827e6" in legend_panel([legend_block(scale, dark=True)], dark=True)


def test_legend_helper(polygons):
    html = kh.legend(polygons, "fill-[pop] scheme-q3", title="Population", fmt="{:,.0f}")
    assert "Population" in html and "kharita-legend" in html
    assert kh.legend(polygons, "fill-red-500") == ""


def test_gradient_legend_for_linear_scheme():
    scale = numeric_scale([0, 5, 10, np.nan], Scheme("linear"))
    html = legend_block(scale)
    assert "linear-gradient(to right,#440154" in html
    assert texts(html)[1:4] == ["0", "5", "10"]
    assert "No data" in html


def test_gradient_labels_and_fmt():
    scale = numeric_scale([0, 1000, 2000], Scheme("linear"))
    assert texts(legend_block(scale, fmt="{:,.0f}"))[1:4] == ["0", "1,000", "2,000"]
    assert texts(legend_block(scale, labels=["Low", "High"]))[1:3] == ["Low", "High"]
    with pytest.raises(ValueError, match="ticks"):
        legend_block(scale, labels=["a", "b", "c", "d"])


def test_bar_legend_shows_edges_not_counts():
    scale = numeric_scale([1, 2, 3, 4, 5, 6], Scheme("equal", k=3))
    html = legend_block(scale, style="bar")
    assert html.count("flex:1;background") == 3
    assert texts(html)[1:] == ["1.0", "2.7", "4.3", "6.0"]


def test_bar_legend_refuses_categories_and_bad_styles():
    cats = classify_categorical(np.array(["a", "b"], dtype=object), "set2", False, "c", NULL)[1]
    with pytest.raises(ValueError, match="numeric classes"):
        legend_block(cats, style="bar")
    with pytest.raises(ValueError, match="style"):
        legend_block(cats, style="pie")


def test_height_block_and_frame_card():
    from kharita.legend import THREE_D_NOTE, frame_card, height_block

    html = height_block("pop", 2_500_000, 120_000)
    assert "Height shows" in html and "2,500,000" in html and "120 km" in html
    assert THREE_D_NOTE in html
    assert "850 m" in height_block("h", 40, 850)
    card = frame_card("Sudan <states>", "2008 census", "U.S. Census Bureau")
    assert "Sudan &lt;states&gt;" in card and "Source: U.S. Census Bureau" in card
    assert frame_card() == ""
