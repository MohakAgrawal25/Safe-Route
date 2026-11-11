"""
SafeRoute AI - Core Routing Engine.
Computes:
1. Shortest Route (Route A): standard Dijkstra distance-minimizing path.
2. Crime-Aware Route (Route B): Dijkstra path using crime-sensitive edge costs
   segment_cost = segment_length * (1 + lambda * segment_risk)
   strictly respecting the user's crime aversion multiplier (lambda),
   maximum allowed detour ratio, and segment crime buffer.
Generates human-readable, transparent comparison explanations.
"""
from typing import Dict, Any, List, Tuple, Optional
import networkx as nx

from backend.config import (
    WALKING_SPEED_MPS,
    DEFAULT_LAMBDA,
    MAX_DETOUR_RATIO,
    DEFAULT_CRIME_BUFFER_METERS,
    DISCLAIMER_TEXT
)
from backend.road_network import PedestrianNetwork, get_pedestrian_network
from backend.spatial_index import CrimeSpatialIndex
from backend.spatial_utils import haversine_distance

class SafeRoutingEngine:
    """
    Pedestrian routing engine providing dual shortest and crime-aware routing
    with dynamic edge-weight calculation and detour cap enforcement.
    """
    def __init__(self, network: PedestrianNetwork = None):
        self.network = network or get_pedestrian_network()
        self.spatial_index: Optional[CrimeSpatialIndex] = None
        self._last_buffer_meters: Optional[float] = None

    def update_spatial_index(self, spatial_index: CrimeSpatialIndex):
        """Updates the spatial index and recalculates edge crime weights."""
        self.spatial_index = spatial_index
        self._last_buffer_meters = None
        self._recalculate_edge_risks(DEFAULT_CRIME_BUFFER_METERS)

    def _recalculate_edge_risks(self, buffer_meters: float = DEFAULT_CRIME_BUFFER_METERS):
        """
        Computes crime risk scores for each edge in the pedestrian graph
        using the specified buffer distance in meters.
        """
        if not self.spatial_index:
            return

        if self._last_buffer_meters == buffer_meters:
            return

        self._last_buffer_meters = buffer_meters

        for u, v, data in self.network.graph.edges(data=True):
            geom = data.get("geometry", [])
            if len(geom) < 2:
                lat1 = self.network.graph.nodes[u]["lat"]
                lon1 = self.network.graph.nodes[u]["lon"]
                lat2 = self.network.graph.nodes[v]["lat"]
                lon2 = self.network.graph.nodes[v]["lon"]
                geom = [[lat1, lon1], [lat2, lon2]]

            weighted_risk = 0.0
            measured_length = 0.0
            incident_count = 0
            categories: Dict[str, int] = {}
            for start, end in zip(geom, geom[1:]):
                length = haversine_distance(*start, *end)
                if length <= 0:
                    continue
                risk, count, cats = self.spatial_index.compute_segment_risk(
                    *start, *end, length, buffer_meters
                )
                weighted_risk += risk * length
                measured_length += length
                incident_count = max(incident_count, count)
                for category, category_count in cats.items():
                    categories[category] = max(
                        categories.get(category, 0), category_count
                    )

            data["risk_score"] = weighted_risk / measured_length if measured_length else 0.0
            data["crime_count"] = incident_count
            data["categories"] = categories

    def _format_time(self, seconds: float) -> str:
        """Formats walking duration in minutes and seconds."""
        total_mins = int(round(seconds / 60.0))
        if total_mins < 1:
            return "< 1 min"
        elif total_mins < 60:
            return f"{total_mins} min"
        else:
            hrs = total_mins // 60
            mins = total_mins % 60
            return f"{hrs}h {mins}m"

    def _extract_route_geometry(
        self, path: List[str], graph: nx.Graph
    ) -> List[List[float]]:
        """Extract each full street-centerline shape in traversal order."""
        if not path:
            return []

        coords = [[graph.nodes[path[0]]["lat"], graph.nodes[path[0]]["lon"]]]
        for u, v in zip(path, path[1:]):
            data = graph.get_edge_data(u, v)
            geometry = data.get("geometry", []) if data else []
            if len(geometry) < 2:
                geometry = [
                    [graph.nodes[u]["lat"], graph.nodes[u]["lon"]],
                    [graph.nodes[v]["lat"], graph.nodes[v]["lon"]],
                ]
            start = [graph.nodes[u]["lat"], graph.nodes[u]["lon"]]
            if haversine_distance(*geometry[0], *start) > haversine_distance(
                *geometry[-1], *start
            ):
                geometry = list(reversed(geometry))
            coords.extend(geometry[1:])
        return coords

    def _calculate_path_metrics(
        self, path: List[str], graph: nx.Graph
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        """Calculates distance (m), walking duration (s), and segment details."""
        total_dist = 0.0
        segments = []
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            edge_data = graph.get_edge_data(u, v)
            if edge_data is None:
                continue
            seg_len = edge_data.get("length", 0.0)
            seg_risk = edge_data.get("risk_score", 0.0)
            seg_crimes = edge_data.get("crime_count", 0)
            cats = edge_data.get("categories", {})
            dom_cat = max(cats.items(), key=lambda x: x[1])[0] if cats else None

            total_dist += seg_len
            segments.append({
                "from_node": u,
                "to_node": v,
                "length_m": round(seg_len, 1),
                "risk_score": round(seg_risk, 3),
                "incident_count": seg_crimes,
                "dominant_category": dom_cat
            })

        duration = total_dist / max(0.5, WALKING_SPEED_MPS)
        return total_dist, duration, segments

    def compute_dual_routes(
        self,
        start_lat: float, start_lon: float,
        dest_lat: float, dest_lon: float,
        risk_lambda: float = DEFAULT_LAMBDA,
        max_detour_ratio: float = MAX_DETOUR_RATIO,
        buffer_meters: float = DEFAULT_CRIME_BUFFER_METERS
    ) -> Dict[str, Any]:
        """
        Calculates both Route A (Shortest) and Route B (Crime-Aware),
        enforces detour bounds, computes normalized 0-100 risk indices,
        and provides an explainable comparison.
        """
        # Update base-edge risks, then split a request-local copy at the nearest roads.
        if self.spatial_index:
            self._recalculate_edge_risks(buffer_meters)
        graph = self.network.graph.copy()
        start_node = self.network.snap_to_road(
            graph, start_lat, start_lon, "__route_start"
        )
        dest_node = self.network.snap_to_road(
            graph, dest_lat, dest_lon, "__route_destination"
        )

        # 2. Compute Route A: Shortest Route (minimizes distance)
        try:
            shortest_path = nx.shortest_path(
                graph,
                source=start_node,
                target=dest_node,
                weight="length"
            )
        except nx.NetworkXNoPath:
            raise ValueError("No pedestrian path could be found between the selected locations.")

        shortest_dist, shortest_dur, shortest_segs = self._calculate_path_metrics(
            shortest_path, graph
        )
        shortest_coords = self._extract_route_geometry(shortest_path, graph)

        # Compute Route A historical crime risk index
        if self.spatial_index:
            risk_a, inc_count_a, cats_a = self.spatial_index.compute_route_risk(
                shortest_coords, shortest_dist, buffer_meters
            )
        else:
            risk_a, inc_count_a, cats_a = (0.0, 0, {})

        # 3. Compute Route B: Crime-Aware Route
        # If user explicitly sets lambda = 0.0, Route B collapses to the shortest route
        if risk_lambda <= 0.01:
            best_safe_path = shortest_path
            best_safe_dist = shortest_dist
            best_safe_dur = shortest_dur
            best_safe_segs = shortest_segs
            best_safe_coords = shortest_coords
            best_safe_risk = risk_a
            best_inc_count = inc_count_a
            best_cats = cats_a
            found_alternative = False
        else:
            # We search across diverse corridor candidates by testing multiple sensitivity weights
            # and penalty variations to discover valid alternative pedestrian corridors
            candidate_paths = []
            seen_path_tuples = set()

            test_weights = [
                risk_lambda * 6.0,
                risk_lambda * 4.0,
                risk_lambda * 2.5,
                risk_lambda * 1.5,
                risk_lambda * 0.8,
            ]

            for test_w in test_weights:
                # FIX: Use default argument to capture current test_w value (avoid Python closure bug)
                def weight_fn(_u, _v, d, _w=test_w):
                    l = d.get("length", 1.0)
                    r = d.get("risk_score", 0.0)
                    return l * (1.0 + _w * r)

                try:
                    p = nx.shortest_path(
                        graph,
                        source=start_node,
                        target=dest_node,
                        weight=weight_fn
                    )
                    tup = tuple(p)
                    if tup not in seen_path_tuples:
                        seen_path_tuples.add(tup)
                        candidate_paths.append(p)
                except nx.NetworkXNoPath:
                    continue

            # Include a few true distance-ranked alternatives so Route B can remain
            # visibly distinct when crime exposure is tied or saturated.
            try:
                for index, path in enumerate(
                    nx.shortest_simple_paths(
                        graph, start_node, dest_node, weight="length"
                    )
                ):
                    if index >= 6:
                        break
                    path_tuple = tuple(path)
                    if path_tuple not in seen_path_tuples:
                        seen_path_tuples.add(path_tuple)
                        candidate_paths.append(path)
            except nx.NetworkXNoPath:
                pass

            # Also generate alternative corridors by blocking segments of the shortest path
            # Penalize the top-1/3 and middle section edges to force route diversification
            if len(shortest_path) > 3:
                # Penalize middle third of the shortest path
                third = len(shortest_path) // 3
                blocked_edges = set()
                for idx in range(third, 2 * third):
                    if idx + 1 < len(shortest_path):
                        u_b = shortest_path[idx]
                        v_b = shortest_path[idx + 1]
                        blocked_edges.add((u_b, v_b))
                        blocked_edges.add((v_b, u_b))  # undirected

                def penalized_weight_fn(u, v, d, _lam=risk_lambda, _blocked=blocked_edges):
                    l = d.get("length", 1.0)
                    r = d.get("risk_score", 0.0)
                    base_cost = l * (1.0 + _lam * 3.0 * r)
                    if (u, v) in _blocked:
                        return base_cost * 10.0  # Strongly encourage parallel corridor
                    return base_cost

                try:
                    pen_p = nx.shortest_path(
                        graph,
                        source=start_node,
                        target=dest_node,
                        weight=penalized_weight_fn
                    )
                    tup = tuple(pen_p)
                    if tup not in seen_path_tuples:
                        seen_path_tuples.add(tup)
                        candidate_paths.append(pen_p)
                except nx.NetworkXNoPath:
                    pass

                # Also penalize first-third edges for another alternative
                first_blocked = set()
                for idx in range(0, third):
                    if idx + 1 < len(shortest_path):
                        u_b = shortest_path[idx]
                        v_b = shortest_path[idx + 1]
                        first_blocked.add((u_b, v_b))
                        first_blocked.add((v_b, u_b))

                def alt_weight_fn(u, v, d, _lam=risk_lambda, _blocked=first_blocked):
                    l = d.get("length", 1.0)
                    r = d.get("risk_score", 0.0)
                    base_cost = l * (1.0 + _lam * 2.0 * r)
                    if (u, v) in _blocked:
                        return base_cost * 8.0
                    return base_cost

                try:
                    alt_p = nx.shortest_path(
                        graph,
                        source=start_node,
                        target=dest_node,
                        weight=alt_weight_fn
                    )
                    tup = tuple(alt_p)
                    if tup not in seen_path_tuples:
                        seen_path_tuples.add(tup)
                        candidate_paths.append(alt_p)
                except nx.NetworkXNoPath:
                    pass

            # Evaluate all candidate paths against detour cap and compute their metrics
            valid_alternatives = []
            for p in candidate_paths:
                p_dist, p_dur, p_segs = self._calculate_path_metrics(p, graph)
                detour = (p_dist - shortest_dist) / max(1.0, shortest_dist)

                # Strict enforcement of max_detour_ratio
                if detour > max_detour_ratio:
                    continue

                p_coords = self._extract_route_geometry(p, graph)

                if self.spatial_index:
                    p_risk, p_count, p_cats = self.spatial_index.compute_route_risk(
                        p_coords, p_dist, buffer_meters
                    )
                else:
                    p_risk, p_count, p_cats = (0.0, 0, {})

                valid_alternatives.append({
                    "path": p,
                    "dist": p_dist,
                    "dur": p_dur,
                    "segs": p_segs,
                    "coords": p_coords,
                    "risk": p_risk,
                    "count": p_count,
                    "cats": p_cats,
                    "detour": detour,
                    "is_shortest": (p == shortest_path)
                })

            # Pick the best route based on user lambda trade-off
            # Cost = Distance + lambda * ScalingFactor * Risk
            # High lambda favors lower risk even if detour is larger; low lambda favors shorter distance
            if valid_alternatives:
                # Find alternative paths that reduce risk compared to shortest route
                safer_alts = [
                    a for a in valid_alternatives
                    if not a["is_shortest"] and a["risk"] < risk_a
                ]

                if safer_alts:
                    # Choose candidate minimizing composite user objective:
                    # Objective = dist + (risk_lambda * 350.0) * (risk / max(1.0, risk_a))
                    best_cand = min(
                        safer_alts,
                        key=lambda a: a["dist"] + (risk_lambda * 350.0) * (a["risk"] / max(1.0, risk_a))
                    )
                    best_safe_path = best_cand["path"]
                    best_safe_dist = best_cand["dist"]
                    best_safe_dur = best_cand["dur"]
                    best_safe_segs = best_cand["segs"]
                    best_safe_coords = best_cand["coords"]
                    best_safe_risk = best_cand["risk"]
                    best_inc_count = best_cand["count"]
                    best_cats = best_cand["cats"]
                    found_alternative = True
                else:
                    distinct_alternatives = [
                        candidate for candidate in valid_alternatives
                        if not candidate["is_shortest"]
                    ]
                    if distinct_alternatives:
                        # Keep Route B visible without claiming a safety improvement.
                        best_cand = min(
                            distinct_alternatives,
                            key=lambda candidate: (
                                candidate["risk"],
                                candidate["dist"],
                            ),
                        )
                        best_safe_path = best_cand["path"]
                        best_safe_dist = best_cand["dist"]
                        best_safe_dur = best_cand["dur"]
                        best_safe_segs = best_cand["segs"]
                        best_safe_coords = best_cand["coords"]
                        best_safe_risk = best_cand["risk"]
                        best_inc_count = best_cand["count"]
                        best_cats = best_cand["cats"]
                    else:
                        best_safe_path = shortest_path
                        best_safe_dist = shortest_dist
                        best_safe_dur = shortest_dur
                        best_safe_segs = shortest_segs
                        best_safe_coords = shortest_coords
                        best_safe_risk = risk_a
                        best_inc_count = inc_count_a
                        best_cats = cats_a
                    found_alternative = False
            else:
                best_safe_path = shortest_path
                best_safe_dist = shortest_dist
                best_safe_dur = shortest_dur
                best_safe_segs = shortest_segs
                best_safe_coords = shortest_coords
                best_safe_risk = risk_a
                best_inc_count = inc_count_a
                best_cats = cats_a
                found_alternative = False

        # Calculate comparison statistics
        detour_pct = round(((best_safe_dist - shortest_dist) / max(1.0, shortest_dist)) * 100.0, 1)
        risk_diff = risk_a - best_safe_risk
        risk_reduct_pct = (
            round(max(0.0, risk_diff / max(0.01, risk_a) * 100.0), 1)
            if risk_a > 0
            else 0.0
        )

        explanation, uncertainty_warning = self._generate_explanation(
            shortest_path, best_safe_path,
            shortest_dist, best_safe_dist,
            risk_a, best_safe_risk,
            inc_count_a, best_inc_count,
            cats_a, best_cats,
            found_alternative, detour_pct, risk_reduct_pct,
            risk_lambda, max_detour_ratio, buffer_meters
        )

        return {
            "shortest_route": {
                "route_type": "shortest",
                "distance_meters": round(shortest_dist, 1),
                "duration_seconds": round(shortest_dur, 0),
                "walking_time_formatted": self._format_time(shortest_dur),
                "historical_risk_index": risk_a,
                "incident_exposure_count": inc_count_a,
                "top_categories_along_route": cats_a,
                "coordinates": shortest_coords,
                "segments": shortest_segs
            },
            "crime_aware_route": {
                "route_type": "crime_aware",
                "distance_meters": round(best_safe_dist, 1),
                "duration_seconds": round(best_safe_dur, 0),
                "walking_time_formatted": self._format_time(best_safe_dur),
                "historical_risk_index": best_safe_risk,
                "incident_exposure_count": best_inc_count,
                "top_categories_along_route": best_cats,
                "coordinates": best_safe_coords,
                "segments": best_safe_segs
            },
            "detour_percentage": detour_pct,
            "risk_reduction_percentage": risk_reduct_pct,
            "explanation": explanation,
            "disclaimer": DISCLAIMER_TEXT,
            "uncertainty_warning": uncertainty_warning,
            "applied_parameters": {
                "risk_lambda": risk_lambda,
                "max_detour_ratio": max_detour_ratio,
                "buffer_meters": buffer_meters
            }
        }

    def _generate_explanation(
        self,
        path_a: List[str], path_b: List[str],
        dist_a: float, dist_b: float,
        risk_a: float, risk_b: float,
        count_a: int, count_b: int,
        cats_a: Dict[str, int], cats_b: Dict[str, int],
        found_alt: bool,
        detour_pct: float,
        risk_reduct_pct: float,
        risk_lambda: float,
        max_detour_ratio: float,
        buffer_meters: float
    ) -> Tuple[str, Optional[str]]:
        """Generates clear, explainable comparison rationale and uncertainty warning."""
        dist_diff_m = int(round(dist_b - dist_a))

        uncertainty_warning = None
        if count_a < 3 and count_b < 3:
            uncertainty_warning = (
                f"Data density within {int(buffer_meters)}m buffer is sparse (<3 recorded incidents). "
                "Calculated risk scores have higher uncertainty."
            )

        if not found_alt or path_a == path_b:
            if path_a != path_b:
                explanation = (
                    f"Route B is a distinct {int(round(dist_b))}m street alternative "
                    f"within the {int(max_detour_ratio * 100)}% detour limit, but the available "
                    "historical data did not show a lower exposure than Route A."
                )
                return explanation, uncertainty_warning
            if risk_lambda <= 0.01:
                explanation = (
                    f"Crime Aversion Multiplier (λ) is set to 0.0. "
                    f"Route B is identical to Route A ({int(round(dist_a))}m) prioritizing minimum distance only."
                )
            else:
                explanation = (
                    f"The shortest corridor ({int(round(dist_a))}m) remains Route B because no distinct "
                    f"street alternative reducing historical exposure was found within your configured "
                    f"{int(max_detour_ratio * 100)}% maximum detour limit."
                )
            return explanation, uncertainty_warning

        # Find which high-severity categories were avoided
        avoided_cats = []
        for cat, cnt_a in cats_a.items():
            cnt_b = cats_b.get(cat, 0)
            if cnt_a > cnt_b:
                avoided_cats.append(f"{cat.title()} (-{cnt_a - cnt_b})")

        exposure_detail = (
            f"It reduces exposure to {', '.join(avoided_cats[:3])}."
            if avoided_cats
            else "It favors segments with lower severity- and recency-weighted exposure."
        )

        explanation = (
            f"With λ={risk_lambda:.1f} and {int(buffer_meters)}m buffer, Route B achieves a {risk_reduct_pct}% lower historical "
            f"exposure index ({risk_b} vs {risk_a}) with a {detour_pct}% detour (+{dist_diff_m}m). "
            f"{exposure_detail} It respects "
            f"your {int(max_detour_ratio * 100)}% maximum detour cap."
        )

        return explanation, uncertainty_warning

# Singleton routing engine instance
routing_engine_instance = SafeRoutingEngine()

def get_routing_engine() -> SafeRoutingEngine:
    return routing_engine_instance
