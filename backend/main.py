"""
SafeRoute AI - Main FastAPI Application.
Crime data is loaded from the local CSV cache; no database is used.
"""
import logging
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config import (
    DEFAULT_CRIME_BUFFER_METERS,
    DEFAULT_CRIME_WEIGHTS,
    DEFAULT_LAMBDA,
    MAX_DETOUR_RATIO,
    STUDY_AREA_CENTER_LAT,
    STUDY_AREA_CENTER_LON,
    STUDY_AREA_NAME,
    STUDY_AREA_RADIUS_METERS,
)
from backend.data_ingestion import fetch_chicago_crime_records
from backend.ml_engine import get_ml_engine
from backend.models import (
    AnalyticsSummary,
    Coordinate,
    HotspotPoint,
    RouteComparisonResponse,
    RouteRequest,
    StudyAreaInfo,
)
from backend.routing_engine import get_routing_engine
from backend.spatial_index import CrimeSpatialIndex
from backend.spatial_utils import is_within_study_area

logger = logging.getLogger("saferoute.api")
logging.basicConfig(level=logging.INFO)

global_spatial_index: Optional[CrimeSpatialIndex] = None
global_crime_records: List[Dict[str, Any]] = []
global_data_source = "Uninitialized"
services_initialized = False


def _record_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            return None
    return None


def _initialize_services(records: List[Dict[str, Any]], source: str) -> None:
    global global_spatial_index, global_crime_records, global_data_source, services_initialized

    normalized = []
    for record in records:
        item = dict(record)
        item["date"] = _record_datetime(item.get("date"))
        normalized.append(item)
    normalized.sort(key=lambda item: item.get("date") or datetime.min, reverse=True)

    logger.info("Building in-memory crime services with %s CSV records...", len(normalized))
    global_crime_records = normalized
    global_data_source = source
    global_spatial_index = CrimeSpatialIndex(normalized)
    get_routing_engine().update_spatial_index(global_spatial_index)
    get_ml_engine().train_from_incidents(normalized)
    services_initialized = True
    logger.info("SafeRoute AI CSV-backed initialization complete.")


def load_and_initialize_system() -> None:
    """Loads the CSV cache and initializes spatial, routing, and ML services."""
    logger.info("Initializing SafeRoute AI from the local CSV dataset...")
    records, source = fetch_chicago_crime_records(use_live_api=False)
    _initialize_services(records, source)


def _ensure_initialized() -> None:
    if not services_initialized:
        load_and_initialize_system()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_and_initialize_system()
    yield


app = FastAPI(
    title="SafeRoute AI - Crime-Aware Safe Navigation System",
    description="Intelligent pedestrian navigation balancing distance and historical crime exposure in Chicago.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    _ensure_initialized()
    routing_engine = get_routing_engine()
    ml_engine = get_ml_engine()
    return {
        "status": "HEALTHY",
        "timestamp": datetime.now().isoformat(),
        "data_store": "LOCAL_CSV",
        "crime_incident_count": len(global_crime_records),
        "road_network": {
            "nodes": routing_engine.network.graph.number_of_nodes(),
            "edges": routing_engine.network.graph.number_of_edges(),
            "status": "OPERATIONAL",
        },
        "spatial_index": "LOADED" if global_spatial_index else "OFFLINE",
        "data_source": global_data_source,
        "ml_model_status": ml_engine.metrics.get("status", "UNINITIALIZED"),
    }


@app.get("/api/study-area", response_model=StudyAreaInfo)
def get_study_area():
    _ensure_initialized()
    dates = [record["date"] for record in global_crime_records if record.get("date")]
    categories = {record["primary_type"] for record in global_crime_records if record.get("primary_type")}
    return StudyAreaInfo(
        name=STUDY_AREA_NAME,
        center=Coordinate(lat=STUDY_AREA_CENTER_LAT, lon=STUDY_AREA_CENTER_LON),
        radius_meters=STUDY_AREA_RADIUS_METERS,
        default_crime_buffer_meters=DEFAULT_CRIME_BUFFER_METERS,
        crime_incident_count=len(global_crime_records),
        date_range_start=min(dates) if dates else None,
        date_range_end=max(dates) if dates else None,
        categories=sorted(categories),
        category_weights=DEFAULT_CRIME_WEIGHTS,
    )


@app.get("/api/crimes")
def get_crimes(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(400, ge=1, le=2500),
    offset: int = Query(0, ge=0),
):
    _ensure_initialized()
    filtered = global_crime_records
    if category and category != "ALL":
        requested_category = category.upper().strip()
        filtered = [r for r in filtered if r.get("primary_type") == requested_category]

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            filtered = [r for r in filtered if r.get("date") and r["date"] >= start]
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            filtered = [r for r in filtered if r.get("date") and r["date"] <= end]
        except ValueError:
            pass

    items = [
        {
            "id": r.get("id", r.get("incident_id")),
            "incident_id": r.get("incident_id"),
            "case_number": r.get("case_number"),
            "date": r["date"].isoformat() if r.get("date") else None,
            "primary_type": r.get("primary_type"),
            "description": r.get("description"),
            "location_description": r.get("location_description"),
            "arrest": r.get("arrest", False),
            "domestic": r.get("domestic", False),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "severity_weight": r.get("severity_weight"),
            "distance_from_center_m": r.get("distance_from_center_m"),
        }
        for r in filtered[offset:offset + limit]
    ]
    return {
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "study_area_radius_meters": STUDY_AREA_RADIUS_METERS,
        "data": items,
    }


@app.get("/api/crime-hotspots", response_model=List[HotspotPoint])
def get_crime_hotspots(grid_size_meters: float = Query(350.0, ge=100.0, le=1000.0)):
    _ensure_initialized()
    if not global_spatial_index:
        return []
    hotspots = global_spatial_index.generate_hotspots(grid_size_meters=grid_size_meters)
    return [
        HotspotPoint(
            lat=hotspot["lat"],
            lon=hotspot["lon"],
            intensity=hotspot["intensity"],
            count=hotspot["count"],
            dominant_crime=hotspot["dominant_crime"],
        )
        for hotspot in hotspots
    ]


@app.get("/api/analytics/summary", response_model=AnalyticsSummary)
def get_analytics_summary():
    _ensure_initialized()
    total = len(global_crime_records)
    violent_types = {
        "HOMICIDE", "CRIMINAL SEXUAL ASSAULT", "ROBBERY",
        "ASSAULT", "BATTERY", "WEAPONS VIOLATION",
    }
    property_types = {
        "THEFT", "BURGLARY", "MOTOR VEHICLE THEFT", "ARSON", "CRIMINAL DAMAGE",
    }
    categories = Counter(record.get("primary_type") for record in global_crime_records)
    hourly_buckets = [0] * 24
    dow_buckets = [0] * 7
    monthly_counts: Counter = Counter()
    arrest_count = 0

    for record in global_crime_records:
        if record.get("arrest"):
            arrest_count += 1
        date = record.get("date")
        if date:
            hourly_buckets[date.hour] += 1
            dow_buckets[date.weekday()] += 1
            monthly_counts[date.strftime("%Y-%m")] += 1

    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return AnalyticsSummary(
        total_crimes=total,
        violent_crimes_pct=round(
            sum(categories.get(category, 0) for category in violent_types) / total * 100, 1
        ) if total else 0.0,
        property_crimes_pct=round(
            sum(categories.get(category, 0) for category in property_types) / total * 100, 1
        ) if total else 0.0,
        arrest_rate_pct=round(arrest_count / total * 100, 1) if total else 0.0,
        top_categories=[
            {"category": category, "count": count}
            for category, count in categories.most_common(10)
            if category
        ],
        monthly_trend=[
            {"month": month, "count": monthly_counts[month]}
            for month in sorted(monthly_counts)[-12:]
        ],
        hourly_distribution=[
            {"hour": f"{hour:02d}:00", "count": hourly_buckets[hour]}
            for hour in range(24)
        ],
        day_of_week_distribution=[
            {"day": dow_names[day], "count": dow_buckets[day]}
            for day in range(7)
        ],
    )


@app.post("/api/routes/compare", response_model=RouteComparisonResponse)
def compare_routes(req: RouteRequest):
    _ensure_initialized()
    start_inside, start_dist = is_within_study_area(
        req.start.lat,
        req.start.lon,
        STUDY_AREA_CENTER_LAT,
        STUDY_AREA_CENTER_LON,
        STUDY_AREA_RADIUS_METERS,
    )
    if not start_inside:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Selected start location ({req.start.lat:.4f}, {req.start.lon:.4f}) is {int(start_dist)}m from center, "
                f"which exceeds the {int(STUDY_AREA_RADIUS_METERS)}m study boundary of Chicago. "
                "Please choose an origin point within the active study circle."
            ),
        )

    dest_inside, dest_dist = is_within_study_area(
        req.destination.lat,
        req.destination.lon,
        STUDY_AREA_CENTER_LAT,
        STUDY_AREA_CENTER_LON,
        STUDY_AREA_RADIUS_METERS,
    )
    if not dest_inside:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Selected destination ({req.destination.lat:.4f}, {req.destination.lon:.4f}) is {int(dest_dist)}m from center, "
                f"which exceeds the {int(STUDY_AREA_RADIUS_METERS)}m study boundary of Chicago. "
                "Please choose a destination within the active study circle."
            ),
        )

    engine_inst = get_routing_engine()
    try:
        result = engine_inst.compute_dual_routes(
            start_lat=req.start.lat,
            start_lon=req.start.lon,
            dest_lat=req.destination.lat,
            dest_lon=req.destination.lon,
            risk_lambda=req.risk_weight_lambda if req.risk_weight_lambda is not None else DEFAULT_LAMBDA,
            max_detour_ratio=req.max_detour_ratio if req.max_detour_ratio is not None else MAX_DETOUR_RATIO,
            buffer_meters=req.buffer_meters if req.buffer_meters is not None else DEFAULT_CRIME_BUFFER_METERS,
        )
    except Exception as error:
        logger.error("Routing computation error: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error

    return RouteComparisonResponse(
        study_area_center=Coordinate(lat=STUDY_AREA_CENTER_LAT, lon=STUDY_AREA_CENTER_LON),
        study_area_radius_meters=STUDY_AREA_RADIUS_METERS,
        shortest_route=result["shortest_route"],
        crime_aware_route=result["crime_aware_route"],
        detour_percentage=result["detour_percentage"],
        risk_reduction_percentage=result["risk_reduction_percentage"],
        explanation=result["explanation"],
        disclaimer=result["disclaimer"],
        uncertainty_warning=result.get("uncertainty_warning"),
    )


@app.get("/api/model/metrics")
def get_ml_metrics():
    _ensure_initialized()
    return get_ml_engine().metrics


@app.post("/api/data/refresh")
def refresh_data():
    global global_data_source
    try:
        records, source = fetch_chicago_crime_records(use_live_api=True)
        if not source.startswith("Live Chicago Data Portal"):
            raise HTTPException(
                status_code=503,
                detail="Chicago Data Portal refresh failed; the existing CSV dataset was left unchanged.",
            )
        _initialize_services(records, source)
        return {
            "status": "SUCCESS",
            "message": f"Successfully updated CSV dataset from {source}.",
            "total_incidents": len(global_crime_records),
            "source": global_data_source,
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Data refresh failed: %s", error)
        raise HTTPException(status_code=500, detail=f"Data refresh failed: {error}") from error
