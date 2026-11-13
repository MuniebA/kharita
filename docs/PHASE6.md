# Phase 6: Symbols, labels, contours and the gallery

**Status:** 6a passed on the laptop; 6b built 13 Nov 2026, 877 tests passing, check notebook `notebooks/06b_contours_satellite_compare.ipynb` to run. 6c (scenario gallery, README, cheat sheet) next.

## Goal

Cover the map types the scenario plan needs that colour alone cannot: proportional symbols, line width by data, dashed lines, your own labels, and topographic contours. Then show every scenario in a gallery before release.

## What was built (6a)

| Change | Where |
| --- | --- |
| `size-[col]`, `size-max-<px>`: point radius by data, scaled by area (square root), so a value twice as big draws a circle twice the area | `binder.py` `_radius`, `adapter.py` |
| `width-[col]`, `width-max-<px>`: line or outline width by data, linear, never under 0.5 px | `binder.py` `_width`, `adapter.py` |
| `dash-<on>` and `dash-<on>-<off>`: dashed lines and outlines (Lonboard PathStyleExtension) | `adapter.py` `_dashed` |
| `label-[col]`: your own labels drawn by the basemap above the data; polygons at a point inside, points beside, lines along the line; numbers formatted (1,200; 50.5) | `maps.py`, `basemaps.py` |
| Legend keys: nested circles for size, three line weights for width | `legend.py` `size_block`, `width_block` |
| `basemap-topo`: white ground, warm tints, brown hillshade, like a printed topographic sheet | `basemaps.py` |
| `kh.contours(where, interval, zoom, index_every, smooth, below_sea)`: contour lines from the Mapzen terrain tiles as a GeoDataFrame with `elevation`, `index` and `weight` | `terrain.py` |
| `preset-topo`: brown contours, index lines twice the weight | `registry.py` |
| `terrain` extra: `pip install kharita[terrain]` (contourpy, Pillow) | `pyproject.toml` |

## Decisions

- Contours moved forward from v0.3 into Phase 6, at the user's request after the 05d check (a topographic reference image).
- Contours are data, not a basemap layer: `kh.contours` returns lines, so they are styled, coloured, labelled and exported like any other layer.
- Interval: chosen for about 20 lines over the area's height range, rounded to 1, 2, 2.5 or 5 times a power of ten. Every fifth line is an index contour, the usual cartographic convention.
- Zoom: the most detailed zoom that needs at most 16 tiles (capped at 13); a hard limit of 64 tiles stops accidental huge downloads.
- A light Gaussian blur (sigma 1 pixel) before tracing removes the stair steps of the 8-bit tiles; `smooth=0` turns it off.
- Size and width need a column: `width-3` stays an error that points to `stroke-3`. `size-` on polygons is an error that names `representative_point()`.
- Labels need a kharita basemap, because they are drawn by MapLibre (Lonboard has no text layer). Above 5,000 labels kharita warns.
- Dashes on points warn and are ignored.

## Tests

`test_phase6.py`, 32 cases: area scaling, negative sizes, width floor, polygon outline widths, legends, dash parsing and layers, label sources, placement and number formatting, labels refused on hosted basemaps, the label limit, the topo theme, and contours traced from a synthetic cone tile (levels, index lines, weights, clipping, interval choice, `preset-topo` widths, zoom choice, smoothing, bad bounds).

## How to verify

```
pip install -e .[dev,demo,terrain]
pytest -q
```

Then run `notebooks/06b_contours_satellite_compare.ipynb` (and `06a` for the 6a features) top to bottom (needs `00` and `00b` data, and internet for the elevation tiles), and fill in the results table.

## 6a check (`notebooks/06a_symbols_labels_contours.ipynb`)

All 9 tests passed. Munieb's notes: contours in F and G were busy, with many tiny loops and jagged edges, unlike published topographic maps; the Red Sea hills (H) gave 662 lines. He asked to see the topographic map next to satellite imagery, and contours combined with the Phase 5 relief designs.

Cause: contours were traced from tiles blurred by only one pixel. At zoom 9 to 10 a tile pixel is 150 to 300 m, and the 90 m source data is resampled into it, so small bumps and resampling steps each became a line. Printed maps generalise contours; 6a did not. Sudan's terrain is not the problem: the Red Sea hills are genuinely rugged, and the noise was in the data and the missing generalisation.

## What was built (6b)

| Change | Where |
| --- | --- |
| Contour generalisation: blur in metres (at least 300 m, or a three-hundredth of the area's width), drop lines shorter than eight blur widths, simplify, then round with two passes of corner cutting | `terrain.py` `blur_metres`, `_clean`, `_chaikin` |
| `detail="low" | "medium" | "high"` on `kh.contours`; `smooth=` now sets the blur in metres, 0 for raw lines; the blur used is in `attrs["smooth"]` | `terrain.py` |
| `basemap-satellite` (imagery only) and `basemap-hybrid` (imagery with roads, borders and labels); relief, elements, data labels and 3D buildings work on both | `basemaps.py` |
| `kh.imagery(year or URL, attribution=)`: Sentinel-2 cloudless years, or your own tile provider | `basemaps.py` |
| `kh.compare(m1, m2, ...)`: maps side by side, panning and zooming together (pulled forward from v0.2) | `maps.py` |

## Decisions (6b)

- Generalisation is measured in metres, not tile pixels, so the same area looks the same at any zoom. Checked by eye on a real 90 m elevation model: medium keeps ridges and valleys and drops about four in five lines.
- Imagery is Sentinel-2 cloudless 2016 by EOX (CC BY-SA 4.0, any use with credit). Newer years are CC BY-NC-SA, so they are opt-in through `kh.imagery(year)`. Esri World Imagery needs an ArcGIS account, so it is not used.
- Satellite maps skip flat building footprints (the imagery shows the roofs) and the ground-colour warning (the ground is a photo).
- `kh.compare` links views through the Python kernel, so linking works in a live notebook, not in exported HTML.

## Known issues

- Labels follow MapLibre collision rules, so some are hidden when crowded; zoom in to see them.
- Contours at the edge of the box are clipped, not closed.
- The pale square near Jebel Marra is a patch of coarser source data in the elevation tiles; generalisation hides its edges but cannot add detail it lacks.
- Imagery stops getting sharper past zoom 14 (10 m Sentinel-2 pixels).
