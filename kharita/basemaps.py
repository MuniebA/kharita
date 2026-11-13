"""Basemaps: hosted keyless styles, and kharita themes built as MapLibre style JSON."""

import base64
import json
from dataclasses import dataclass, replace
from difflib import get_close_matches
from urllib.parse import quote

OPENFREEMAP_TILES = "https://tiles.openfreemap.org/planet"
OPENFREEMAP_GLYPHS = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf"
TERRARIUM_TILES = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
FONT = ["Noto Sans Regular"]
FIRST_LABEL = "label-road"
DATA_LABEL = "kh-label"
VECTOR_ATTRIBUTION = (
    '<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> '
    '<a href="https://www.openmaptiles.org/" target="_blank">&copy; OpenMapTiles</a> '
    'Data from <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>'
)
TERRAIN_ATTRIBUTION = (
    'Elevation: <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank">'
    "Mapzen Terrain Tiles</a>"
)
EOX_TILES = "https://tiles.maps.eox.at/wmts/1.0.0/{layer}/default/g/{{z}}/{{y}}/{{x}}.jpg"
EOX_ATTRIBUTION = ('Sentinel-2 cloudless by <a href="https://s2maps.eu" target="_blank">EOX IT '
                   "Services GmbH</a> (Contains modified Copernicus Sentinel data {year})")
# Sentinel-2 cloudless years; 2016 is CC BY-SA 4.0, later years are for non-commercial use only
EOX_YEARS = {2016: "s2cloudless_3857", 2017: "s2cloudless-2017_3857",
             2018: "s2cloudless-2018_3857", 2020: "s2cloudless-2020_3857",
             2021: "s2cloudless-2021_3857", 2022: "s2cloudless-2022_3857",
             2023: "s2cloudless-2023_3857", 2024: "s2cloudless-2024_3857"}
MAJOR_ROADS = ["motorway", "trunk", "primary", "secondary"]
MINOR_ROADS = ["tertiary", "minor", "service"]

# Hosted styles kharita cannot recolour; dark and fiord replace CARTO Dark Matter
HOSTED = {
    "light": "https://tiles.openfreemap.org/styles/positron",
    "dark": "https://tiles.openfreemap.org/styles/dark",
    "fiord": "https://tiles.openfreemap.org/styles/fiord",
}
RELIEFS = ("soft", "sharp", "tint", "steps")
BUILDINGS = ("flat", "3d", "none")
# Elevation in metres for the hypsometric tint stops
TINT_STOPS = (0, 300, 600, 1000, 1500, 2200, 3000)


@dataclass(frozen=True)
class Theme:
    name: str
    dark: bool
    background: str
    water: str
    water_line: str
    land: str
    boundary: str
    boundary_minor: str
    road_major: str
    road_minor: str
    label: str
    halo: str
    shadow: str
    highlight: str
    building: str
    tint: tuple[str, ...]
    labels: bool = True
    imagery: bool = False


THEMES = {
    "paper": Theme("paper", False, "#f4efe6", "#c9d8df", "#b3c7d0", "#ebe5d8", "#9a8f80",
                   "#c8bfb1", "#e3dccf", "#ece6da", "#5b5246", "#f4efe6", "#5c4a32", "#ffffff",
                   "#e6ddcc", ("#eef0df", "#e6e3c7", "#ddd3ae", "#d2c099", "#c4a985",
                               "#b0947a", "#e9e4dc")),
    "midnight": Theme("midnight", True, "#0b1020", "#070b16", "#111a33", "#0e1428", "#3b4566",
                      "#222a44", "#1c2440", "#151c33", "#8b95b3", "#0b1020", "#000000",
                      "#5a6a9c", "#18213d", ("#0b1020", "#0f1730", "#141f42", "#1a2853",
                                             "#223267", "#2e3f7c", "#3f5294")),
    "mono": Theme("mono", False, "#f5f5f5", "#e0e0e0", "#d0d0d0", "#eeeeee", "#9e9e9e",
                  "#d4d4d4", "#ffffff", "#fafafa", "#616161", "#f5f5f5", "#424242", "#ffffff",
                  "#e4e4e4", ("#f5f5f5", "#ececec", "#e0e0e0", "#d2d2d2", "#c2c2c2", "#b0b0b0",
                              "#9a9a9a")),
    "neon": Theme("neon", True, "#14062b", "#0a0218", "#2a0f52", "#1a0a36", "#6d28d9",
                  "#3b1670", "#2a0f52", "#1f0b40", "#c4b5fd", "#14062b", "#000000", "#8b5cf6",
                  "#241048", ("#14062b", "#1c0a3d", "#26104f", "#331566", "#451c80",
                              "#5b249c", "#7c3aed")),
    "topo": Theme("topo", False, "#fdfcf8", "#cde4ef", "#6aa6c8", "#f8e6b0", "#8a8378",
                  "#bdb6aa", "#d4442a", "#eab3a3", "#4a3b2c", "#fdfcf8", "#6b5843", "#ffffff",
                  "#ebe5d9", ("#fdfcf8", "#f6f0dc", "#eee2bf", "#e4d0a2", "#d6ba86", "#c4a170",
                              "#f1ece4")),
    "muted": Theme("muted", False, "#f1f1ef", "#dde3e6", "#cfd8dc", "#ecebe7", "#b9b9b4",
                   "#d9d8d3", "#e6e5e1", "#ebeae6", "#7a7a75", "#f1f1ef", "#55554f", "#ffffff",
                   "#e3e2dd", ("#f1f1ef", "#eae9e3", "#e1dfd6", "#d6d3c8", "#c9c5b8",
                               "#bab5a8", "#e8e7e3"), labels=False),
    "satellite": Theme("satellite", True, "#10140f", "#10140f", "#7dd3fc", "#10140f", "#ffffff",
                       "#d4d4d4", "#fde68a", "#ffffff", "#ffffff", "#111111", "#000000",
                       "#ffffff", "#e5e5e5", ("#fdfcf8", "#f6f0dc", "#eee2bf", "#e4d0a2",
                                              "#d6ba86", "#c4a170", "#f1ece4"),
                       labels=False, imagery=True),
}
# Satellite imagery with roads, borders and labels drawn over it
THEMES["hybrid"] = replace(THEMES["satellite"], name="hybrid", labels=True)
# The imagery satellite and hybrid draw; kh.imagery changes it
IMAGERY = {"tiles": EOX_TILES.format(layer=EOX_YEARS[2016]),
           "attribution": EOX_ATTRIBUTION.format(year=2016), "maxzoom": 14}
# Names that pick a theme plus a relief design
ALIASES = {"terrain": ("paper", "tint")}
BASEMAP_NAMES = (*HOSTED, *THEMES, *ALIASES, "none")
DARK_BASEMAPS = frozenset({"dark", "fiord", *(n for n, t in THEMES.items() if t.dark)})
# Which Theme field each element utility recolours, and which layers -none removes
ELEMENT_FIELDS = {
    "land": "background", "water": "water", "rivers": "water_line", "parks": "land",
    "roads": "road_major", "streets": "road_minor", "buildings": "building",
    "borders": "boundary", "admin": "boundary_minor", "labels": "label",
}
ELEMENT_LAYERS = {
    "rivers": ("waterway",), "parks": ("park", "landcover"), "roads": ("road-major",),
    "streets": ("road-minor",), "borders": ("boundary-country",), "admin": ("boundary-state",),
}


def basemap_names() -> tuple[str, ...]:
    """Every basemap name, including themes added with kh.theme."""
    return (*HOSTED, *THEMES, *ALIASES, "none")


def is_dark(name: str) -> bool:
    """True for basemaps with a dark ground, built in or added with kh.theme."""
    theme, _ = resolve(name)
    return name in ("dark", "fiord") or (theme in THEMES and THEMES[theme].dark)


def css_color(c) -> str:
    """An RGBA tuple as a MapLibre colour string."""
    r, g, b, a = c
    return f"#{r:02x}{g:02x}{b:02x}" if a == 255 else f"rgba({r},{g},{b},{a / 255:.3f})"


def apply_elements(t: Theme, elements: dict) -> Theme:
    """The theme with element colours replaced; hidden elements are dropped in style()."""
    changes = {ELEMENT_FIELDS[k]: css_color(v) for k, v in elements.items() if v != "none"}
    if "land" in elements and elements["land"] != "none" and t.halo == t.background:
        # Label halos follow the ground so text stays crisp on the new colour
        changes["halo"] = changes["background"]
    return replace(t, **changes)


def get_theme(name: str) -> Theme:
    """A theme by name, with a suggestion on a typo."""
    if name in THEMES:
        return THEMES[name]
    close = get_close_matches(name, THEMES, n=1)
    hint = f" Did you mean '{close[0]}'?" if close else ""
    raise ValueError(f"Unknown basemap theme '{name}'; use {', '.join(THEMES)}.{hint}")


def resolve(name: str) -> tuple[str, str | None]:
    """The theme and default relief behind a basemap name such as 'terrain'."""
    return ALIASES.get(name, (name, None))


def _zoom(*stops: float) -> list:
    # Linear interpolation over zoom from (zoom, value) pairs
    return ["interpolate", ["linear"], ["zoom"], *stops]


def _steps(t: Theme) -> list:
    # Flat colour bands: each band holds its colour until a hair below the next stop
    stops: list = []
    for i, (h, c) in enumerate(zip(TINT_STOPS, t.tint, strict=True)):
        stops += [h, c]
        if i + 1 < len(TINT_STOPS):
            stops += [TINT_STOPS[i + 1] - 0.01, c]
    return ["interpolate", ["linear"], ["elevation"], *stops]


def _relief_layers(t: Theme, relief: str) -> list[dict]:
    # Shaded relief from the terrain source; strength eases off as you zoom in
    strength = _zoom(3, 0.6 if t.dark else 0.5, 8, 0.4, 13, 0.25)
    layers = []
    if relief == "steps":
        layers.append({"id": "relief-tint", "type": "color-relief", "source": "terrain",
                       "paint": {"color-relief-color": _steps(t), "color-relief-opacity": 0.95}})
        # A faint shade keeps the bands reading as terraces, not flat paint
        strength = _zoom(3, 0.3, 13, 0.15)
    if relief == "tint":
        stops = [v for pair in zip(TINT_STOPS, t.tint, strict=True) for v in pair]
        layers.append({"id": "relief-tint", "type": "color-relief", "source": "terrain",
                       "paint": {"color-relief-color": ["interpolate", ["linear"],
                                                        ["elevation"], *stops],
                                 "color-relief-opacity": 0.9}})
    if relief == "sharp":
        # Light from four directions brings out ridges a single sun flattens
        paint = {"hillshade-method": "multidirectional",
                 "hillshade-illumination-direction": [270, 315, 0, 45],
                 "hillshade-illumination-altitude": [30, 30, 30, 30],
                 "hillshade-shadow-color": [t.shadow] * 4,
                 "hillshade-highlight-color": [t.highlight] * 4,
                 "hillshade-exaggeration": strength}
    else:
        paint = {"hillshade-shadow-color": t.shadow, "hillshade-highlight-color": t.highlight,
                 "hillshade-accent-color": t.shadow, "hillshade-exaggeration": strength,
                 "hillshade-illumination-direction": 315}
    layers.append({"id": "relief-shade", "type": "hillshade", "source": "terrain",
                   "paint": paint})
    return layers


def _base_layers(t: Theme) -> list[dict]:
    # Ground, water, roads and boundaries from the OpenMapTiles schema
    src = {"source": "openmaptiles"}
    not_sea = ["!=", ["get", "maritime"], 1]
    return [
        {"id": "park", "type": "fill", **src, "source-layer": "park",
         "paint": {"fill-color": t.land, "fill-opacity": 0.7}},
        {"id": "landcover", "type": "fill", **src, "source-layer": "landcover",
         "filter": ["match", ["get", "class"], ["wood", "grass", "wetland"], True, False],
         "paint": {"fill-color": t.land, "fill-opacity": 0.6}},
        {"id": "water", "type": "fill", **src, "source-layer": "water",
         "paint": {"fill-color": t.water}},
        {"id": "waterway", "type": "line", **src, "source-layer": "waterway", "minzoom": 6,
         "filter": ["match", ["get", "class"], ["river", "canal"], True, False],
         "paint": {"line-color": t.water_line, "line-width": _zoom(6, 0.5, 12, 2, 16, 5)}},
        {"id": "road-minor", "type": "line", **src, "source-layer": "transportation",
         "minzoom": 11, "filter": ["match", ["get", "class"], MINOR_ROADS, True, False],
         "layout": {"line-cap": "round", "line-join": "round"},
         "paint": {"line-color": t.road_minor, "line-width": _zoom(11, 0.5, 16, 6)}},
        {"id": "road-major", "type": "line", **src, "source-layer": "transportation",
         "minzoom": 5, "filter": ["match", ["get", "class"], MAJOR_ROADS, True, False],
         "layout": {"line-cap": "round", "line-join": "round"},
         "paint": {"line-color": t.road_major, "line-width": _zoom(5, 0.5, 10, 1.5, 16, 10)}},
        {"id": "boundary-state", "type": "line", **src, "source-layer": "boundary",
         "minzoom": 3, "filter": ["all", ["==", ["get", "admin_level"], 4], not_sea],
         "paint": {"line-color": t.boundary_minor, "line-dasharray": [3, 2],
                   "line-width": _zoom(3, 0.4, 10, 1.2)}},
        {"id": "boundary-country", "type": "line", **src, "source-layer": "boundary",
         "filter": ["all", ["==", ["get", "admin_level"], 2], not_sea],
         "layout": {"line-join": "round"},
         "paint": {"line-color": t.boundary, "line-width": _zoom(2, 0.6, 10, 2)}},
    ]


def imagery(source: str | int = 2016, attribution: str | None = None,
            max_zoom: int = 14) -> dict:
    """Choose the imagery for basemap-satellite and basemap-hybrid.

    source is a Sentinel-2 cloudless year (2016 is free for any use with credit; 2017 to 2024
    are non-commercial only) or your own tile URL with {z}, {x} and {y}, such as a provider
    you hold a key for. Returns the imagery now in use.
    """
    if isinstance(source, int) or str(source).isdigit():
        year = int(source)
        if year not in EOX_YEARS:
            raise ValueError(f"Sentinel-2 cloudless years are {', '.join(map(str, EOX_YEARS))}, "
                             f"got {year}.")
        tiles, credit = EOX_TILES.format(layer=EOX_YEARS[year]), EOX_ATTRIBUTION.format(year=year)
    else:
        if not all(k in source for k in ("{z}", "{x}", "{y}")) or not source.startswith("http"):
            raise ValueError("An imagery URL needs http(s) and {z}, {x} and {y}, like "
                             "https://example.com/tiles/{z}/{x}/{y}.jpg")
        if not attribution:
            raise ValueError("Give the imagery's attribution= so the map credits it.")
        tiles, credit = source, attribution
    IMAGERY.update({"tiles": tiles, "attribution": attribution or credit, "maxzoom": max_zoom})
    return dict(IMAGERY)


def _imagery_layers(t: Theme) -> list[dict]:
    # Roads and borders stay on hybrid, a little see-through so the ground shows
    if not t.labels:
        return []
    keep = ("waterway", "road-major", "road-minor", "boundary-state", "boundary-country")
    layers = [lyr for lyr in _base_layers(t) if lyr["id"] in keep]
    for lyr in layers:
        lyr["paint"]["line-opacity"] = 0.75
    return layers


def _building_layer(t: Theme, buildings: str) -> list[dict]:
    # Footprints from zoom 13, or extruded to their mapped height
    src = {"source": "openmaptiles", "source-layer": "building", "minzoom": 13}
    if buildings == "none":
        return []
    if buildings == "3d":
        return [{"id": "buildings", "type": "fill-extrusion", **src,
                 "paint": {"fill-extrusion-color": t.building,
                           "fill-extrusion-height": ["coalesce", ["get", "render_height"], 6],
                           "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
                           "fill-extrusion-opacity": 0.85}}]
    return [{"id": "buildings", "type": "fill", **src,
             "paint": {"fill-color": t.building, "fill-outline-color": t.boundary_minor,
                       "fill-opacity": _zoom(13, 0, 14, 1)}}]


def _label(t: Theme, name: str, layer: str, classes: list[str] | None, minzoom: float,
           maxzoom: float, size: list, upper: bool = False, line: bool = False) -> dict:
    # One label layer; line labels follow the road
    layout = {
        "text-field": ["coalesce", ["get", "name:en"], ["get", "name_en"], ["get", "name"]],
        "text-font": FONT,
        "text-size": size,
        "text-max-width": 8,
    }
    if upper:
        layout.update({"text-transform": "uppercase", "text-letter-spacing": 0.12})
    if line:
        layout["symbol-placement"] = "line"
    out = {"id": f"label-{name}", "type": "symbol", "source": "openmaptiles",
           "source-layer": layer, "minzoom": minzoom, "maxzoom": maxzoom, "layout": layout,
           "paint": {"text-color": t.label, "text-halo-color": t.halo, "text-halo-width": 1.4}}
    if classes:
        out["filter"] = ["match", ["get", "class"], classes, True, False]
    return out


def _label_layers(t: Theme) -> list[dict]:
    # Later layers win label collisions, so the most important come last
    return [
        _label(t, "road", "transportation_name", None, 14, 24, _zoom(14, 9, 18, 13), line=True),
        _label(t, "suburb", "place", ["suburb", "neighbourhood", "quarter"], 12, 16,
               _zoom(12, 9, 15, 12), upper=True),
        _label(t, "town", "place", ["town"], 8, 24, _zoom(8, 10, 14, 14)),
        _label(t, "city", "place", ["city"], 5, 24, _zoom(5, 11, 12, 18)),
        _label(t, "state", "place", ["state"], 4, 9, _zoom(4, 9, 8, 12), upper=True),
        _label(t, "country", "place", ["country"], 2, 7, _zoom(2, 11, 6, 15), upper=True),
    ]


def _data_label_layers(t: Theme, data_labels: list[dict]) -> tuple[dict, list[dict]]:
    # Sources and symbol layers for label-[...]: drawn last, so above the data and the basemap
    sources, layers = {}, []
    for i, lab in enumerate(data_labels):
        sid = f"{DATA_LABEL}-{i}"
        sources[sid] = {"type": "geojson", "data": lab["geojson"]}
        line = lab["placement"] == "line"
        layout = {"text-field": ["get", "t"], "text-font": FONT,
                  "text-size": 11 if line else 12.5, "text-max-width": 9,
                  "symbol-placement": "line" if line else "point"}
        if lab["placement"] == "beside":
            # Beside points, so the label never covers its own symbol
            layout.update({"text-variable-anchor": ["top", "bottom", "left", "right"],
                           "text-radial-offset": 0.9})
        layers.append({"id": sid, "type": "symbol", "source": sid, "layout": layout,
                       "paint": {"text-color": lab.get("color") or t.label,
                                 "text-halo-color": t.halo, "text-halo-width": 1.8}})
    return sources, layers


def style(theme: str = "paper", labels: bool | None = None, hillshade: bool = False,
          relief: str | None = None, buildings: str = "flat", elements: dict | None = None,
          data_labels: list[dict] | None = None) -> dict:
    """MapLibre style JSON for a theme; labels default to the theme's own setting."""
    name, alias_relief = resolve(theme)
    elements = elements or {}
    unknown = set(elements) - set(ELEMENT_FIELDS)
    if unknown:
        raise ValueError(f"Unknown map element {sorted(unknown)}; use {', '.join(ELEMENT_FIELDS)}.")
    t = apply_elements(get_theme(name), elements)
    relief = relief or alias_relief or ("soft" if hillshade else None)
    if relief is not None and relief not in RELIEFS:
        raise ValueError(f"relief must be one of {', '.join(RELIEFS)}, got '{relief}'.")
    if buildings not in BUILDINGS:
        raise ValueError(f"buildings must be one of {', '.join(BUILDINGS)}, got '{buildings}'.")
    show_labels = t.labels if labels is None else labels
    sources: dict = {"openmaptiles": {"type": "vector", "url": OPENFREEMAP_TILES,
                                      "attribution": VECTOR_ATTRIBUTION}}
    layers: list[dict] = [{"id": "background", "type": "background",
                           "paint": {"background-color": t.background}}]
    if t.imagery:
        sources["imagery"] = {"type": "raster", "tiles": [IMAGERY["tiles"]], "tileSize": 256,
                              "maxzoom": IMAGERY["maxzoom"],
                              "attribution": IMAGERY["attribution"]}
        layers.append({"id": "imagery", "type": "raster", "source": "imagery",
                       "paint": {"raster-fade-duration": 0}})
    if relief is not None:
        sources["terrain"] = {"type": "raster-dem", "tiles": [TERRARIUM_TILES], "tileSize": 256,
                              "maxzoom": 15, "encoding": "terrarium",
                              "attribution": TERRAIN_ATTRIBUTION}
        layers.extend(_relief_layers(t, relief))
    if t.imagery:
        layers.extend(_imagery_layers(t))
        # Flat footprints would hide the roofs the imagery already shows
        layers.extend(_building_layer(t, buildings) if buildings == "3d" else [])
    else:
        layers.extend(_base_layers(t))
        layers.extend(_building_layer(t, buildings))
    out = {"version": 8, "name": f"kharita {theme}", "sources": sources}
    if show_labels or data_labels:
        out["glyphs"] = OPENFREEMAP_GLYPHS
    if show_labels:
        layers.extend(_label_layers(t))
    if data_labels:
        extra_sources, extra_layers = _data_label_layers(t, data_labels)
        sources.update(extra_sources)
        layers.extend(extra_layers)
    hidden = {lid for k, v in elements.items() if v == "none" for lid in ELEMENT_LAYERS.get(k, ())}
    out["layers"] = [lyr for lyr in layers if lyr["id"] not in hidden]
    return out


def data_url(style_json: dict, encoding: str = "base64") -> str:
    """The style as a data URL MapLibre can load like any style URL."""
    text = json.dumps(style_json, separators=(",", ":"))
    if encoding == "base64":
        return "data:application/json;base64," + base64.b64encode(text.encode()).decode()
    if encoding == "percent":
        return "data:application/json," + quote(text, safe="")
    raise ValueError(f"encoding must be 'base64' or 'percent', got '{encoding}'.")


_THEME_BASEMAP = None


def _theme_basemap_class():
    # Lonboard's style trait refuses anything but http URLs; its frontend passes any style on
    global _THEME_BASEMAP
    if _THEME_BASEMAP is None:
        import traitlets
        from lonboard.basemap import MaplibreBasemap

        class ThemeBasemap(MaplibreBasemap):
            """A MapLibre basemap whose style may be a data URL or a style object."""

            style = traitlets.Union([traitlets.Unicode(), traitlets.Dict()]).tag(sync=True)

        _THEME_BASEMAP = ThemeBasemap
    return _THEME_BASEMAP


def basemap(theme: str = "paper", labels: bool | None = None, hillshade: bool = False,
            mode: str = "overlaid", encoding: str = "base64", relief: str | None = None,
            buildings: str = "flat", elements: dict | None = None,
            data_labels: list[dict] | None = None):
    """A Lonboard basemap drawing a kharita theme; encoding is base64, percent or object."""
    s = style(theme, labels=labels, hillshade=hillshade, relief=relief, buildings=buildings,
              elements=elements, data_labels=data_labels)
    value = s if encoding == "object" else data_url(s, encoding=encoding)
    return _theme_basemap_class()(style=value, mode=mode)
