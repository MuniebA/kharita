"""Synthetic fixtures so tests never depend on real data."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Point, box


@pytest.fixture
def polygons() -> gpd.GeoDataFrame:
    # 10 squares in a row with awkward columns for classification tests
    geoms = [box(30 + i, 15, 31 + i, 16) for i in range(10)]
    data = {
        "name": [f"state {i}" for i in range(10)],
        "pop": [100, 200, 200, 200, 500, 800, 1000, 5000, 20000, np.nan],
        "area": [1.0, 2.0, 0.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        "constant": [7.0] * 10,
        "all_null": [np.nan] * 10,
        "class_id": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        "region": [
            "north", "north", "east", "east", "west", "west", "south", "south", None, "north"
        ],
        "median income": [float(i) for i in range(10)],
    }
    return gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:4326")


@pytest.fixture
def points() -> gpd.GeoDataFrame:
    # 5 points with a size column
    geoms = [Point(32 + i * 0.5, 15.5) for i in range(5)]
    return gpd.GeoDataFrame({"value": [1, 2, 3, 4, 5]}, geometry=geoms, crs="EPSG:4326")


@pytest.fixture
def lines() -> gpd.GeoDataFrame:
    # 3 roads with a category column
    geoms = [LineString([(30, 15 + i), (40, 15 + i)]) for i in range(3)]
    kinds = {"kind": ["primary", "secondary", "track"]}
    return gpd.GeoDataFrame(kinds, geometry=geoms, crs="EPSG:4326")


@pytest.fixture
def mixed(polygons, points) -> gpd.GeoDataFrame:
    # Mixed geometry types plus one null geometry, for row alignment tests
    frame = gpd.GeoDataFrame(
        {"value": list(range(6))},
        geometry=list(polygons.geometry[:3]) + list(points.geometry[:2]) + [None],
        crs="EPSG:4326",
    )
    return frame


@pytest.fixture
def no_crs(polygons) -> gpd.GeoDataFrame:
    # Same squares with the CRS removed
    return polygons.set_crs(None, allow_override=True)
