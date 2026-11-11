# kharita

Classified, legended [Lonboard](https://github.com/developmentseed/lonboard) maps from one style string.

```python
import kharita as kh

kh.layer(states, "fill-[pop/area] ramp-ylorrd scheme-q5 stroke-1 stroke-white")
```

**Status:** pre-alpha, under active development. Nothing works yet beyond the project skeleton.

## Install for development

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## Not for

Rasters, feature labels, or print layouts. Use Cartopy, matplotlib or QGIS for those.

## Credits

- Palette and ramp sources: see [`kharita/data/NOTICE.md`](kharita/data/NOTICE.md).
- Demo data: see [`data/README.md`](data/README.md).

## Licence

MIT
