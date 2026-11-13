"""Themed basemap styles: structure, options and data URLs."""

import base64
import json
import re
from urllib.parse import unquote

import pytest

from kharita import basemaps as kb

HEX = re.compile(r"^#[0-9a-f]{6}$")


def _symbols(s: dict) -> list[dict]:
    return [layer for layer in s["layers"] if layer["type"] == "symbol"]


def _luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@pytest.mark.parametrize("name", list(kb.THEMES))
def test_every_theme_builds_a_valid_shape(name):
    s = kb.style(name)
    assert s["version"] == 8
    assert s["sources"]["openmaptiles"]["url"] == kb.OPENFREEMAP_TILES
    assert s["layers"][0]["type"] == "background"
    ids = [layer["id"] for layer in s["layers"]]
    assert len(ids) == len(set(ids))
    for layer in s["layers"]:
        assert layer.get("source") in (None, "openmaptiles", "terrain", "imagery")


@pytest.mark.parametrize("name", list(kb.THEMES))
def test_theme_colours_are_hex(name):
    t = kb.THEMES[name]
    for field in ("background", "water", "water_line", "land", "boundary", "boundary_minor",
                  "road_major", "road_minor", "label", "halo", "shadow", "highlight"):
        assert HEX.match(getattr(t, field)), field


@pytest.mark.parametrize("name", list(kb.THEMES))
def test_dark_flag_matches_background(name):
    t = kb.THEMES[name]
    assert t.dark == (_luminance(t.background) < 0.5)


def test_labels_add_glyphs_and_symbol_layers():
    s = kb.style("paper")
    assert s["glyphs"] == kb.OPENFREEMAP_GLYPHS
    labels = _symbols(s)
    assert labels[0]["id"] == kb.FIRST_LABEL
    # Labels are drawn last so they sit above everything else
    assert s["layers"][-len(labels):] == labels


def test_labels_can_be_turned_off():
    s = kb.style("paper", labels=False)
    assert "glyphs" not in s and not _symbols(s)


def test_muted_has_no_labels_unless_asked():
    assert not _symbols(kb.style("muted"))
    assert _symbols(kb.style("muted", labels=True))


def test_hillshade_adds_terrarium_source_under_everything():
    s = kb.style("paper", hillshade=True)
    dem = s["sources"]["terrain"]
    assert dem["type"] == "raster-dem" and dem["encoding"] == "terrarium"
    assert s["layers"][1]["type"] == "hillshade"
    assert "terrain" not in kb.style("paper")["sources"]


def test_unknown_theme_suggests():
    with pytest.raises(ValueError, match="Did you mean 'paper'"):
        kb.style("papper")


@pytest.mark.parametrize("encoding", ["base64", "percent"])
def test_data_url_round_trips(encoding):
    s = kb.style("neon", hillshade=True)
    url = kb.data_url(s, encoding=encoding)
    head, body = url.split(",", 1)
    assert head.startswith("data:application/json")
    text = base64.b64decode(body).decode() if encoding == "base64" else unquote(body)
    assert json.loads(text) == s


def test_bad_encoding_raises():
    with pytest.raises(ValueError, match="encoding"):
        kb.data_url({}, encoding="hex")


def test_basemap_accepts_data_urls_and_objects():
    bm = kb.basemap("midnight", mode="interleaved")
    assert bm.style.startswith("data:application/json;base64,")
    assert bm.mode == "interleaved"
    assert kb.basemap("paper", encoding="object").style["version"] == 8


def test_theme_basemap_works_in_a_lonboard_map(polygons):
    from lonboard import Map

    import kharita as kh

    m = Map(kh.layer(polygons, "fill-[pop]"), basemap=kb.basemap("neon", hillshade=True))
    assert m.basemap.style.startswith("data:")
    assert "data:application/json;base64," in m.to_html()


def _ids(s: dict) -> list[str]:
    return [layer["id"] for layer in s["layers"]]


def test_relief_designs():
    soft = kb.style("paper", relief="soft")
    assert _ids(soft)[1] == "relief-shade"
    sharp = kb.style("midnight", relief="sharp")
    paint = sharp["layers"][1]["paint"]
    assert paint["hillshade-method"] == "multidirectional"
    assert len(paint["hillshade-illumination-direction"]) == len(paint["hillshade-shadow-color"])
    tint = kb.style("neon", relief="tint")
    assert _ids(tint)[1:3] == ["relief-tint", "relief-shade"]
    stops = tint["layers"][1]["paint"]["color-relief-color"][3:]
    assert stops[0::2] == list(kb.TINT_STOPS)
    with pytest.raises(ValueError, match="relief"):
        kb.style("paper", relief="3d")


@pytest.mark.parametrize("name", list(kb.THEMES))
def test_tints_match_stops(name):
    assert len(kb.THEMES[name].tint) == len(kb.TINT_STOPS)


def test_terrain_is_paper_with_tint():
    s = kb.style("terrain")
    assert "relief-tint" in _ids(s) and s["layers"][0]["paint"]["background-color"] == "#f4efe6"
    assert "relief-shade" in _ids(kb.style("terrain", relief="sharp"))


def test_buildings_flat_3d_none():
    flat = next(x for x in kb.style("paper")["layers"] if x["id"] == "buildings")
    assert flat["type"] == "fill" and flat["minzoom"] == 13
    tall = next(x for x in kb.style("midnight", buildings="3d")["layers"] if x["id"] == "buildings")
    assert tall["type"] == "fill-extrusion"
    assert "buildings" not in _ids(kb.style("paper", buildings="none"))
    with pytest.raises(ValueError, match="buildings"):
        kb.style("paper", buildings="tall")


def test_buildings_sit_under_labels():
    ids = _ids(kb.style("paper", buildings="3d"))
    assert ids.index("buildings") < ids.index(kb.FIRST_LABEL)


def test_basemap_name_tables():
    assert set(kb.HOSTED) == {"light", "dark", "fiord"}
    assert {"midnight", "neon", "dark", "fiord", "satellite", "hybrid"} == set(kb.DARK_BASEMAPS)
    assert kb.resolve("terrain") == ("paper", "tint") and kb.resolve("mono") == ("mono", None)
