"""
Unit tests for Dijkstra shortest path and crime-aware routing algorithms.
"""
from backend.road_network import get_pedestrian_network
from backend.spatial_index import CrimeSpatialIndex
from backend.routing_engine import SafeRoutingEngine

def test_pedestrian_network_integrity():
    net = get_pedestrian_network()
    assert net.graph.number_of_nodes() > 200
    assert net.graph.number_of_edges() > 400
    assert all(data["road_class"] in {"2", "3", "4", "5", "7"}
               for _, _, data in net.graph.edges(data=True))


def test_route_geometry_uses_centerline_vertices():
    net = get_pedestrian_network()
    engine = SafeRoutingEngine(net)
    u, v, edge = next(
        (u, v, data)
        for u, v, data in net.graph.edges(data=True)
        if len(data["geometry"]) > 2
    )

    route_geometry = engine._extract_route_geometry([u, v], net.graph)
    centerline = edge["geometry"]

    assert len(route_geometry) == len(centerline)
    assert route_geometry in (centerline, list(reversed(centerline)))


def test_navy_pier_landmark_snaps_to_walkable_street():
    net = get_pedestrian_network()
    graph = net.graph.copy()

    access_node = net.snap_to_road(
        graph, 41.8917, -87.6043, "__navy_pier_test"
    )

    connector = graph.edges[access_node, next(iter(graph.neighbors(access_node)))]
    assert connector["connector"] is True
    assert connector["length"] <= 600.0


def test_routing_shortest_vs_crime_aware():
    net = get_pedestrian_network()
    engine = SafeRoutingEngine(net)

    # Place a synthetic high-severity incident right on State St
    # (between Adams and Jackson)
    synthetic_crimes = [
        {
            "incident_id": "SYNTH-1",
            "date": "2026-10-15T12:00:00",
            "primary_type": "ROBBERY",
            "severity_weight": 0.95,
            "latitude": 41.8790,
            "longitude": -87.6278,
            "distance_from_center_m": 120.0
        },
        {
            "incident_id": "SYNTH-2",
            "date": "2026-10-16T14:00:00",
            "primary_type": "BATTERY",
            "severity_weight": 0.80,
            "latitude": 41.8790,
            "longitude": -87.6278,
            "distance_from_center_m": 120.0
        }
    ]
    spatial_index = CrimeSpatialIndex(synthetic_crimes)
    engine.update_spatial_index(spatial_index)

    # Route from Madison & State to Harrison & State
    # Start: Madison & State (41.8820, -87.6278)
    # Dest: Harrison & State (41.8741, -87.6278)
    res = engine.compute_dual_routes(
        start_lat=41.8820, start_lon=-87.6278,
        dest_lat=41.8741, dest_lon=-87.6278,
        risk_lambda=3.5,
        max_detour_ratio=0.35,
        buffer_meters=60.0
    )

    shortest = res["shortest_route"]
    crime_aware = res["crime_aware_route"]

    # Shortest route should have minimum distance
    assert shortest["distance_meters"] <= crime_aware["distance_meters"]

    # Detour must not exceed maximum detour ratio
    assert res["detour_percentage"] <= 35.0

    # Risk score must be non-negative
    assert shortest["historical_risk_index"] >= 0.0
    assert crime_aware["historical_risk_index"] >= 0.0
    assert crime_aware["coordinates"] != shortest["coordinates"]
    assert crime_aware["historical_risk_index"] < shortest["historical_risk_index"]
