"""
Unit tests for geographic boundary enforcement and Haversine distance.
"""
from backend.spatial_utils import haversine_distance, is_within_study_area, get_bounding_box
from backend.config import STUDY_AREA_CENTER_LAT, STUDY_AREA_CENTER_LON, STUDY_AREA_RADIUS_METERS

def test_haversine_same_point():
    dist = haversine_distance(41.8781, -87.6298, 41.8781, -87.6298)
    assert dist == 0.0

def test_haversine_known_distance():
    # Distance between Millennium Park (41.8826, -87.6233) and Willis Tower (41.8789, -87.6359)
    # is roughly 1.1 km to 1.3 km
    dist = haversine_distance(41.8826, -87.6233, 41.8789, -87.6359)
    assert 1000.0 < dist < 1400.0

def test_study_area_boundary_inside():
    # Point ~500m from center
    is_inside, dist = is_within_study_area(
        STUDY_AREA_CENTER_LAT + 0.003,
        STUDY_AREA_CENTER_LON + 0.003,
        STUDY_AREA_CENTER_LAT,
        STUDY_AREA_CENTER_LON,
        STUDY_AREA_RADIUS_METERS
    )
    assert is_inside is True
    assert dist < STUDY_AREA_RADIUS_METERS

def test_study_area_boundary_outside():
    # Chicago O'Hare Airport (41.9742, -87.9073) is ~25 km away, strictly outside 5 km study area
    is_inside, dist = is_within_study_area(
        41.9742,
        -87.9073,
        STUDY_AREA_CENTER_LAT,
        STUDY_AREA_CENTER_LON,
        STUDY_AREA_RADIUS_METERS
    )
    assert is_inside is False
    assert dist > 20000.0

def test_bounding_box_coverage():
    min_lat, min_lon, max_lat, max_lon = get_bounding_box(
        STUDY_AREA_CENTER_LAT, STUDY_AREA_CENTER_LON, STUDY_AREA_RADIUS_METERS
    )
    assert min_lat < STUDY_AREA_CENTER_LAT < max_lat
    assert min_lon < STUDY_AREA_CENTER_LON < max_lon
