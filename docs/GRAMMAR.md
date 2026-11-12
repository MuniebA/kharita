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
| `kh.map(gdf, style, legend=None, basemap=None, height=500)` | A `kh.Map`; shows itself in a notebook. `basemap=` takes any basemap name and overrides the style |
| `kh.Map(basemap=None, height=500).add(gdf, style, legend=None)` | The same map, for several layers; `.to_html(path)` exports one HTML file |
| `kh.layer(gdf, style)` | Native Lonboard layers, one per geometry type, for your own `lonboard.Map` |
| `kh.legend(gdf, style, dark=False, **legend)` | The legend card as HTML |
| `kh.bind(gdf, style)` | Colour and height arrays plus the `Scale` |
| `kh.parse`, `kh.explain`, `kh.validate`, `kh.define`, `kh.help` | The style language tools |

`legend=` takes `title`, `fmt` (such as `"{:,.0f}"`), `labels` (one per class) and `note`.

Only the geometry and the columns named in the style are sent to the map. Data without a CRS is refused; other CRSs are reprojected. Rows without geometry are skipped with a warning.

## Colours

A colour is `<family>-<shade>` (22 families, shades 50 to 950), `white`, `black` or `transparent`, with an optional `/<opacity>` from 0 to 100.

| Utility | Meaning | Example |
| --- | --- | --- |
| `fill-<colour>` | Constant fill | `fill-indigo-600/70` |
| `stroke-<colour>` | Outline or line colour | `stroke-slate-300` |
| `stroke-<n>` | Outline or line width in pixels | `stroke-2` |
| `stroke-[<expr>]` | Line colour by data, for line layers | `stroke-[speed]` |
| `size-<n>` | Point radius in pixels | `size-6` |
| `opacity-<n>` | Whole-layer opacity, 0 to 100 | `opacity-80` |
| `highlight-<colour>` | Colour of the feature under the mouse | `highlight-amber-400` |
| `null-<colour>` | Colour for missing values (default `gray-300`) | `null-zinc-200` |

## Data-bound fill

| Utility | Meaning | Example |
| --- | --- | --- |
| `fill-[<expr>]` | Colour by data | `fill-[pop]` |
| `ramp-<name>` | Ramp for the data (`-r` reverses) | `ramp-viridis-r` |
| `scheme-q<k>` | Quantiles, k classes (3 to 9) | `scheme-q5` |
| `scheme-e<k>` | Equal interval, k classes | `scheme-e4` |
| `scheme-[<b1>,<b2>,...]` | Explicit class breaks | `scheme-[10,50,100]` |
| `scheme-cat` | Categorical, one colour per value | `scheme-cat` |
| `scheme-div` | Diverging, centred on 0 | `scheme-div` |
| `scheme-div-[<v>]` | Diverging, centred on a value | `scheme-div-[50]` |

**Bracket expressions** allow only: a column (`[pop]`), a quoted column with odd characters (`['pop/km2']`), a ratio of two columns (`[pop/area]`), or a column times a number (`[pop*1000]`). Spaces in column names are fine: `[median income]`.

**Defaults:** a numeric column gets `ramp-viridis scheme-q5`; a text column gets `ramp-set2 scheme-cat`. Categories beyond the ramp's colour count are grouped as "other". Division by zero is treated as missing.

## How data is classified

`kh.bind(gdf, style)` turns a style into colour and height arrays in the table's row order, plus a `Scale` (breaks, labels, colours, counts) the legend is drawn from.

- Quantile ties reduce the number of classes, with a warning.
- `scheme-div` always uses 7 classes, symmetric around the centre, with the middle class neutral.
- Categories are ordered by frequency; beyond the ramp's colour count (12 for continuous ramps) the rest become "other".
- Missing values, division by zero and infinities are shown as no data and counted in the legend.
- Numbers stored as text are converted, with a warning. Dates are refused.
- Whole-number columns with 12 or fewer distinct values warn that `scheme-cat` may be meant.
- `extrude-[...]` scales the tallest feature to `extrude-max`, or to a tenth of the data's extent. Negative and missing values are drawn flat.

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
| `basemap-terrain` | Paper with tinted relief | Theme |
| `basemap-none` | Nothing | |

| Utility | Meaning | Example |
| --- | --- | --- |
| `theme-<name>` | Basemap, default ramp and legend style together: `paper` (ylorrd), `midnight` (viridis), `mono` (blues), `neon` (plasma) | `theme-midnight` |
| `relief-soft` | Shaded terrain, one light source | `relief-soft` |
| `relief-sharp` | Shaded terrain lit from four directions; crisper ridges | `relief-sharp` |
| `relief-tint` | Colour by elevation, with shading on top | `relief-tint` |
| `buildings-flat`, `buildings-3d`, `buildings-none` | Basemap building footprints from zoom 13 (flat is the default) | `buildings-3d` |
| `labels-none` | Hide the basemap's place labels | `labels-none` |
| `halo-<colour>` | Two faint wide bands under outlines, lines or points; opacity scales both | `halo-cyan-300` |
| `glow` | Colours add up where features overlap. Applies to the whole map; meant for dark basemaps | `glow` |

- On a theme with labels, your layers are drawn under the place names, so labels stay readable over the data.
- `relief-*`, `buildings-*` and `labels-none` need a theme; with no basemap set they pick `paper`. On `basemap-light`, `dark` or `fiord` they raise an error.
- A typed `ramp-` always beats the theme's default ramp. In a map with several layers, the first layer to set the basemap, theme, relief, buildings or labels wins.
- Elevation comes from the Mapzen Terrain Tiles on AWS Open Data; place data from OpenStreetMap via OpenFreeMap. Both credits appear on the map.

## Reuse

| Feature | Example |
| --- | --- |
| Built-in presets | `preset-choropleth`: `scheme-q5 stroke-1 stroke-white null-gray-300 highlight-amber-400` |
| | `preset-outline`: `fill-transparent stroke-2 stroke-slate-700` |
| | `preset-points`: `size-4 stroke-1 stroke-white highlight-amber-400` |
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
