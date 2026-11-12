# Phase 4: Rendering

**Status:** done, 12 Nov 2026. 497 tests passing at the end of the phase.

## Goal

Connect the compiled style to Lonboard and draw the legend, in the notebook and in exported HTML. This is the only phase that imports Lonboard.

## What was built

| File | Does |
| --- | --- |
| `kharita/adapter.py` | `layer(gdf, style)`: native Lonboard layers per geometry type; CRS guard; only named columns sent |
| `kharita/legend.py` | Legend card HTML: class rows with counts, "No data" row, title, `fmt`, custom labels, note; light and dark |
| `kharita/maps.py` | `kh.Map().add().to_html()`, `kh.map`, `kh.legend`; legend overlay in the notebook, injected in export |
| `notebooks/04_maps.ipynb` | Seven maps: choropleth, breaks and labels, categories, dark 3D, two layers, export, escape hatch |

Public API: `kh.map`, `kh.Map`, `kh.layer`, `kh.legend`.

## Decisions

- `basemap-light` is OpenFreeMap positron (keyless). `basemap-dark` is CARTO Dark Matter until Phase 5 finds a keyless dark style.
- Data without a CRS raises with the `set_crs` fix in the message; other CRSs are reprojected to EPSG:4326.
- Mixed geometry tables are split into one layer per type, with colours kept aligned to rows.
- Tooltip columns are sent as text with thousands separators, fixing the raw floats seen in the spike.
- Extruded layers turn on wireframe edges and tilt the camera to pitch 45, bearing -10.
- A preset's scheme gives way to a typed categorical ramp and to text data; found when `preset-choropleth fill-[size] ramp-set2` failed in the demo notebook.
- Legend options are validated at `add()`, so a bad `fmt` fails there, not at display.

## Tests

`test_adapter`, `test_legend`, `test_maps`. Layer properties are asserted in Python with no browser: units, colours per row, null and mixed geometry alignment, the user's table unchanged, legend markup in the exported page.

## How to verify

```
pytest -q tests/test_adapter.py tests/test_legend.py tests/test_maps.py
```

Then run `notebooks/04_maps.ipynb`. The export cell opens the page in your browser.

## Known issues

- Fixed in Phase 5: the bottom-right legend's last row sat under Lonboard's corner button. The bottom margin is now 72px in the notebook and in export.
- 3D lighting still shifts colours; see Phase 3.
