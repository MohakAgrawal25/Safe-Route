"""
SafeRoute AI - Configuration Module
Defines study area bounds, crime category weights, and routing cost parameters.
"""
import os
from typing import Dict

# Study Area Geographic Scope: Chicago, Illinois
# Center: Middle of Chicago (Near West / Medical District / UIC / West Town / Pilsen)
STUDY_AREA_NAME: str = os.getenv("STUDY_AREA_NAME", "Chicago Central & Middle Metro Study Area")
STUDY_AREA_CENTER_LAT: float = float(os.getenv("STUDY_AREA_CENTER_LAT", "41.8700"))
STUDY_AREA_CENTER_LON: float = float(os.getenv("STUDY_AREA_CENTER_LON", "-87.6700"))
STUDY_AREA_RADIUS_METERS: float = float(os.getenv("STUDY_AREA_RADIUS_METERS", "7000.0"))

# Pedestrian & Routing Engine Parameters
WALKING_SPEED_MPS: float = float(os.getenv("WALKING_SPEED_MPS", "1.39"))  # 5 km/h walking speed
DEFAULT_CRIME_BUFFER_METERS: float = float(os.getenv("DEFAULT_CRIME_BUFFER_METERS", "75.0"))
DEFAULT_LAMBDA: float = float(os.getenv("DEFAULT_LAMBDA", "2.5"))  # Trade-off multiplier (risk vs length)
MAX_DETOUR_RATIO: float = float(os.getenv("MAX_DETOUR_RATIO", "0.30"))  # 30% max detour over shortest route
RECENCY_DECAY_HALF_LIFE_DAYS: float = float(os.getenv("RECENCY_DECAY_HALF_LIFE_DAYS", "180.0"))

# Chicago Data Portal (Socrata Open Data API)
CHICAGO_DATA_PORTAL_URL: str = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"
CHICAGO_API_APP_TOKEN: str = os.getenv("CHICAGO_API_APP_TOKEN", "")

# Transparent, Configurable Crime Category Weights
# Rationale: Violent crimes and crimes against persons carry the highest severity weights,
# property crimes carry moderate weights, and non-violent or administrative offenses carry lowest weights.
# All weights are bounded in [0.05, 1.00] for mathematical interpretability.
DEFAULT_CRIME_WEIGHTS: Dict[str, float] = {
    "HOMICIDE": 1.00,
    "CRIMINAL SEXUAL ASSAULT": 0.95,
    "ROBBERY": 0.85,
    "WEAPONS VIOLATION": 0.80,
    "ASSAULT": 0.75,
    "BATTERY": 0.70,
    "KIDNAPPING": 0.90,
    "ARSON": 0.65,
    "BURGLARY": 0.55,
    "MOTOR VEHICLE THEFT": 0.50,
    "THEFT": 0.35,
    "NARCOTICS": 0.30,
    "CRIMINAL DAMAGE": 0.25,
    "CRIMINAL TRESPASS": 0.20,
    "DECEPTIVE PRACTICE": 0.15,
    "PUBLIC PEACE VIOLATION": 0.20,
    "OFFENSE INVOLVING CHILDREN": 0.85,
    "INTIMIDATION": 0.60,
    "STALKING": 0.75,
    "INTERFERENCE WITH PUBLIC OFFICER": 0.30,
    "LIQUOR LAW VIOLATION": 0.15,
    "CONCEALED CARRY LICENSE VIOLATION": 0.40,
    "NON-CRIMINAL": 0.05,
    "OTHER OFFENSE": 0.20,
}

# Ethical Disclaimer & Limitations Statement
DISCLAIMER_TEXT: str = (
    "SafeRoute AI provides research-based navigation guidance by analyzing historical incident "
    "records published by the Chicago Police Department. Historical crime patterns cannot predict "
    "or guarantee future safety. Users must maintain situational awareness, obey all local regulations, "
    "and exercise personal discretion at all times."
)
