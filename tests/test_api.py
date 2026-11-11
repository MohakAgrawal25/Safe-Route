"""
API integration tests for SafeRoute AI endpoints.
"""
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import (
    STUDY_AREA_CENTER_LAT,
    STUDY_AREA_CENTER_LON,
    STUDY_AREA_RADIUS_METERS,
)

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["data_store"] == "LOCAL_CSV"
    assert data["road_network"]["nodes"] > 200

def test_study_area_endpoint():
    res = client.get("/api/study-area")
    assert res.status_code == 200
    data = res.json()
    assert data["radius_meters"] == STUDY_AREA_RADIUS_METERS
    assert "center" in data
    assert data["center"]["lat"] == STUDY_AREA_CENTER_LAT
    assert "categories" in data
    assert len(data["categories"]) > 0

def test_crimes_endpoint():
    res = client.get("/api/crimes?limit=20")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert "total" in data

def test_analytics_summary():
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_crimes" in data
    assert "violent_crimes_pct" in data
    assert "top_categories" in data

def test_routes_compare_valid():
    payload = {
        "start": {"lat": 41.8820, "lon": -87.6278},
        "destination": {"lat": 41.8741, "lon": -87.6278},
        "buffer_meters": 75.0,
        "risk_weight_lambda": 2.5,
        "max_detour_ratio": 0.30
    }
    res = client.post("/api/routes/compare", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "shortest_route" in data
    assert "crime_aware_route" in data
    assert "explanation" in data
    assert "disclaimer" in data
    assert len(data["shortest_route"]["coordinates"]) > 1
    assert len(data["crime_aware_route"]["coordinates"]) > 1

def test_routes_compare_out_of_bounds_rejected():
    # Coordinate far away in Evanston / O'Hare outside study circle
    payload = {
        "start": {"lat": 42.0451, "lon": -87.6877},
        "destination": {"lat": 41.8781, "lon": -87.6298}
    }
    res = client.post("/api/routes/compare", json=payload)
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert f"exceeds the {int(STUDY_AREA_RADIUS_METERS)}m study boundary" in detail

def test_ml_metrics_endpoint():
    res = client.get("/api/model/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "disclaimer" in data
