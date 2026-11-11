import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Circle, Polyline, Marker, Popup, CircleMarker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Layers, Compass, AlertTriangle, ShieldCheck, Route, Eye, EyeOff } from 'lucide-react';

// Fix standard Leaflet default icon issues in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom Origin Marker Icon (Emerald Glow)
const startIcon = new L.DivIcon({
  className: 'custom-start-marker',
  html: `
    <div style="
      background: #10b981;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 3px solid #ffffff;
      box-shadow: 0 0 14px rgba(16, 185, 129, 0.9);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #022c22;
      font-weight: 800;
      font-size: 11px;
    ">A</div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

// Custom Destination Marker Icon (Ruby Glow)
const destIcon = new L.DivIcon({
  className: 'custom-dest-marker',
  html: `
    <div style="
      background: #ef4444;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 3px solid #ffffff;
      box-shadow: 0 0 14px rgba(239, 68, 68, 0.9);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #450a0a;
      font-weight: 800;
      font-size: 11px;
    ">B</div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

// Helper component to handle clicks on the map
function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click: (e) => {
      onMapClick(e.latlng);
    }
  });
  return null;
}

// Helper component to auto-fit bounds when routes change
function RouteBoundsFitter({ routeResult }) {
  const map = useMap();
  useEffect(() => {
    if (!routeResult) return;
    const coords = [
      ...(routeResult.shortest_route?.coordinates || []),
      ...(routeResult.crime_aware_route?.coordinates || [])
    ];
    if (coords.length > 2) {
      const bounds = L.latLngBounds(coords.map(c => [c[0], c[1]]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    }
  }, [routeResult, map]);
  return null;
}

function routesHaveSameCoordinates(routeA, routeB) {
  const coordinatesA = routeA?.coordinates || [];
  const coordinatesB = routeB?.coordinates || [];
  return coordinatesA.length === coordinatesB.length
    && coordinatesA.every((point, index) => (
      point[0] === coordinatesB[index][0]
      && point[1] === coordinatesB[index][1]
    ));
}

export default function InteractiveMap({
  studyArea,
  startPoint,
  destPoint,
  onLocationSelect,
  routeResult,
  crimes = [],
  hotspots = [],
  isCalculating
}) {
  // Default center matches config.py: Near West / UIC / Medical District / West Town (middle of city)
  const centerLat = studyArea?.center?.lat || 41.8700;
  const centerLon = studyArea?.center?.lon || -87.6700;
  const radius = studyArea?.radius_meters || 7000;
  const sameRoute = routesHaveSameCoordinates(
    routeResult?.shortest_route,
    routeResult?.crime_aware_route
  );

  // Layer Visibility States
  const [showCrimes, setShowCrimes] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [showBoundary, setShowBoundary] = useState(true);
  const [showShortest, setShowShortest] = useState(true);
  const [showSafe, setShowSafe] = useState(true);

  const getCrimeColor = (category, weight) => {
    if (weight >= 0.70) return '#ef4444'; // Red for violent
    if (weight >= 0.35) return '#f59e0b'; // Amber for property
    return '#38bdf8'; // Blue for minor
  };

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden">
      <MapContainer
        key={`map-${centerLat.toFixed(4)}-${centerLon.toFixed(4)}`}
        center={[centerLat, centerLon]}
        zoom={12}
        className="w-full h-full"
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapClickHandler onMapClick={onLocationSelect} />
        <RouteBoundsFitter routeResult={routeResult} />

        {/* Configured study area circular boundary */}
        {showBoundary && (
          <Circle
            center={[centerLat, centerLon]}
            radius={radius}
            pathOptions={{
              color: '#10b981',
              weight: 2,
              dashArray: '6, 8',
              fillColor: '#10b981',
              fillOpacity: 0.04
            }}
          >
            <Popup>
              <div className="p-1 text-xs">
                <p className="font-bold text-emerald-400">Chicago 7 km Study Area Boundary</p>
                <p className="text-slate-300">Center: {centerLat.toFixed(4)}, {centerLon.toFixed(4)}</p>
                <p className="text-slate-400">All crime filtering and route options are strictly confined inside this circle.</p>
              </div>
            </Popup>
          </Circle>
        )}

        {/* Crime Hotspots Layer */}
        {showHotspots && hotspots.map((h, idx) => (
          <CircleMarker
            key={`hotspot-${idx}`}
            center={[h.lat, h.lon]}
            radius={Math.min(11, 3 + Math.log2(h.count) * 0.7)}
            pathOptions={{
              color: '#fb923c',
              weight: 0.8,
              opacity: 0.42,
              fillColor: '#f97316',
              fillOpacity: 0.12
            }}
          >
            <Popup>
              <div className="text-xs p-1">
                <p className="font-bold text-rose-400">Crime Hotspot Cluster</p>
                <p className="text-slate-200">Total incidents: <span className="font-semibold">{h.count}</span></p>
                <p className="text-slate-300">Dominant crime: <span className="text-amber-300 font-medium">{h.dominant_crime}</span></p>
                <p className="text-slate-400">Exposure intensity: {h.intensity}</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* Individual Crime Incident Markers */}
        {showCrimes && crimes.slice(0, 300).map((c) => (
          <CircleMarker
            key={`crime-${c.id || c.incident_id}`}
            center={[c.latitude, c.longitude]}
            radius={4}
            pathOptions={{
              color: '#ffffff',
              weight: 0.8,
              fillColor: getCrimeColor(c.primary_type, c.severity_weight),
              fillOpacity: 0.85
            }}
          >
            <Popup>
              <div className="text-xs p-1 max-w-[220px]">
                <div className="flex items-center justify-between border-b border-slate-700 pb-1 mb-1">
                  <span className="font-bold text-slate-100">{c.primary_type}</span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-semibold text-white"
                    style={{ backgroundColor: getCrimeColor(c.primary_type, c.severity_weight) }}
                  >
                    Weight {c.severity_weight}
                  </span>
                </div>
                <p className="text-slate-300">{c.description || 'No detailed description'}</p>
                <p className="text-slate-400 mt-1">Block: {c.block || 'N/A'}</p>
                <p className="text-slate-400">Date: {new Date(c.date).toLocaleDateString()}</p>
                <p className="text-slate-500 text-[10px] mt-1">Arrest: {c.arrest ? 'Yes' : 'No'} | Domestic: {c.domestic ? 'Yes' : 'No'}</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* Shortest Route (Route A - Blue) */}
        {showShortest && routeResult?.shortest_route?.coordinates && (
          <Polyline
            positions={routeResult.shortest_route.coordinates}
            pathOptions={{
              color: '#3b82f6',
              weight: 5,
              opacity: 0.85,
              lineCap: 'round',
              lineJoin: 'round'
            }}
          >
            <Popup>
              <div className="text-xs p-1">
                <p className="font-bold text-blue-400">Route A: Shortest Route</p>
                <p className="text-slate-200">Distance: {routeResult.shortest_route.distance_meters}m</p>
                <p className="text-slate-200">Walking Time: {routeResult.shortest_route.walking_time_formatted}</p>
                <p className="text-amber-400 font-semibold">Crime Exposure Index: {routeResult.shortest_route.historical_risk_index}/100</p>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Crime-Aware Safe Route (Route B - Emerald Glowing) */}
        {showSafe && routeResult?.crime_aware_route?.coordinates && (
          <Polyline
            positions={routeResult.crime_aware_route.coordinates}
            pathOptions={{
              color: '#10b981',
              weight: 6,
              opacity: 0.95,
              lineCap: 'round',
              lineJoin: 'round',
              dashArray: sameRoute ? '7, 10' : undefined
            }}
          >
            <Popup>
              <div className="text-xs p-1">
                <p className="font-bold text-emerald-400">Route B: SafeRoute AI Recommended</p>
                <p className="text-slate-200">Distance: {routeResult.crime_aware_route.distance_meters}m</p>
                <p className="text-slate-200">Walking Time: {routeResult.crime_aware_route.walking_time_formatted}</p>
                <p className="text-emerald-400 font-semibold">Crime Exposure Index: {routeResult.crime_aware_route.historical_risk_index}/100</p>
                <p className="text-slate-300 text-[11px] mt-1">
                  {routeResult.risk_reduction_percentage > 0
                    ? `${routeResult.risk_reduction_percentage}% lower historical exposure`
                    : sameRoute
                      ? 'Same street path as Route A'
                      : 'Distinct alternative; no lower exposure found'}
                </p>
              </div>
            </Popup>
          </Polyline>
        )}

        {/* Origin Marker */}
        {startPoint && (
          <Marker position={[startPoint.lat, startPoint.lon]} icon={startIcon}>
            <Popup>
              <div className="text-xs p-1 font-semibold text-emerald-400">
                Origin (Start Location)
                <div className="text-slate-300 font-normal">{startPoint.lat.toFixed(5)}, {startPoint.lon.toFixed(5)}</div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Destination Marker */}
        {destPoint && (
          <Marker position={[destPoint.lat, destPoint.lon]} icon={destIcon}>
            <Popup>
              <div className="text-xs p-1 font-semibold text-rose-400">
                Destination (Goal)
                <div className="text-slate-300 font-normal">{destPoint.lat.toFixed(5)}, {destPoint.lon.toFixed(5)}</div>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>

      {/* Floating Map Controls Top-Right */}
      <div className="map-controls absolute top-4 right-4 z-[1000] flex flex-col space-y-2">
        {/* Layer Toggle Panel */}
        <div className="map-glass-panel p-3 text-xs space-y-2.5 min-w-[180px]">
          <div className="font-semibold text-slate-300 flex items-center space-x-1.5 pb-1 border-b border-slate-800">
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            <span>Map Layers</span>
          </div>

          <label className="flex items-center justify-between cursor-pointer text-slate-300 hover:text-white">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block"></span>
              <span>Route B: Alternative</span>
            </span>
            <input
              type="checkbox"
              checked={showSafe}
              onChange={(e) => setShowSafe(e.target.checked)}
              className="accent-emerald-500 rounded"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer text-slate-300 hover:text-white">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block"></span>
              <span>Shortest Route (A)</span>
            </span>
            <input
              type="checkbox"
              checked={showShortest}
              onChange={(e) => setShowShortest(e.target.checked)}
              className="accent-blue-500 rounded"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer text-slate-300 hover:text-white">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
              <span>Crime Hotspots</span>
            </span>
            <input
              type="checkbox"
              checked={showHotspots}
              onChange={(e) => setShowHotspots(e.target.checked)}
              className="accent-rose-500 rounded"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer text-slate-300 hover:text-white">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block"></span>
              <span>Crime Incidents</span>
            </span>
            <input
              type="checkbox"
              checked={showCrimes}
              onChange={(e) => setShowCrimes(e.target.checked)}
              className="accent-amber-500 rounded"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer text-slate-300 hover:text-white">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full border border-emerald-400 border-dashed inline-block"></span>
              <span>7km Boundary</span>
            </span>
            <input
              type="checkbox"
              checked={showBoundary}
              onChange={(e) => setShowBoundary(e.target.checked)}
              className="accent-emerald-500 rounded"
            />
          </label>
        </div>

      </div>

      {/* Floating Map Legend Bottom-Right */}
      <div className="map-legend absolute bottom-6 right-4 z-[1000] map-glass-panel p-3 text-[11px] max-w-[220px]">
        <div className="font-semibold text-slate-200 mb-2 flex items-center space-x-1">
          <Compass className="w-3.5 h-3.5 text-emerald-400" />
          <span>Navigation Legend</span>
        </div>
        <div className="space-y-1.5 text-slate-300">
          <div className="flex items-center space-x-2">
            <span className="w-4 h-1.5 bg-emerald-500 rounded-full"></span>
            <span>Route B: Alternative / lower exposure</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-4 h-1.5 bg-blue-500 rounded-full"></span>
            <span>Route A: Shortest Path</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            <span>Violent Crime Incident</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span>Property Crime Incident</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full border border-emerald-400 border-dashed"></span>
            <span>7 km Study Perimeter</span>
          </div>
        </div>
      </div>

      {/* Loading Indicator */}
      {isCalculating && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[1001] bg-slate-900/95 backdrop-blur-md px-5 py-4 rounded-2xl border border-emerald-500/40 shadow-2xl flex items-center space-x-3 text-slate-100">
          <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <div>
            <div className="font-bold text-sm">Evaluating Crime-Sensitive Paths...</div>
            <div className="text-xs text-slate-400">Balancing distance cost & historical exposure</div>
          </div>
        </div>
      )}
    </div>
  );
}
