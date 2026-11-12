# Phase 5: Design system

**Status:** in progress. Spike done 12 Nov 2026; first build (5b) 13 Nov 2026, 569 tests passing. This file is finished at the end of the phase.

## Goal

Turn a correct map into one that looks designed, with no extra code beyond a theme token and a title. Grew during the phase to cover city-scale maps (roads, buildings) and several relief designs.

## Design spike results (`notebooks/05_design_spike.ipynb`)

| Test | Result | Decision |
| --- | --- | --- |
| A, B, C: theme as base64 URL, percent URL, style object | All three render | Lonboard refuses non-http styles, so kharita subclasses its basemap widget; base64 is the default because it was also proven in export |
| D: five themes | All distinct; muted has no labels | Kept: paper, midnight, mono, neon, muted |
| E: hillshade | Clear at Jebel Marra; invisible at country zoom on midnight | Strength now eases with zoom; dark themes got lighter highlights |
| F: labels above data | Works in interleaved mode | Default for every theme with labels |
| G: glow, luma.gl v9 names | Overlaps turn bright | `glow` utility, map-wide |
| H: glow, WebGL constants | No visible effect | Dropped |
| I: halo | Soft cyan glow along borders | `halo-<colour>` utility |
| J: OpenFreeMap dark and fiord | Both load, keyless | `basemap-dark` now OpenFreeMap dark (CARTO dropped); `basemap-fiord` added |
| K: export with a theme | Works | No change needed |
| L: legend clears the corner button | Works | Bottom margin 72px kept |

## What was built (5b)

| File | Change |
| --- | --- |
| `kharita/basemaps.py` | Hosted and themed basemaps; relief designs `soft`, `sharp` (four light sources), `tint` (colour by elevation); building footprints flat or 3D; road and suburb labels at city zoom |
| `kharita/registry.py`, `parser.py`, `spec.py` | New utilities: `theme-`, `relief-`, `buildings-`, `labels-none`, `halo-`, `glow`; more `basemap-` names; bare utilities (no value) |
| `kharita/adapter.py` | Halo bands under polygons, lines and points; halos ignore the mouse |
| `kharita/binder.py` | A theme's default ramp |
| `kharita/maps.py` | Basemap resolution, layers under labels, glow parameters, tilted camera for `buildings-3d` |
| `notebooks/00b_city_data.ipynb` | Central Khartoum roads and buildings from Overture Maps |
| `notebooks/05b_city_and_relief.ipynb` | City maps and relief designs to check by eye |

## Decisions

- Glow is map-wide: deck.gl blending is set on the map, and Lonboard layers do not expose their own parameters. It warns on light basemaps, where additive colours turn white.
- `relief-`, `buildings-` and `labels-none` need a kharita theme; hosted styles cannot be edited. With no basemap set they pick `paper`.
- In a multi-layer map, the first layer to set the basemap, theme, relief, buildings or labels wins.
- City data comes from Overture Maps, read straight from its cloud files. osmnx was tried first, but the public Overpass servers refused or timed out on scripted downloads. Overture mixes OpenStreetMap (ODbL) with other open sources; it is downloaded by a notebook and gitignored, not committed.
- Building heights: Overture's height, else 3 m per floor, else 6 m, with the source kept in `height_source`.

## Tests

`test_basemaps` (themes, reliefs, buildings, data URLs, name tables), plus new cases in `test_adapter` (halo), `test_maps` (themes, interleaving, glow, relief rules, export) and `test_parser` (bare utilities, explain). All 72 theme, relief and building combinations were also checked against MapLibre 5's style validator and loaded in a browser.

## How to verify

```
pip install -e .[dev,demo]
pytest -q
```

Then run `notebooks/00b_city_data.ipynb` once, and `notebooks/05b_city_and_relief.ipynb` top to bottom.

## Still to build (5c)

- Map frame: `title=`, `subtitle=`, `source=` as an HTML card in the notebook and export
- Gradient legend for continuous schemes; height key for extrusion; 3D legend note
- Ramps `ice`, `ember`, `terrain`, checked for even lightness steps
- Extruded layers skip the palest ramp stops
- Open a Lonboard issue asking to expose `material`

## Known issues

- Glow lightens every layer on the map, not only the one that asked for it.
- `extrude-max` scales the tallest feature, so true building heights need `extrude-max` set to the tallest height (see 05b cell F). A metres option is a candidate for 5c.
