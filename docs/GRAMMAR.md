# kharita style grammar, v0.1

Run `kh.help()` for this list in a notebook, and `kh.explain(style)` to see what a style compiles to.

A style is a space-separated list of utilities. Order does not matter. Two utilities that set the same property raise `StyleSyntaxError`.

```python
kh.layer(states, "fill-[pop/area] ramp-ylorrd scheme-q5 stroke-1 stroke-white null-gray-300")
```

## Colours

A colour is `<family>-<shade>` (22 families, shades 50 to 950), `white`, `black` or `transparent`, with an optional `/<opacity>` from 0 to 100.

| Utility | Meaning | Example |
| --- | --- | --- |
| `fill-<colour>` | Constant fill | `fill-indigo-600/70` |
| `stroke-<colour>` | Outline or line colour | `stroke-slate-300` |
| `stroke-<n>` | Outline or line width in pixels | `stroke-2` |
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
| `basemap-light`, `basemap-dark`, `basemap-none` | Basemap theme | `basemap-dark` |
| `legend-none` | Hide this layer's legend | `legend-none` |
| `legend-tl`, `legend-tr`, `legend-bl`, `legend-br` | Legend corner | `legend-br` |

Text such as legend titles, number formats and class labels goes in keyword arguments, not the style string:

```python
kh.layer(states, "fill-[pop] scheme-q5", legend={"title": "Population", "fmt": "{:,.0f}", "labels": ["Low", "", "", "", "High"]})
```

## Reuse

| Feature | Example |
| --- | --- |
| Built-in presets | `preset-choropleth`: `scheme-q5 stroke-1 stroke-white null-gray-300 highlight-amber-400` |
| | `preset-outline`: `fill-transparent stroke-2 stroke-slate-700` |
| | `preset-points`: `size-4 stroke-1 stroke-white highlight-amber-400` |
| Your own named style | `kh.define("roads", "stroke-2 stroke-slate-400")`, then `preset-roads` |

Explicit utilities always override a preset's, wherever they appear in the string: `preset-choropleth scheme-e4` uses equal intervals.

## Hover and 3D

Both passed the Phase 1 spike.

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
