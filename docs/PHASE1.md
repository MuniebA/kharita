# Phase 1: Spike

**Status:** done, 12 Nov 2026. Gate passed.

## Goal

Prove the riskiest assumptions with a throwaway notebook before writing library code. The gate: the legend must survive `to_html()` export. Tooltips and extrusion went into v0.1 only if they worked here.

## What was built

`notebooks/01_spike.ipynb`: plain Lonboard and hand-written HTML, no kharita code. Eight questions, each in its own cell.

## Results (VS Code on Windows)

| Question | Result | Decision for kharita |
| --- | --- | --- |
| 1 px outlines | Works with `line_width_units="pixels"` | The adapter always sets pixel units |
| Hover highlight | Works | `highlight-<colour>` stays in v0.1 |
| Legend over the map in a notebook | Works (CSS grid overlay); the map still drags | Default legend placement |
| Legend beside the map | Works | Kept as fallback |
| Legend in exported HTML (gate) | Works: full-window map, legend pinned bottom-right | Export injects the legend |
| Keyless basemap | OpenFreeMap positron, bright and liberty all load | `basemap-light` uses positron |
| Tooltip with chosen columns | Works, but shows raw floats | `tooltip-[cols]` with number formatting |
| Extrusion with tilt | Works | `extrude-[col]`, off by default |
| 1 million points | 0.99 s frame, 0.10 s classify, 1.09 s layer | Fast enough |

## Decisions

- The side panel shows nothing because only geometry is sent to Lonboard, so kharita turns it off and uses `tooltip-[cols]` instead.
- The legend is self-contained HTML with inline styles, so the same markup works in the notebook and in export.
- No dark keyless style was tested; `basemap-dark` uses CARTO Dark Matter until the Phase 5 spike.

## Tests

None; the spike is throwaway by design. Its answers became the Phase 4 tests.

## How to verify

Run `notebooks/01_spike.ipynb` top to bottom. Cell Q4 opens the exported page in your browser; the legend must be visible there.

## Known issues

- The overlay legend was only tested in VS Code. Re-test in JupyterLab and Colab in Phase 6.
- Lonboard has no text layer, so map labels must come from the basemap.
