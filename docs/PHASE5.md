# Phase 5: Design system

**Status:** built, 13 Nov 2026, 793 tests passing; closes once `notebooks/05d_colours_and_elements.ipynb` passes on the laptop. Spike 12 Nov; 5b, 5c and 5d built 13 Nov.

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

## City and relief check (`notebooks/05b_city_and_relief.ipynb`)

All 12 tests passed on central Khartoum: 10,706 roads and 71,223 buildings. Findings: extruded buildings showed white speckle (fixed in 5c); a pale square near Jebel Marra appears in every relief design and looks like a gap in the elevation tiles. Preferred looks: muted for city basemaps, `relief-tint` on neon.

## What was built (5c)

| Change | Where |
| --- | --- |
| Title card: `title=`, `subtitle=`, `source=` on `kh.map` and `kh.Map`, top left, stacked above a top-left legend; the exported page takes the title | `legend.py` `frame_card`, `maps.py` |
| `scheme-linear`: unclassed colour along the ramp, with a gradient legend and low, middle, high ticks | `classify.py`, `registry.py`, `legend.py` |
| `legend={"style": "bar"}`: classes as one bar with their edges underneath | `legend.py` |
| Height key on extruded layers, with the 3D shading note | `legend.py` `height_block`, `maps.py` |
| Extruded layers skip near-white ramp stops; strong colours such as viridis yellow are kept | `classify.py` `ramp_stops`, `binder.py` |
| Extruded edges are the fill a shade darker, not white | `adapter.py` |
| Draft Lonboard issue asking to expose `material` | `docs/drafts/lonboard-material-issue.md` |

Moved to 5d: the `ice`, `ember` and `terrain` ramps, because 5d brings the full ramp catalogue, which already has an `ice` (cmocean).

## 5c check (`notebooks/05c_title_and_legends.ipynb`)

Six of seven passed. Test D failed: bar legend labels such as 5,274,321 ran past the bar. Fixed in 5d (below).

## What was built (5d): colour system and map elements

| Change | Where |
| --- | --- |
| Hex colours anywhere a colour goes: `fill-[#0f766e]/70`, `halo-[#fde047]`, `colors={"x": "#111"}` | `palette.py`, `registry.py` |
| 138 named ramps: ColorBrewer (35), matplotlib (6), Crameri (34), cmocean (19), CARTOColors (32), standards and kharita originals; 22 Tailwind family ramps on top | `data/ramps.json`, generated by `tools/make_ramps.py` |
| Friendly names: `heatwave`, `ocean`, `forest`, `desert`, `hypsometric` | `ramps.json` aliases |
| Ramps from Tailwind: `ramp-teal`, `ramp-teal-rose`, `ramp-[sky-100,indigo-500,#4c1d95]`, blended in OKLab | `palette.py` |
| Standard palettes with fixed colours and labels per value: `ipc`, `worldcover`, `landuse` | `classify.py` |
| `colors=` and `order=` on `kh.map`, `Map.add`, `kh.layer`, `kh.bind`, `kh.legend` | `classify.py`, `binder.py`, `adapter.py`, `maps.py` |
| `kh.palette()` and `kh.theme()` for your own ramps and themes | `catalog.py` |
| Map element utilities: `land-`, `water-`, `rivers-`, `parks-`, `roads-`, `streets-`, `buildings-<colour>`, `borders-`, `admin-`, `labels-<colour>`, with `-none` where it makes sense | `registry.py`, `basemaps.py` |
| `relief-steps`: flat colour bands by height | `basemaps.py` |
| `kh.colors()`, `kh.ramps()`, `kh.check_ramp()`; `docs/colours.html` cheat sheet | `catalog.py` |
| Warning when a class colour nearly matches the basemap ground (a diverging scale's neutral middle is exempt) | `maps.py` |
| Bar legend: short numbers by default (554K, 1.27M), ticks exactly under the class edges, two rows when crowded, short numbers when even two rows overflow | `legend.py` |
| Short published ramps blend extra colours instead of repeating when more classes are asked for | `classify.py` |

## Decisions (5d)

- One flat namespace of ramp names. Tailwind family names are reserved for family ramps, so CARTOColors' Teal is `carto-teal`.
- Published palettes keep their own colours and stop counts; sampled colormaps keep 11 stops, as before. The original 24 ramps are byte for byte unchanged.
- Standard palettes never invent colours: a value outside `ipc` or `worldcover` is grouped as "other".
- An inline ramp is blended for numbers but used exactly, in order, for categories.
- The colour-blind check simulates protanopia and deuteranopia (Machado, 2009) and needs neighbouring classes at least 10 CIE76 units apart; lightness is "even" when the spread of steps is under 30% of their mean. Both are guides, not guarantees.
- The `ice`, `ember` and `terrain` ramps moved here from 5c; `ice` is cmocean's.

## Tests (5d)

`test_colours.py`, 174 cases: hex parsing, every ramp passes the checks, family, two-family and inline ramps, IPC and WorldCover keys, fixed colours and order, palettes and themes registered and used, every element changes only its own layer, elements refused on hosted basemaps, stepped relief bands, the ground warning, galleries, compact numbers. Every theme, relief and element combination also passed MapLibre 5's style validator and loaded in a browser.

## Known issues

- Glow lightens every layer on the map, not only the one that asked for it.
- `extrude-max` scales the tallest feature, so true building heights need `extrude-max` set to the tallest height (see 05b cell F). A metres option is moved to v0.2.
- `kh.palette` and `kh.theme` last for the Python session; save them in a module you import, like `kh.define`.
