"""
Data models and schemas for SafeRoute AI.
Defines Pydantic schemas for API validation.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
# --- Pydantic Request & Response Schemas ---

class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")


class RouteRequest(BaseModel):
    start: Coordinate
    destination: Coordinate
    buffer_meters: Optional[float] = Field(default=75.0, ge=20.0, le=300.0)
    risk_weight_lambda: Optional[float] = Field(default=2.5, ge=0.0, le=10.0)
    max_detour_ratio: Optional[float] = Field(default=0.30, ge=0.05, le=1.0)


class CrimeIncidentSchema(BaseModel):
    id: int
    incident_id: str
    case_number: Optional[str]
    date: datetime
    primary_type: str
    description: Optional[str]
    location_description: Optional[str]
    arrest: bool
    domestic: bool
    latitude: float
    longitude: float
    severity_weight: float

    model_config = {"from_attributes": True}


class RouteSegmentDetail(BaseModel):
    from_node: str
    to_node: str
    length_m: float
    risk_score: float
    incident_count: int
    dominant_category: Optional[str] = None


class RouteComparisonResult(BaseModel):
    route_type: str  # "shortest" or "crime_aware"
    distance_meters: float
    duration_seconds: float
    walking_time_formatted: str
    historical_risk_index: float  # Normalized 0 - 100
    incident_exposure_count: int
    top_categories_along_route: Dict[str, int]
    coordinates: List[List[float]]  # [[lat, lon], ...]
    segments: Optional[List[RouteSegmentDetail]] = None


class RouteComparisonResponse(BaseModel):
    study_area_center: Coordinate
    study_area_radius_meters: float
    shortest_route: RouteComparisonResult
    crime_aware_route: RouteComparisonResult
    detour_percentage: float
    risk_reduction_percentage: float
    explanation: str
    disclaimer: str
    uncertainty_warning: Optional[str] = None


class StudyAreaInfo(BaseModel):
    name: str
    center: Coordinate
    radius_meters: float
    default_crime_buffer_meters: float
    crime_incident_count: int
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    categories: List[str]
    category_weights: Dict[str, float]


class CrimeFilterParams(BaseModel):
    category: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: Optional[int] = Field(default=500, ge=1, le=5000)
    offset: Optional[int] = Field(default=0, ge=0)


class HotspotPoint(BaseModel):
    lat: float
    lon: float
    intensity: float  # Weight sum
    count: int
    dominant_crime: str


class AnalyticsSummary(BaseModel):
    total_crimes: int
    violent_crimes_pct: float
    property_crimes_pct: float
    arrest_rate_pct: float
    top_categories: List[Dict[str, Any]]
    monthly_trend: List[Dict[str, Any]]
    hourly_distribution: List[Dict[str, Any]]
    day_of_week_distribution: List[Dict[str, Any]]
