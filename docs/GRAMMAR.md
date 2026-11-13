# kharita style grammar, v0.1

Run `kh.help()` for this list in a notebook, and `kh.explain(style)` to see what a style compiles to.

A style is a space-separated list of utilities. Order does not matter. Two utilities that set the same property raise `StyleSyntaxError`.

```python
import kharita as kh

kh.map(states, "fill-[pop/area] ramp-ylorrd scheme-q5 stroke-1 stroke-white", legend={"title": "People per km2"})
```

## Functions

| Function | Returns |
| --- | --- |
| `kh.map(gdf, style, legend=None, basemap=None, height=500, title=None, subtitle=None, source=None, colors=None, order=None)` | A `kh.Map`; shows itself in a notebook. `basemap=` takes any basemap name and overrides the style; `title`, `subtitle` and `source` draw the title card top left; `colors` and `order` fix category colours |
| `kh.Map(basemap=None, height=500, title=None, subtitle=None, source=None).add(gdf, style, legend=None, colors=None, order=None)` | The same map, for several layers; `.to_html(path)` exports one HTML file |
| `kh.layer(gdf, style)` | Native Lonboard layers, one per geometry type, for your own `lonboard.Map` |
| `kh.legend(gdf, style, dark=False, **legend)` | The legend card as HTML |
| `kh.bind(gdf, style)` | Colour and height arrays plus the `Scale` |
| `kh.parse`, `kh.explain`, `kh.validate`, `kh.define`, `kh.help` | The style language tools |
| `kh.colors(family=None)`, `kh.ramps(kind=None, search=None, source=None)` | Every colour shade, or every ramp, as swatches in the notebook; `.names` lists them, `.to_html(path)` saves a page |
| `kh.check_ramp(name)` | Whether a ramp's lightness steps are even and whether it is safe for colour-blind readers |
| `kh.contours(where, interval=None, zoom=None, index_every=5, detail="medium", smooth=None)` | Contour lines over a GeoDataFrame's extent or a `(west, south, east, north)` box: a GeoDataFrame with `elevation`, `index` and `weight` columns, traced from the open Mapzen terrain tiles. `detail` is `low`, `medium` or `high`; `smooth` sets the blur in metres (0 for raw lines). Needs `pip install kharita[terrain]` |
| `kh.imagery(source=2016, attribution=None, max_zoom=14)` | The imagery behind `basemap-satellite` and `basemap-hybrid`: a Sentinel-2 cloudless year, or your own `{z}/{x}/{y}` tile URL with its attribution |
| `kh.compare(m1, m2, ..., link=True)` | Maps side by side in the notebook; linked maps pan and zoom together |
| `kh.palette(name, colors, kind="sequential")` | Registers your own ramp as `ramp-<name>` |
| `kh.theme(name, base="paper", ramp=None, **elements)` | Registers your own theme as `theme-<name>` and `basemap-<name>` |

`legend=` takes `title`, `fmt` (such as `"{:,.0f}"`), `labels` (one per class; for `scheme-linear`, two or three tick labels), `note`, and `style`: `"list"` (default, one row per class with counts) or `"bar"` (a compact bar with the class edges under it).

Only the geometry and the columns named in the style are sent to the map. Data without a CRS is refused; other CRSs are reprojected. Rows without geometry are skipped with a warning.

## Colours

A colour is `<family>-<shade>` (22 families, shades 50 to 950), `white`, `black`, `transparent`, or any hex colour in brackets such as `[#0f766e]`, with an optional `/<opacity>` from 0 to 100. Run `kh.colors()` to see every shade.

| Utility | Meaning | Example |
| --- | --- | --- |
| `fill-<colour>` | Constant fill | `fill-indigo-600/70` |
| `stroke-<colour>` | Outline or line colour | `stroke-slate-300` |
| `stroke-<n>` | Outline or line width in pixels | `stroke-2` |
| `stroke-[<expr>]` | Line colour by data, for line layers | `stroke-[speed]` |
| `size-<n>` | Point radius in pixels | `size-6` |
| `size-[<expr>]` | Circles sized by data: area grows with the value, with a nested-circle key in the legend. Points only; turn polygons into points with `gdf.representative_point()` | `size-[pop]` |
| `size-max-<n>` | Radius of the largest circle (default 24) | `size-max-30` |
| `width-[<expr>]` | Line or outline width by data, never thinner than half a pixel, with a key in the legend | `width-[rank]` |
| `width-max-<n>` | Width of the widest line (default 8) | `width-max-10` |
| `dash-<on>-<off>`, `dash-<n>` | Dashed lines and outlines; lengths are in line widths | `dash-4-2` |
| `label-[<col>]` | Your own labels, placed by the map so they never overlap: inside polygons, beside points, along lines. Needs a kharita basemap | `label-[name]` |
| `opacity-<n>` | Whole-layer opacity, 0 to 100 | `opacity-80` |
| `highlight-<colour>` | Colour of the feature under the mouse | `highlight-amber-400` |
| `null-<colour>` | Colour for missing values (default `gray-300`) | `null-zinc-200` |

## Data-bound fill

| Utility | Meaning | Example |
| --- | --- | --- |
| `fill-[<expr>]` | Colour by data | `fill-[pop]` |
| `ramp-<name>` | Ramp for the data (`-r` reverses); see Ramps below | `ramp-batlow-r` |
| `scheme-q<k>` | Quantiles, k classes (3 to 9) | `scheme-q5` |
| `scheme-e<k>` | Equal interval, k classes | `scheme-e4` |
| `scheme-[<b1>,<b2>,...]` | Explicit class breaks | `scheme-[10,50,100]` |
| `scheme-linear` | No classes: colour runs smoothly from the lowest to the highest value, with a gradient legend | `scheme-linear` |
| `scheme-cat` | Categorical, one colour per value | `scheme-cat` |
| `scheme-div` | Diverging, centred on 0 | `scheme-div` |
| `scheme-div-[<v>]` | Diverging, centred on a value | `scheme-div-[50]` |

**Bracket expressions** allow only: a column (`[pop]`), a quoted column with odd characters (`['pop/km2']`), a ratio of two columns (`[pop/area]`), or a column times a number (`[pop*1000]`). Spaces in column names are fine: `[median income]`.

**Defaults:** a numeric column gets `ramp-viridis scheme-q5` (or its theme's ramp); a text column gets `ramp-set2 scheme-cat`. Categories beyond the ramp's colour count are grouped as "other". Division by zero is treated as missing.

## Ramps

About 160 ramps by name. Run `kh.ramps()` to see them all as swatches, `kh.ramps(kind="diverging")` or `kh.ramps(search="sun")` to narrow the list.

| Collection | Examples | Licence |
| --- | --- | --- |
| ColorBrewer | `ylorrd`, `blues`, `rdbu`, `spectral`, `set2`, `paired` | Apache 2.0 |
| matplotlib | `viridis`, `magma`, `plasma`, `inferno`, `cividis`, `turbo` | CC0, Turbo Apache 2.0 |
| Crameri scientific | `batlow`, `oslo`, `lajolla`, `davos`, `vik`, `roma`, `berlin` | MIT |
| cmocean | `thermal`, `haline`, `deep`, `ice`, `rain`, `balance`, `topo` | MIT |
| CARTOColors | `sunset`, `emrld`, `burg`, `temps`, `prism`, `bold`, `safe`; CARTO's Teal is `carto-teal` | CC BY 4.0 |
| Standards | `ipc` (food security phases 1 to 5), `worldcover` (ESA land cover codes), `landuse` | Fixed colours per value |
| kharita | `terrain`, `ndvi`, `aurora`, `ember` | MIT |
| Friendly names | `heatwave` (blue to red, same as `rdbu-r`), `ocean`, `forest`, `desert`, `hypsometric` | As their target |

Build a ramp from Tailwind colours:

| Ramp | Meaning | Example |
| --- | --- | --- |
| `ramp-<family>` | One family, shade 100 to 900 | `ramp-teal` |
| `ramp-<family>-<family>` | Diverging: the first family dark to light, a neutral middle, the second light to dark | `ramp-teal-rose` |
| `ramp-[<colour>,<colour>,...]` | Your own stops, blended evenly for numbers and used exactly, in order, for categories | `ramp-[sky-100,indigo-500,#4c1d95]` |

Standard palettes (`ipc`, `worldcover`, `landuse`) give each value its fixed colour and label; other values become "other". For any categories, `colors={"mosque": "emerald-600"}` fixes chosen colours and `order=["hospital", "school"]` sets the legend order; the rest come from the ramp.

Ramps with fewer stops than classes blend extra colours instead of repeating one.

## How data is classified

`kh.bind(gdf, style)` turns a style into colour and height arrays in the table's row order, plus a `Scale` (breaks, labels, colours, counts) the legend is drawn from.

- Quantile ties reduce the number of classes, with a warning.
- `scheme-div` always uses 7 classes, symmetric around the centre, with the middle class neutral.
- Categories are ordered by frequency; beyond the ramp's colour count (12 for continuous ramps) the rest become "other".
- Missing values, division by zero and infinities are shown as no data and counted in the legend.
- Numbers stored as text are converted, with a warning. Dates are refused.
- Whole-number columns with 12 or fewer distinct values warn that `scheme-cat` may be meant.
- `extrude-[...]` scales the tallest feature to `extrude-max`, or to a tenth of the data's extent. Negative and missing values are drawn flat.
- Extruded layers skip near-white ramp colours, which 3D lighting turns grey, and draw their edges a shade darker than the fill. The legend adds a height key that says what height shows and how tall the tallest feature is.

## Map and legend

| Utility | Meaning | Example |
| --- | --- | --- |
| `basemap-<name>` | Basemap (see Design below) | `basemap-dark` |
| `legend-none` | Hide this layer's legend | `legend-none` |
| `legend-tl`, `legend-tr`, `legend-bl`, `legend-br` | Legend corner | `legend-br` |

Text such as legend titles, number formats and class labels goes in keyword arguments, not the style string:

```python
kh.layer(states, "fill-[pop] scheme-q5", legend={"title": "Population", "fmt": "{:,.0f}", "labels": ["Low", "", "", "", "High"]})
```

## Design

Every basemap is keyless. Three are hosted by OpenFreeMap and used as they are; the rest are kharita themes, built as MapLibre styles so kharita can recolour them, add relief and buildings, and draw your data under the place names.

| Basemap | Look | Kind |
| --- | --- | --- |
| `basemap-light` | Light grey, the default | Hosted (positron) |
| `basemap-dark` | Near black | Hosted |
| `basemap-fiord` | Slate blue | Hosted |
| `basemap-paper` | Warm cream, print style | Theme |
| `basemap-midnight` | Deep navy | Theme |
| `basemap-mono` | Neutral greys | Theme |
| `basemap-neon` | Dark violet | Theme |
| `basemap-muted` | Pale, no labels | Theme |
| `basemap-topo` | Near-white, warm vegetation, red roads; made for contours | Theme |
| `basemap-satellite` | Sentinel-2 cloudless imagery, no labels | Theme (imagery) |
| `basemap-hybrid` | Imagery with roads, borders and labels | Theme (imagery) |
| `basemap-terrain` | Paper with tinted relief | Theme |
| `basemap-none` | Nothing | |

| Utility | Meaning | Example |
| --- | --- | --- |
| `theme-<name>` | Basemap, default ramp and legend style together: `paper` (ylorrd), `midnight` (viridis), `mono` (blues), `neon` (plasma), `topo` (terrain) | `theme-midnight` |
| `relief-soft` | Shaded terrain, one light source | `relief-soft` |
| `relief-steps` | Flat colour bands by height, like a layered model, with a faint shade | `relief-steps` |
| `relief-sharp` | Shaded terrain lit from four directions; crisper ridges | `relief-sharp` |
| `relief-tint` | Colour by elevation, with shading on top | `relief-tint` |
| `buildings-flat`, `buildings-3d`, `buildings-none` | Basemap building footprints from zoom 13 (flat is the default) | `buildings-3d` |
| `labels-none` | Hide the basemap's place labels | `labels-none` |
| `halo-<colour>` | Two faint wide bands under outlines, lines or points; opacity scales both | `halo-cyan-300` |
| `glow` | Colours add up where features overlap. Applies to the whole map; meant for dark basemaps | `glow` |

**Map elements.** Every part of a kharita theme takes a colour, so a theme is only a set of defaults:

| Element | Utility | Example |
| --- | --- | --- |
| Ground | `land-<colour>` | `land-stone-100` |
| Sea and lakes | `water-<colour>` | `water-sky-200` |
| Rivers and canals | `rivers-<colour>`, `rivers-none` | `rivers-sky-400` |
| Parks and vegetation | `parks-<colour>`, `parks-none` | `parks-emerald-100` |
| Major roads | `roads-<colour>`, `roads-none` | `roads-amber-200` |
| Minor streets | `streets-<colour>`, `streets-none` | `streets-stone-200` |
| Buildings | `buildings-<colour>` | `buildings-amber-100` |
| Country borders | `borders-<colour>`, `borders-none` | `borders-slate-500` |
| State borders | `admin-<colour>`, `admin-none` | `admin-slate-300` |
| Place and street names | `labels-<colour>` | `labels-slate-700` |

Save a set of them as your own theme with `kh.theme("desert", base="paper", land="[#f3e5c8]", water="sky-200", ramp="lajolla")`, then write `theme-desert`.

A warning fires when a class colour is almost the basemap's ground colour, since those features would vanish.

- On a theme with labels, your layers are drawn under the place names, so labels stay readable over the data.
- `relief-*`, `buildings-*`, `labels-*` and the element utilities need a kharita theme; with no basemap set they pick `paper`. On `basemap-light`, `dark` or `fiord` they raise an error.
- A typed `ramp-` always beats the theme's default ramp. In a map with several layers, the first layer to set the basemap, theme, relief, buildings or labels wins.
- Elevation comes from the Mapzen Terrain Tiles on AWS Open Data; place data from OpenStreetMap via OpenFreeMap. Both credits appear on the map.

## Contours

```python
c = kh.contours(states[states["key"] == "SDN_09"], interval=100)
m = kh.Map()
m.add(c, "preset-topo basemap-topo")
m.add(c[c["index"]], "stroke-transparent label-[elevation] legend-none")
```

Index contours (every fifth line by default) have `weight` 2 and draw twice as thick under `preset-topo`; labelling them gives the classic topographic look. Colour by height instead with `stroke-[elevation] ramp-terrain`. Contours combine with `relief-` designs on the basemap, and with `basemap-satellite` or `basemap-hybrid` (use a light stroke such as `stroke-amber-200`).

Contours are generalised the way printed maps are: the elevation is blurred, lines shorter than eight blur widths are dropped, and the rest are simplified and rounded. `detail="medium"` blurs at least 300 m, or a three-hundredth of the area's width; `low` doubles that and `high` halves it.

Imagery: Sentinel-2 cloudless 2016 by EOX IT Services GmbH is free for any use with credit (CC BY-SA 4.0); `kh.imagery(2024)` switches to a newer year, which EOX licenses for non-commercial use only.

## Reuse

| Feature | Example |
| --- | --- |
| Built-in presets | `preset-choropleth`: `scheme-q5 stroke-1 stroke-white null-gray-300 highlight-amber-400` |
| | `preset-outline`: `fill-transparent stroke-2 stroke-slate-700` |
| | `preset-points`: `size-4 stroke-1 stroke-white highlight-amber-400` |
| | `preset-topo`: `stroke-orange-800/80 width-[weight] width-max-1.6 legend-none`, for `kh.contours` output |
| Your own named style | `kh.define("roads", "stroke-2 stroke-slate-400")`, then `preset-roads` |

Explicit utilities always override a preset's, wherever they appear in the string: `preset-choropleth scheme-e4` uses equal intervals. A preset's scheme also gives way to a categorical ramp you type and to text data, so `preset-choropleth fill-[region] ramp-set2` works.

## Hover and 3D

Both passed the Phase 1 spike. `buildings-3d` and `extrude-[...]` tilt the camera to 45 degrees.

| Utility | Meaning | Example |
| --- | --- | --- |
| `tooltip-[<col>,<col>]` | Columns shown on hover | `tooltip-[name,pop]` |
| `extrude-[<expr>]` | 3D height from data | `extrude-[pop]` |
| `extrude-max-<m>` | Tallest feature in metres | `extrude-max-5000` |

## Errors

| Error | Raised when |
| --- | --- |
| `StyleSyntaxError` | Unknown utility, bad colour, unbalanced bracket, two utilities setting the same thing, a ramp or scheme without a data-bound fill, a categorical ramp with a numeric scheme. Carries the token, its position and a suggestion |
| `BindingError` | A column is missing, not numeric where a number is needed, or the CRS is missing. Carries the column and the closest names |
