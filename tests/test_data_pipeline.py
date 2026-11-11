"""
Unit tests for crime data cleaning, category weighting, and deduplication.
"""
from backend.data_ingestion import _clean_and_filter_records
from backend.config import STUDY_AREA_CENTER_LAT, STUDY_AREA_CENTER_LON
from backend.spatial_index import CrimeSpatialIndex

def test_clean_and_filter_records():
    raw_data = [
        {
            # Valid record near center
            "id": "1001",
            "case_number": "JC001",
            "date": "2026-10-01T12:00:00.000",
            "primary_type": "ROBBERY",
            "latitude": str(STUDY_AREA_CENTER_LAT),
            "longitude": str(STUDY_AREA_CENTER_LON)
        },
        {
            # Duplicate ID (should be dropped)
            "id": "1001",
            "case_number": "JC001",
            "date": "2026-10-01T12:00:00.000",
            "primary_type": "ROBBERY",
            "latitude": str(STUDY_AREA_CENTER_LAT),
            "longitude": str(STUDY_AREA_CENTER_LON)
        },
        {
            # Missing coordinates (should be dropped)
            "id": "1002",
            "case_number": "JC002",
            "date": "2026-10-02T12:00:00.000",
            "primary_type": "THEFT",
            "latitude": None,
            "longitude": None
        },
        {
            # Out of bounds (>5km away, should be dropped)
            "id": "1003",
            "case_number": "JC003",
            "date": "2026-10-03T12:00:00.000",
            "primary_type": "BATTERY",
            "latitude": "41.5000",
            "longitude": "-87.6000"
        }
    ]

    cleaned = _clean_and_filter_records(raw_data)
    assert len(cleaned) == 1
    assert cleaned[0]["incident_id"] == "1001"
    assert cleaned[0]["primary_type"] == "ROBBERY"
    assert cleaned[0]["severity_weight"] == 0.85


def test_hotspots_only_include_incidents_inside_study_circle():
    inside_incidents = [
        {"latitude": STUDY_AREA_CENTER_LAT, "longitude": STUDY_AREA_CENTER_LON, "severity_weight": 0.7, "primary_type": "BATTERY"},
        {"latitude": STUDY_AREA_CENTER_LAT + 0.0001, "longitude": STUDY_AREA_CENTER_LON, "severity_weight": 0.35, "primary_type": "THEFT"},
    ]
    index = CrimeSpatialIndex(inside_incidents)

    hotspots = index.generate_hotspots(grid_size_meters=350)

    assert len(hotspots) == 1
    assert hotspots[0]["count"] == 2

    outside_lat = STUDY_AREA_CENTER_LAT + 0.08
    outside_incidents = [
        {"latitude": outside_lat, "longitude": STUDY_AREA_CENTER_LON, "severity_weight": 0.7, "primary_type": "BATTERY"},
        {"latitude": outside_lat + 0.0001, "longitude": STUDY_AREA_CENTER_LON, "severity_weight": 0.35, "primary_type": "THEFT"},
    ]
    outside_index = CrimeSpatialIndex(outside_incidents)

    assert outside_index.generate_hotspots(grid_size_meters=350) == []
