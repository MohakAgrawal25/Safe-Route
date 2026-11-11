"""Build a local pedestrian graph from Chicago's official street centerlines."""
import gzip
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from backend.config import STUDY_AREA_CENTER_LAT, STUDY_AREA_CENTER_LON
from backend.spatial_utils import haversine_distance

ROAD_DATA_PATH = Path(__file__).resolve().parent / "data" / "chicago_walk_network.json.gz"
WALKABLE_ROAD_CLASSES = {"2", "3", "4", "5", "7"}
MAX_SNAP_DISTANCE_METERS = 600.0


class PedestrianNetwork:
    """A locally cached, real-road graph with geometries retained for map output."""

    def __init__(self):
        self.graph = nx.Graph()
        self._build_chicago_centerline_graph()

    def _build_chicago_centerline_graph(self) -> None:
        if not ROAD_DATA_PATH.is_file():
            raise FileNotFoundError(
                f"Chicago street network data is missing: {ROAD_DATA_PATH}"
            )

        with gzip.open(ROAD_DATA_PATH, "rt", encoding="utf-8") as data_file:
            segments = json.load(data_file)

        for segment in segments:
            if str(segment.get("class")) not in WALKABLE_ROAD_CLASSES:
                continue
            if segment.get("status") not in (None, "N"):
                continue

            from_id = segment.get("fnode_id")
            to_id = segment.get("tnode_id")
            parts = segment.get("the_geom", {}).get("coordinates", [])
            if not from_id or not to_id or not parts:
                continue

            geometry = self._join_geometry_parts(parts)
            if len(geometry) < 2:
                continue

            from_id, to_id = str(from_id), str(to_id)
            from_point = geometry[0]
            to_point = geometry[-1]
            self._add_node(from_id, from_point)
            self._add_node(to_id, to_point)

            length = self._geometry_length(geometry)
            if length <= 0:
                continue

            self.graph.add_edge(
                from_id,
                to_id,
                name=segment.get("streetname") or "Street",
                length=length,
                risk_score=0.0,
                crime_count=0,
                categories={},
                geometry=geometry,
                road_class=str(segment.get("class")),
                one_way=segment.get("oneway_dir"),
                connector=False,
            )

        if not self.graph.number_of_edges():
            raise ValueError(f"No walkable street segments were loaded from {ROAD_DATA_PATH}")

        connected_components = list(nx.connected_components(self.graph))
        largest_component = max(connected_components, key=len)
        self.graph = self.graph.subgraph(largest_component).copy()

    @staticmethod
    def _join_geometry_parts(parts: List[List[List[float]]]) -> List[List[float]]:
        """Join contiguous GeoJSON line parts and keep coordinates as [lat, lon]."""
        joined: List[List[float]] = []
        for part in parts:
            points = [[float(lat), float(lon)] for lon, lat in part]
            if len(points) < 2:
                continue
            if not joined:
                joined.extend(points)
                continue

            if haversine_distance(*joined[-1], *points[0]) <= 1.0:
                joined.extend(points[1:])
            elif haversine_distance(*joined[-1], *points[-1]) <= 1.0:
                points.reverse()
                joined.extend(points[1:])
            else:
                # Disconnected parts are not joined by an invented straight line.
                return []
        return joined

    def _add_node(self, node_id: str, point: List[float]) -> None:
        if node_id not in self.graph:
            self.graph.add_node(node_id, lat=point[0], lon=point[1])

    @staticmethod
    def _geometry_length(geometry: List[List[float]]) -> float:
        return sum(
            haversine_distance(*geometry[index], *geometry[index + 1])
            for index in range(len(geometry) - 1)
        )

    @staticmethod
    def _metric_point(lat: float, lon: float) -> Tuple[float, float]:
        meters_per_degree_lat = 111320.0
        meters_per_degree_lon = meters_per_degree_lat * math.cos(
            math.radians(STUDY_AREA_CENTER_LAT)
        )
        return (
            (lon - STUDY_AREA_CENTER_LON) * meters_per_degree_lon,
            (lat - STUDY_AREA_CENTER_LAT) * meters_per_degree_lat,
        )

    @staticmethod
    def _interpolate_point(
        start: List[float], end: List[float], fraction: float
    ) -> List[float]:
        return [
            start[0] + fraction * (end[0] - start[0]),
            start[1] + fraction * (end[1] - start[1]),
        ]

    def _oriented_geometry(
        self, graph: nx.Graph, u: str, v: str, data: Dict[str, Any]
    ) -> List[List[float]]:
        geometry = data.get("geometry", [])
        if len(geometry) < 2:
            return [
                [graph.nodes[u]["lat"], graph.nodes[u]["lon"]],
                [graph.nodes[v]["lat"], graph.nodes[v]["lon"]],
            ]

        start = [graph.nodes[u]["lat"], graph.nodes[u]["lon"]]
        end = [graph.nodes[v]["lat"], graph.nodes[v]["lon"]]
        forward_error = haversine_distance(*geometry[0], *start) + haversine_distance(
            *geometry[-1], *end
        )
        reverse_error = haversine_distance(*geometry[-1], *start) + haversine_distance(
            *geometry[0], *end
        )
        return geometry if forward_error <= reverse_error else list(reversed(geometry))

    def snap_to_road(
        self, graph: nx.Graph, lat: float, lon: float, access_node_id: str
    ) -> str:
        """Attach a request endpoint to its nearest real road, splitting that edge."""
        query_x, query_y = self._metric_point(lat, lon)
        best: Optional[Tuple[float, str, str, Dict[str, Any], int, float, List[float]]] = None

        for u, v, data in graph.edges(data=True):
            if data.get("connector"):
                continue
            geometry = self._oriented_geometry(graph, u, v, data)
            for index, (start, end) in enumerate(zip(geometry, geometry[1:])):
                start_x, start_y = self._metric_point(*start)
                end_x, end_y = self._metric_point(*end)
                dx, dy = end_x - start_x, end_y - start_y
                squared_length = dx * dx + dy * dy
                fraction = 0.0 if squared_length == 0 else (
                    (query_x - start_x) * dx + (query_y - start_y) * dy
                ) / squared_length
                fraction = min(1.0, max(0.0, fraction))
                projected = self._interpolate_point(start, end, fraction)
                projected_x, projected_y = self._metric_point(*projected)
                distance = math.hypot(query_x - projected_x, query_y - projected_y)
                if best is None or distance < best[0]:
                    best = (distance, u, v, data, index, fraction, projected)

        if best is None or best[0] > MAX_SNAP_DISTANCE_METERS:
            raise ValueError(
                f"Could not find a walkable street within {int(MAX_SNAP_DISTANCE_METERS)}m "
                "of the selected location."
            )

        _, u, v, edge_data, segment_index, fraction, projected = best
        geometry = self._oriented_geometry(graph, u, v, edge_data)
        if fraction <= 1e-6:
            road_node = u if segment_index == 0 else None
        elif fraction >= 1.0 - 1e-6:
            road_node = v if segment_index == len(geometry) - 2 else None
        else:
            road_node = None

        if road_node is None:
            snap_node_id = f"__snap_{access_node_id}"
            while snap_node_id in graph:
                snap_node_id += "_"
            first_half = geometry[:segment_index + 1] + [projected]
            second_half = [projected] + geometry[segment_index + 1:]
            graph.remove_edge(u, v)
            graph.add_node(snap_node_id, lat=projected[0], lon=projected[1])
            for start_node, end_node, part in (
                (u, snap_node_id, first_half),
                (snap_node_id, v, second_half),
            ):
                if len(part) < 2:
                    continue
                split_data = dict(edge_data)
                split_data["geometry"] = part
                split_data["length"] = self._geometry_length(part)
                graph.add_edge(start_node, end_node, **split_data)
            road_node = snap_node_id

        road_point = [graph.nodes[road_node]["lat"], graph.nodes[road_node]["lon"]]
        graph.add_node(access_node_id, lat=lat, lon=lon)
        graph.add_edge(
            access_node_id,
            road_node,
            name="Street access",
            length=haversine_distance(lat, lon, *road_point),
            risk_score=0.0,
            crime_count=0,
            categories={},
            geometry=[[lat, lon], road_point],
            connector=True,
        )
        return access_node_id

    def find_nearest_node(self, lat: float, lon: float, exclude_node: str = None) -> str:
        """Return the closest street-intersection node for compatibility with callers."""
        best_node = None
        min_distance = float("inf")
        for node_id, data in self.graph.nodes(data=True):
            if node_id == exclude_node:
                continue
            distance = haversine_distance(lat, lon, data["lat"], data["lon"])
            if distance < min_distance:
                best_node, min_distance = node_id, distance
        return best_node

    def get_all_edges_geometry(self) -> List[Dict[str, Any]]:
        """Return local street edges and their original centerline geometries."""
        return [
            {
                "u": u,
                "v": v,
                "name": data.get("name", "Street"),
                "length": data.get("length", 0.0),
                "risk_score": data.get("risk_score", 0.0),
                "crime_count": data.get("crime_count", 0),
                "geometry": data.get("geometry", []),
            }
            for u, v, data in self.graph.edges(data=True)
        ]


network_instance = PedestrianNetwork()


def get_pedestrian_network() -> PedestrianNetwork:
    return network_instance
