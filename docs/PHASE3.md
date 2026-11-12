# Phase 3: Data binding

**Status:** done, 12 Nov 2026. 454 tests passing at the end of the phase.

## Goal

Turn bound columns into colour arrays, heights and a `Scale` the legend is drawn from. This is where silent wrong maps come from, so the tests are the main deliverable.

## What was built

| File | Does |
| --- | --- |
| `kharita/classify.py` | `Scale`; quantiles, equal interval, explicit breaks, diverging (7 classes), categorical (top N plus "other"); number formatting |
| `kharita/binder.py` | `bind(gdf, style)`: evaluates expressions, detects types, picks defaults, builds colour (n, 4) uint8 and height arrays |
| `notebooks/03_data_binding.ipynb` | Scales, three schemes on the same data, heights, data warnings |

## Decisions

- Classification is pure numpy; no mapclassify dependency.
- Defaults: numeric columns get `ramp-viridis scheme-q5`, text columns `ramp-set2 scheme-cat`.
- `scheme-div` always uses 7 symmetric classes with a neutral middle.
- Explicit breaks print with the decimals the user typed (`10`, not `10.0`).
- Values are always copied, because pandas can return views or read-only arrays that would otherwise let kharita change the user's table.
- Division by zero and infinities become missing values, counted in the legend.
- Numbers stored as text are converted with a warning; dates are refused.
- Whole-number columns with 12 or fewer distinct values warn that `scheme-cat` may be meant.
- Heights default to a tenth of the data's extent, computed from the bounding-box corners only.

## Tests

`test_classify`, `test_binder`. Covered: ties that reduce the class count, k above the number of distinct values, constant and all-null columns, division by zero, numbers as text, more than 12 categories, row order after shuffling, the user's table unchanged, 1 million rows classified and coloured in under 3 seconds.

## How to verify

```
pytest -q tests/test_classify.py tests/test_binder.py
```

Then run `notebooks/03_data_binding.ipynb`.

## Known issues

- Extruded polygons are lit by deck.gl, which darkens colours and makes the palest class hard to see. Lonboard does not expose `material` to turn lighting off. Workaround for now: viridis plus wireframe. Phase 5 trims the palest stops on extruded layers.
