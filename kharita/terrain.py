"""Contour lines traced from the open Mapzen terrain tiles, ready to style like any other lines."""

import math
from io import BytesIO

import numpy as np

from kharita.basemaps import TERRARIUM_TILES

TILE = 256
MAX_TILES = 16
MAX_ZOOM = 13
TIMEOUT = 30
USER_AGENT = "kharita (https://github.com/MuniebA/kharita)"
INSTALL_HINT = "Contours need the terrain extra: pip install kharita[terrain]"
EARTH = 156543.03392
# Per detail level: the least blur in metres, and the blur as a share of the area's width
DETAIL = {"low": (600.0, 1 / 150), "medium": (300.0, 1 / 300), "high": (150.0, 1 / 600)}
# Lines shorter than this many blur widths are noise: dropped
MIN_LENGTH = 8


def _bbox(where) -> tuple[float, float, float, float]:
    # (west, south, east, north) in degrees from a GeoDataFrame, GeoSeries or a 4-tuple
    if hasattr(where, "total_bounds"):
        if where.crs is None:
            raise ValueError("The data has no CRS; set one with gdf.set_crs(...) first.")
        w, s, e, n = where.to_crs(4326).total_bounds
    else:
        w, s, e, n = (float(v) for v in where)
    if not (-180 <= w < e <= 180 and -85 <= s < n <= 85):
        raise ValueError(f"Bounds must be (west, south, east, north) in degrees, got "
                         f"{(w, s, e, n)}.")
    return w, s, e, n


def _to_pixels(lon: float, lat: float, z: int) -> tuple[float, float]:
    # Web Mercator global pixel coordinates at zoom z
    size = TILE * 2 ** z
    x = (lon + 180) / 360 * size
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * size
    return x, y


def _to_lonlat(px: np.ndarray, py: np.ndarray, z: int) -> tuple[np.ndarray, np.ndarray]:
    # Global pixel coordinates back to degrees
    size = TILE * 2 ** z
    lon = px / size * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * py / size))))
    return lon, lat


def _tile_range(bbox, z: int) -> tuple[int, int, int, int]:
    # First and last tile column and row covering the box
    w, s, e, n = bbox
    x0, y0 = _to_pixels(w, n, z)
    x1, y1 = _to_pixels(e, s, z)
    return int(x0 // TILE), int(y0 // TILE), int(x1 // TILE), int(y1 // TILE)


def auto_zoom(bbox) -> int:
    """The most detailed zoom whose tiles over the box number at most 16."""
    for z in range(MAX_ZOOM, -1, -1):
        tx0, ty0, tx1, ty1 = _tile_range(bbox, z)
        if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) <= MAX_TILES:
            return z
    return 0


def _fetch_tile(z: int, x: int, y: int) -> np.ndarray:
    # One 256 x 256 tile of elevation in metres from its Terrarium PNG
    import urllib.request

    try:
        from PIL import Image
    except ImportError:
        raise ImportError(INSTALL_HINT) from None
    url = TERRARIUM_TILES.format(z=z, x=x, y=y)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        rgb = np.asarray(Image.open(BytesIO(response.read())).convert("RGB"), dtype=np.float32)
    return rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768


def elevation_grid(where, zoom: int | None = None):
    """Elevation in metres over the box, plus the pixel offset and zoom it was read at."""
    bbox = _bbox(where)
    z = auto_zoom(bbox) if zoom is None else zoom
    tx0, ty0, tx1, ty1 = _tile_range(bbox, z)
    if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 64:
        raise ValueError(f"zoom {z} needs {(tx1 - tx0 + 1) * (ty1 - ty0 + 1)} tiles here; "
                         "use a lower zoom or a smaller area.")
    rows = [np.hstack([_fetch_tile(z, x, y) for x in range(tx0, tx1 + 1)])
            for y in range(ty0, ty1 + 1)]
    return np.vstack(rows), tx0 * TILE, ty0 * TILE, z


def _smooth(grid: np.ndarray, sigma: float) -> np.ndarray:
    # Separable Gaussian blur; edges repeat so contours do not bend at the border
    radius = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    k /= k.sum()
    padded = np.pad(grid, radius, mode="edge")
    rows = np.apply_along_axis(lambda r: np.convolve(r, k, mode="valid"), 1, padded)
    return np.apply_along_axis(lambda c: np.convolve(c, k, mode="valid"), 0, rows)


def metres_per_pixel(lat: float, z: int) -> float:
    """Ground size of one tile pixel at a latitude and zoom."""
    return EARTH * math.cos(math.radians(lat)) / 2 ** z


def blur_metres(bbox, detail: str) -> float:
    """How far to blur the elevation before tracing: wider areas and lower detail blur more."""
    if detail not in DETAIL:
        raise ValueError(f"detail must be one of {', '.join(DETAIL)}, got '{detail}'.")
    w, s, e, n = bbox
    width = (e - w) * 111320 * math.cos(math.radians((s + n) / 2))
    floor, share = DETAIL[detail]
    return max(floor, width * share)


def _chaikin(xy: np.ndarray, closed: bool, rounds: int = 2) -> np.ndarray:
    # Corner cutting: each round replaces every corner with two points a quarter in
    for _ in range(rounds):
        p = xy[:-1]
        q = np.roll(p, -1, axis=0) if closed else xy[1:]
        cut = np.empty((2 * len(p), 2))
        cut[0::2] = 0.75 * p + 0.25 * q
        cut[1::2] = 0.25 * p + 0.75 * q
        xy = np.vstack([cut, cut[:1]]) if closed else np.vstack([xy[:1], cut, xy[-1:]])
    return xy


def _clean(line: np.ndarray, min_length: float, tolerance: float) -> np.ndarray | None:
    """A traced line in pixels, simplified and rounded; None when it is too short to keep."""
    from shapely.geometry import LineString

    if len(line) < 2 or np.hypot(*np.diff(line, axis=0).T).sum() < min_length:
        return None
    closed = bool(np.allclose(line[0], line[-1]))
    xy = np.asarray(LineString(line).simplify(tolerance).coords)
    if closed and len(xy) < 4:
        return None
    return _chaikin(xy, closed)


def nice_interval(span: float, lines: int = 20) -> float:
    """A round contour interval giving about `lines` levels over the span."""
    if span <= 0:
        return 1.0
    raw = span / lines
    base = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if m * base >= raw:
            return m * base
    return 10 * base


def contours(where, interval: float | None = None, zoom: int | None = None,
             index_every: int = 5, detail: str = "medium", smooth: float | None = None,
             below_sea: bool = False):
    """Contour lines over an area: a GeoDataFrame with elevation, index and weight columns.

    where is a GeoDataFrame, GeoSeries or (west, south, east, north). Every index_every-th line
    is an index contour (weight 2, the rest 1), the thicker labelled line of a topographic map.
    detail is low, medium or high: how much small bumps and wiggles are kept. smooth sets the
    blur in metres directly; 0 turns generalisation off.
    """
    import geopandas as gpd
    from shapely.geometry import LineString

    try:
        from contourpy import contour_generator
    except ImportError:
        raise ImportError(INSTALL_HINT) from None
    bbox = _bbox(where)
    grid, x_off, y_off, z = elevation_grid(bbox, zoom)
    # Trace only the window over the box, with a margin so lines run to its edge
    w, s, e, n = bbox
    px0, py0 = _to_pixels(w, n, z)
    px1, py1 = _to_pixels(e, s, z)
    c0, r0 = max(int(px0 - x_off) - 2, 0), max(int(py0 - y_off) - 2, 0)
    c1 = min(int(px1 - x_off) + 3, grid.shape[1])
    r1 = min(int(py1 - y_off) + 3, grid.shape[0])
    window = grid[r0:r1, c0:c1].astype(float)
    pixel = metres_per_pixel((s + n) / 2, z)
    blur = blur_metres(bbox, detail) if smooth is None else smooth
    sigma = blur / pixel
    if sigma > 0:
        window = _smooth(window, max(sigma, 0.5))
    lo, hi = float(np.nanmin(window)), float(np.nanmax(window))
    if not below_sea:
        lo = max(lo, 0.0)
    step = interval or nice_interval(hi - lo)
    levels = np.arange(math.ceil(lo / step) * step, hi, step)
    levels = levels[levels > 0] if not below_sea else levels
    gen = contour_generator(z=window)
    rows = []
    min_length = MIN_LENGTH * sigma
    tolerance = min(max(sigma / 4, 0.2), 1.5) if sigma > 0 else 0.0
    for level in levels:
        for raw in gen.lines(float(level)):
            line = _clean(raw, min_length, tolerance) if sigma > 0 else raw
            if line is None or len(line) < 2:
                continue
            lon, lat = _to_lonlat(line[:, 0] + c0 + x_off + 0.5, line[:, 1] + r0 + y_off + 0.5, z)
            rows.append((float(level), LineString(np.column_stack([lon, lat]))))
    out = gpd.GeoDataFrame({"elevation": [r[0] for r in rows]},
                           geometry=[r[1] for r in rows], crs=4326)
    out["geometry"] = out.geometry.clip_by_rect(w, s, e, n)
    out = out[~out.geometry.is_empty].reset_index(drop=True)
    index_step = step * index_every
    out["index"] = np.isclose(np.mod(out["elevation"], index_step), 0) | np.isclose(
        np.mod(out["elevation"], index_step), index_step)
    out["weight"] = np.where(out["index"], 2, 1)
    out.attrs.update({"interval": step, "zoom": z, "smooth": round(blur), "detail": detail})
    return out
