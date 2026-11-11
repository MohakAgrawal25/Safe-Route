import React, { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import InteractiveMap from './components/InteractiveMap';
import NavigationPanel from './components/NavigationPanel';
import { fetchHealth, fetchStudyArea, fetchCrimes, fetchHotspots, compareRoutes, triggerDataRefresh } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('navigation');
  const [healthData, setHealthData] = useState(null);
  const [studyArea, setStudyArea] = useState(null);
  const [crimes, setCrimes] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Navigation State with intuitive Chicago Loop defaults (within 7km study area centered at 41.8700, -87.6700)
  const [startPoint, setStartPoint] = useState({
    name: 'Willis Tower (Skydeck)',
    lat: 41.8789,
    lon: -87.6359
  });
  const [destPoint, setDestPoint] = useState({
    name: 'UIC Campus (Halsted & Taylor)',
    lat: 41.8700,
    lon: -87.6500
  });
  const [activeSelecting, setActiveSelecting] = useState(null);
  const [routeResult, setRouteResult] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Initial data loading
  useEffect(() => {
    Promise.all([
      fetchHealth().catch(() => null),
      fetchStudyArea().catch(() => null),
      fetchCrimes('', 350).catch(() => ({ data: [] })),
      fetchHotspots().catch(() => [])
    ]).then(([health, study, crimeData, hotspotList]) => {
      if (health) setHealthData(health);
      if (study) setStudyArea(study);
      if (crimeData?.data) setCrimes(crimeData.data);
      if (hotspotList) setHotspots(hotspotList);

      // Auto-calculate initial demo route between Millennium Park & Willis Tower
      handleCalculateRoute();
    });
  }, []);

  const handleCalculateRoute = async (options = {}) => {
    if (!startPoint || !destPoint) return;
    setIsCalculating(true);
    setErrorMessage(null);

    try {
      const result = await compareRoutes(startPoint, destPoint, options);
      setRouteResult(result);
    } catch (err) {
      console.error('Route calculation error:', err);
      setErrorMessage(err.message || 'Route calculation failed');
    } finally {
      setIsCalculating(false);
    }
  };

  const handleMapLocationSelect = (latlng) => {
    setErrorMessage(null);

    // Validate that selected points stay inside the configured circular boundary.
    const centerLat = studyArea?.center?.lat || 41.8700;
    const centerLon = studyArea?.center?.lon || -87.6700;

    // Approximate distance check in degrees
    const dLat = (latlng.lat - centerLat) * 111320;
    const dLon = (latlng.lng - centerLon) * (111320 * Math.cos(centerLat * Math.PI / 180));
    const distMeters = Math.sqrt(dLat * dLat + dLon * dLon);

    const radiusMeters = studyArea?.radius_meters || 7000;
    if (distMeters > radiusMeters) {
      setErrorMessage(
        `Selected point is ${Math.round(distMeters)}m from center, which exceeds the ${(radiusMeters / 1000).toFixed(1)} km Chicago study boundary. Please click inside the circular perimeter.`
      );
      return;
    }

    const newCoord = {
      name: `Custom (${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)})`,
      lat: latlng.lat,
      lon: latlng.lng
    };

    if (activeSelecting === 'start') {
      setStartPoint(newCoord);
      setActiveSelecting(null);
    } else if (activeSelecting === 'dest') {
      setDestPoint(newCoord);
      setActiveSelecting(null);
    } else {
      // Default click flow: set start if not set, else dest, else reset
      if (!startPoint) {
        setStartPoint(newCoord);
      } else if (!destPoint) {
        setDestPoint(newCoord);
      } else {
        setStartPoint(newCoord);
        setDestPoint(null);
        setRouteResult(null);
      }
    }
  };

  const handleRefreshData = async () => {
    setIsRefreshing(true);
    try {
      await triggerDataRefresh();
      const [health, crimeData, hotspotList] = await Promise.all([
        fetchHealth(),
        fetchCrimes('', 350),
        fetchHotspots()
      ]);
      setHealthData(health);
      if (crimeData?.data) setCrimes(crimeData.data);
      if (hotspotList) setHotspots(hotspotList);
      if (startPoint && destPoint) {
        handleCalculateRoute();
      }
    } catch (err) {
      console.error('Data refresh error:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-slate-950 select-none overflow-hidden font-sans">
      {/* Navigation Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthData={healthData}
        onRefreshData={handleRefreshData}
        isRefreshing={isRefreshing}
      />

      {/* Main Workspace */}
      <main className="flex-1 relative overflow-hidden flex">
        {activeTab === 'navigation' && (
          <div className="w-full h-full flex flex-col md:flex-row relative">
            {/* Sidebar Navigation Panel */}
            <NavigationPanel
              startPoint={startPoint}
              destPoint={destPoint}
              setStartPoint={setStartPoint}
              setDestPoint={setDestPoint}
              activeSelecting={activeSelecting}
              setActiveSelecting={setActiveSelecting}
              onCalculateRoute={handleCalculateRoute}
              routeResult={routeResult}
              isLoading={isCalculating}
              errorMessage={errorMessage}
            />

            {/* Interactive Map Area */}
            <div className="map-workspace flex-1 h-full relative">
              <InteractiveMap
                studyArea={studyArea}
                startPoint={startPoint}
                destPoint={destPoint}
                onLocationSelect={handleMapLocationSelect}
                routeResult={routeResult}
                crimes={crimes}
                hotspots={hotspots}
                isCalculating={isCalculating}
              />
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
