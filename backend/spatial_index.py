"""
Spatial Indexing & Crime Risk Scoring Engine for SafeRoute AI.
Uses metric projection and scipy.spatial.cKDTree for ultra-fast geospatial buffer queries.
Applies category severity weights, exponential recency decay, and segment-level normalization.
"""
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Set
import numpy as np
from scipy.spatial import cKDTree

from backend.config import (
    STUDY_AREA_CENTER_LAT,
    STUDY_AREA_CENTER_LON,
    DEFAULT_CRIME_BUFFER_METERS,
    RECENCY_DECAY_HALF_LIFE_DAYS,
    STUDY_AREA_RADIUS_METERS,
)
from backend.spatial_utils import haversine_distance, is_within_study_area

class CrimeSpatialIndex:
    """
    High-performance spatial index for crime incidents within the study area.
    """
    def __init__(self, incidents: List[Dict[str, Any]]):
        self.incidents = incidents
        self.tree = None
        self.coords_metric = None
        self._build_index()

    def _latlon_to_metric(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Projects (lat, lon) to local metric offsets (x, y in meters)
        centered at the Chicago study area center point.
        """
        lat_rad = math.radians(STUDY_AREA_CENTER_LAT)
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * math.cos(lat_rad)

        x = (lon - STUDY_AREA_CENTER_LON) * m_per_deg_lon
        y = (lat - STUDY_AREA_CENTER_LAT) * m_per_deg_lat
        return (x, y)

    def _build_index(self):
        """Builds KD-tree from crime coordinates in projected metric space."""
        if not self.incidents:
            return

        points = []
        for inc in self.incidents:
            lat = inc.get("latitude")
            lon = inc.get("longitude")
            points.append(self._latlon_to_metric(lat, lon))

        self.coords_metric = np.array(points)
        self.tree = cKDTree(self.coords_metric)

    def query_segment_incidents(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        buffer_meters: float = DEFAULT_CRIME_BUFFER_METERS
    ) -> List[Dict[str, Any]]:
        """
        Finds all unique crime incidents within buffer_meters of a line segment.
        Samples points along the segment to prevent missing incidents in curves or long segments.
        """
        if self.tree is None or len(self.incidents) == 0:
            return []

        x1, y1 = self._latlon_to_metric(lat1, lon1)
        x2, y2 = self._latlon_to_metric(lat2, lon2)

        seg_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        # Sample points every 30 meters along segment
        num_samples = max(2, int(seg_length / 30.0) + 1)

        unique_indices: Set[int] = set()
        for i in range(num_samples):
            t = i / (num_samples - 1)
            sx = x1 + t * (x2 - x1)
            sy = y1 + t * (y2 - y1)
            indices = self.tree.query_ball_point([sx, sy], r=buffer_meters)
            unique_indices.update(indices)

        return [self.incidents[idx] for idx in unique_indices]

    def compute_segment_risk(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        length_m: float,
        buffer_meters: float = DEFAULT_CRIME_BUFFER_METERS,
        reference_time: datetime = None
    ) -> Tuple[float, int, Dict[str, int]]:
        """
        Computes the normalized risk score for a road segment.
        Considers category severity weight and exponential recency decay.
        Returns: (normalized_risk, incident_count, category_counts)
        """
        if reference_time is None:
            reference_time = datetime.now()

        nearby_crimes = self.query_segment_incidents(lat1, lon1, lat2, lon2, buffer_meters)
        if not nearby_crimes:
            return (0.0, 0, {})

        total_weighted_risk = 0.0
        category_counts: Dict[str, int] = {}

        # Recency decay constant (lambda = ln(2) / half_life)
        decay_const = math.log(2.0) / max(1.0, RECENCY_DECAY_HALF_LIFE_DAYS)

        for inc in nearby_crimes:
            cat = inc.get("primary_type", "OTHER OFFENSE")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            weight = inc.get("severity_weight", 0.20)

            # Date calculation
            inc_date = inc.get("date")
            if isinstance(inc_date, str):
                try:
                    dt = datetime.fromisoformat(inc_date.replace('Z', '+00:00'))
                    # Strip timezone for naive comparison
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                except ValueError:
                    dt = reference_time
            elif isinstance(inc_date, datetime):
                dt = inc_date.replace(tzinfo=None) if inc_date.tzinfo else inc_date
            else:
                dt = reference_time

            days_diff = max(0.0, (reference_time - dt).total_seconds() / 86400.0)
            recency_factor = math.exp(-decay_const * days_diff)

            total_weighted_risk += weight * recency_factor

        # Normalize risk by segment length (risk density per 100 meters)
        length_factor = max(0.5, length_m / 100.0)
        normalized_risk = total_weighted_risk / length_factor

        return (normalized_risk, len(nearby_crimes), category_counts)

    def compute_route_risk(
        self,
        route_coords: List[List[float]],
        total_distance_m: float,
        buffer_meters: float = DEFAULT_CRIME_BUFFER_METERS,
        reference_time: datetime = None
    ) -> Tuple[float, int, Dict[str, int]]:
        """
        Computes the route-level historical crime exposure index (0 to 100).
        Deduplicates incidents across the entire route to avoid double-counting.
        """
        if reference_time is None:
            reference_time = datetime.now()

        if self.tree is None or len(route_coords) < 2:
            return (0.0, 0, {})

        seen_incident_ids: Set[str] = set()
        unique_incidents: List[Dict[str, Any]] = []

        for i in range(len(route_coords) - 1):
            lat1, lon1 = route_coords[i]
            lat2, lon2 = route_coords[i + 1]
            seg_crimes = self.query_segment_incidents(lat1, lon1, lat2, lon2, buffer_meters)
            for c in seg_crimes:
                inc_id = c.get("incident_id") or f"{c.get('latitude')}_{c.get('longitude')}"
                if inc_id not in seen_incident_ids:
                    seen_incident_ids.add(inc_id)
                    unique_incidents.append(c)

        if not unique_incidents:
            return (0.0, 0, {})

        decay_const = math.log(2.0) / max(1.0, RECENCY_DECAY_HALF_LIFE_DAYS)
        total_route_risk = 0.0
        category_counts: Dict[str, int] = {}

        for inc in unique_incidents:
            cat = inc.get("primary_type", "OTHER OFFENSE")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            weight = inc.get("severity_weight", 0.20)
            inc_date = inc.get("date")
            if isinstance(inc_date, str):
                try:
                    dt = datetime.fromisoformat(inc_date.replace('Z', '+00:00'))
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                except ValueError:
                    dt = reference_time
            elif isinstance(inc_date, datetime):
                dt = inc_date.replace(tzinfo=None) if inc_date.tzinfo else inc_date
            else:
                dt = reference_time

            days_diff = max(0.0, (reference_time - dt).total_seconds() / 86400.0)
            recency_factor = math.exp(-decay_const * days_diff)

            total_route_risk += weight * recency_factor

        # Standardized Route Historical Exposure Index (0 to 100)
        # Exposure intensity per 1 km walked, scaled to an intuitive 0-100 index
        km_walked = max(0.1, total_distance_m / 1000.0)
        exposure_per_km = total_route_risk / km_walked
        risk_index = round(100.0 * (1.0 - math.exp(-exposure_per_km / 100.0)), 1)

        return (risk_index, len(unique_incidents), category_counts)

    def generate_hotspots(self, grid_size_meters: float = 350.0) -> List[Dict[str, Any]]:
        """
        Aggregates crime intensity into spatial clusters / hotspots across the study area.
        """
        if not self.incidents:
            return []

        # Discretize into spatial buckets
        grid: Dict[Tuple[int, int], Dict[str, Any]] = {}
        lat_rad = math.radians(STUDY_AREA_CENTER_LAT)
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * math.cos(lat_rad)

        for inc in self.incidents:
            lat = inc.get("latitude")
            lon = inc.get("longitude")
            if lat is None or lon is None:
                continue
            inside, _ = is_within_study_area(
                lat,
                lon,
                STUDY_AREA_CENTER_LAT,
                STUDY_AREA_CENTER_LON,
                STUDY_AREA_RADIUS_METERS
            )
            if not inside:
                continue

            x = (lon - STUDY_AREA_CENTER_LON) * m_per_deg_lon
            y = (lat - STUDY_AREA_CENTER_LAT) * m_per_deg_lat

            gx = int(round(x / grid_size_meters))
            gy = int(round(y / grid_size_meters))
            key = (gx, gy)

            if key not in grid:
                grid[key] = {
                    "gx": gx,
                    "gy": gy,
                    "count": 0,
                    "weight_sum": 0.0,
                    "categories": {}
                }

            grid[key]["count"] += 1
            w = inc.get("severity_weight", 0.20)
            grid[key]["weight_sum"] += w
            cat = inc.get("primary_type", "OTHER")
            grid[key]["categories"][cat] = grid[key]["categories"].get(cat, 0) + 1

        hotspots = []
        for (gx, gy), data in grid.items():
            if data["count"] < 2:
                continue
            center_x = gx * grid_size_meters
            center_y = gy * grid_size_meters

            h_lat = STUDY_AREA_CENTER_LAT + (center_y / m_per_deg_lat)
            h_lon = STUDY_AREA_CENTER_LON + (center_x / m_per_deg_lon)
            inside, _ = is_within_study_area(
                h_lat,
                h_lon,
                STUDY_AREA_CENTER_LAT,
                STUDY_AREA_CENTER_LON,
                STUDY_AREA_RADIUS_METERS
            )
            if not inside:
                continue

            # Dominant crime in hotspot
            dominant = max(data["categories"].items(), key=lambda item: item[1])[0]

            hotspots.append({
                "lat": round(h_lat, 6),
                "lon": round(h_lon, 6),
                "intensity": round(data["weight_sum"], 2),
                "count": data["count"],
                "dominant_crime": dominant
            })

        # Sort by intensity descending
        hotspots.sort(key=lambda x: x["intensity"], reverse=True)
        return hotspots
