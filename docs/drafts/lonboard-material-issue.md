# Draft issue for developmentseed/lonboard

**Title:** Expose `material` on PolygonLayer and SolidPolygonLayer to turn off 3D lighting

**Body:**

deck.gl's `SolidPolygonLayer` (and so `PolygonLayer`) has a `material` prop. Setting `material: false` turns off lighting for extruded polygons, so their colours render exactly as given.

Lonboard 0.17.0 does not expose this prop. For extruded choropleths this matters: lighting darkens every face, and pale classes turn grey, so the map no longer matches its legend.

**Request:** a `material` trait on `PolygonLayer` and `SolidPolygonLayer`, accepting `False` or a dict passed through to deck.gl (`ambient`, `diffuse`, `shininess`, `specularColor`).

**Minimal example:**

```python
import geopandas as gpd
from lonboard import Map, PolygonLayer

gdf = gpd.read_file("states.gpkg")
layer = PolygonLayer.from_geopandas(
    gdf,
    extruded=True,
    get_elevation=gdf["pop"] / 10,
    get_fill_color=[255, 255, 204],  # renders grey-yellow, not pale yellow
)
Map(layer)
```

**Context:** we build kharita, a style-string layer on top of Lonboard. As a workaround it currently drops near-white ramp colours on extruded layers.
