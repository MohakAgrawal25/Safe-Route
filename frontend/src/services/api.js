/**
 * SafeRoute AI - API Service Layer
 * Centralizes all backend REST calls for study bounds, crime data, routing, and analytics.
 */

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchStudyArea() {
  const res = await fetch(`${API_BASE}/study-area`);
  if (!res.ok) throw new Error('Failed to load study area configuration');
  return res.json();
}

export async function fetchCrimes(category = '', limit = 300) {
  let url = `${API_BASE}/crimes?limit=${limit}`;
  if (category && category !== 'ALL') {
    url += `&category=${encodeURIComponent(category)}`;
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch crime records');
  return res.json();
}

export async function fetchHotspots() {
  const res = await fetch(`${API_BASE}/crime-hotspots?grid_size_meters=350`);
  if (!res.ok) throw new Error('Failed to load crime hotspots');
  return res.json();
}

export async function fetchAnalytics() {
  const res = await fetch(`${API_BASE}/analytics/summary`);
  if (!res.ok) throw new Error('Failed to load analytics data');
  return res.json();
}

export async function compareRoutes(start, destination, options = {}) {
  const payload = {
    start: { lat: start.lat, lon: start.lon },
    destination: { lat: destination.lat, lon: destination.lon },
    buffer_meters: options.buffer_meters || 75.0,
    risk_weight_lambda: options.risk_weight_lambda ?? 2.5,
    max_detour_ratio: options.max_detour_ratio ?? 0.30
  };

  const res = await fetch(`${API_BASE}/routes/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Route calculation failed');
  }
  return data;
}

export async function fetchModelMetrics() {
  const res = await fetch(`${API_BASE}/model/metrics`);
  if (!res.ok) throw new Error('Failed to fetch ML metrics');
  return res.json();
}

export async function triggerDataRefresh() {
  const res = await fetch(`${API_BASE}/data/refresh`, {
    method: 'POST'
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Data refresh failed');
  return data;
}
