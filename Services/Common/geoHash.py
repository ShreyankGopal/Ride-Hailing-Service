"""
Minimal geohash utility.
Used only to convert (lat, lon) -> region_id.
No expansion, no neighbors, no extra logic.
"""

import geohash2

# 7 ≈ ~150m x 150m (good enough for city-level matching)
DEFAULT_PRECISION = 7


def get_region(lat: float, lon: float, precision: int = DEFAULT_PRECISION) -> str:
    """
    Return geohash region string for given latitude and longitude.

    Example:
        get_region(12.9716, 77.5946) -> "dr5ru7k"
    """
    return geohash2.encode(lat, lon, precision)