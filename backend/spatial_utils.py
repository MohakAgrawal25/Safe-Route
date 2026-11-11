"""
Geospatial utility functions for SafeRoute AI.
Provides fast Haversine distance, bounding box calculations, and study area boundary validation.
"""
import math
from typing import Tuple, List

EARTH_RADIUS_METERS = 6371000.0  # Earth mean radius in meters

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in meters
    using the Haversine formula.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_METERS * c


def is_within_study_area(
    lat: float,
    lon: float,
    center_lat: float,
    center_lon: float,
    radius_meters: float
) -> Tuple[bool, float]:
    """
    Validates if a coordinate is strictly within the study area radius.
    Returns (is_inside, distance_meters).
    """
    dist = haversine_distance(lat, lon, center_lat, center_lon)
    return (dist <= radius_meters, dist)


def get_bounding_box(
    center_lat: float,
    center_lon: float,
    radius_meters: float
) -> Tuple[float, float, float, float]:
    """
    Calculates latitude and longitude bounding box for API query clipping.
    Returns (min_lat, min_lon, max_lat, max_lon).
    """
    # 1 degree latitude ~ 111,320 meters
    delta_lat = radius_meters / 111320.0
    # 1 degree longitude ~ 111,320 * cos(lat) meters
    delta_lon = radius_meters / (111320.0 * math.cos(math.radians(center_lat)))

    return (
        center_lat - delta_lat,
        center_lon - delta_lon,
        center_lat + delta_lat,
        center_lon + delta_lon
    )


def point_to_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float
) -> float:
    """
    Computes minimum distance (in approximate meters) from point (px, py) to line segment (x1, y1)-(x2, y2).
    Coordinates are in degrees (lat, lon), converted to local metric projection.
    """
    # Local equirectangular projection centered at py
    lat_rad = math.radians(py)
    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * math.cos(lat_rad)

    # Convert coordinates to local metric offsets (x=easting/lon, y=northing/lat)
    p_x = (py - y1) * m_per_deg_lon
    p_y = (px - x1) * m_per_deg_lat

    seg_dx = (y2 - y1) * m_per_deg_lon
    seg_dy = (x2 - x1) * m_per_deg_lat

    seg_len_sq = seg_dx * seg_dx + seg_dy * seg_dy
    if seg_len_sq == 0.0:
        return math.sqrt(p_x * p_x + p_y * p_y)

    # Project point onto segment: t = dot(p, seg) / |seg|^2
    t = max(0.0, min(1.0, (p_x * seg_dx + p_y * seg_dy) / seg_len_sq))

    proj_x = t * seg_dx
    proj_y = t * seg_dy

    dist_x = p_x - proj_x
    dist_y = p_y - proj_y

    return math.sqrt(dist_x * dist_x + dist_y * dist_y)
