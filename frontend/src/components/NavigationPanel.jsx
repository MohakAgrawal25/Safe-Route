import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Navigation, Sliders, ArrowUpDown, ChevronDown, ChevronUp, AlertCircle, Sparkles, RefreshCw } from 'lucide-react';
import RouteComparisonCard from './RouteComparisonCard';

// Popular Chicago Landmarks spanning the Middle & Central 7 km Study Area
const CHICAGO_LANDMARKS = [
  { name: 'Millennium Park (Cloud Gate)', lat: 41.8826, lon: -87.6233 },
  { name: 'Willis Tower (Skydeck)', lat: 41.8789, lon: -87.6359 },
  { name: 'United Center (Near West Side)', lat: 41.8807, lon: -87.6742 },
  { name: 'UIC Campus (Halsted & Taylor)', lat: 41.8700, lon: -87.6500 },
  { name: 'Illinois Medical District', lat: 41.8720, lon: -87.6770 },
  { name: 'Pilsen Arts District (18th & Halsted)', lat: 41.8576, lon: -87.6475 },
  { name: 'Wicker Park (Damen & Milwaukee)', lat: 41.9098, lon: -87.6774 },
  { name: 'Fulton Market (West Loop)', lat: 41.8860, lon: -87.6475 },
  { name: 'Garfield Park Conservatory', lat: 41.8860, lon: -87.7170 },
  { name: 'Union Station (Canal & Adams)', lat: 41.8787, lon: -87.6403 },
  { name: 'Chinatown Square (Cermak Rd)', lat: 41.8530, lon: -87.6320 },
  { name: 'Navy Pier Promenade', lat: 41.8917, lon: -87.6043 },
];

export default function NavigationPanel({
  startPoint,
  destPoint,
  setStartPoint,
  setDestPoint,
  activeSelecting,
  setActiveSelecting,
  onCalculateRoute,
  routeResult,
  isLoading,
  errorMessage
}) {
  const [showSettings, setShowSettings] = useState(true); // Open by default for easy tuning
  const [riskLambda, setRiskLambda] = useState(2.5);
  const [maxDetour, setMaxDetour] = useState(30);
  const [bufferMeters, setBufferMeters] = useState(75);

  const debounceTimer = useRef(null);

  const handlePresetSelect = (landmark, target) => {
    if (target === 'start') {
      setStartPoint({ lat: landmark.lat, lon: landmark.lon, name: landmark.name });
    } else {
      setDestPoint({ lat: landmark.lat, lon: landmark.lon, name: landmark.name });
    }
  };

  const handleSwap = () => {
    const temp = startPoint;
    setStartPoint(destPoint);
    setDestPoint(temp);
  };

  // Trigger recalculation with given parameters
  const triggerRecalculate = (lambdaVal, detourVal, bufferVal) => {
    if (!startPoint || !destPoint) return;
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    debounceTimer.current = setTimeout(() => {
      onCalculateRoute({
        risk_weight_lambda: lambdaVal,
        max_detour_ratio: detourVal / 100.0,
        buffer_meters: bufferVal
      });
    }, 200);
  };

  const handleLambdaChange = (val) => {
    const num = parseFloat(val);
    setRiskLambda(num);
    triggerRecalculate(num, maxDetour, bufferMeters);
  };

  const handleDetourChange = (val) => {
    const num = parseInt(val);
    setMaxDetour(num);
    triggerRecalculate(riskLambda, num, bufferMeters);
  };

  const handleBufferChange = (val) => {
    const num = parseInt(val);
    setBufferMeters(num);
    triggerRecalculate(riskLambda, maxDetour, num);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!startPoint || !destPoint) return;
    onCalculateRoute({
      risk_weight_lambda: riskLambda,
      max_detour_ratio: maxDetour / 100.0,
      buffer_meters: bufferMeters
    });
  };

  return (
    <aside className="navigation-sidebar w-full md:w-[420px] h-full backdrop-blur-xl border-r border-slate-800 text-slate-100 flex flex-col shadow-2xl z-10 overflow-y-auto">
      <div className="p-4 space-y-4 flex-1">
        {/* Origin & Destination Inputs */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="bg-slate-950/60 p-3 rounded-2xl border border-slate-800/80 space-y-3">
            {/* Start / Origin */}
            <div>
              <div className="flex items-center justify-between text-xs font-semibold mb-1">
                <span className="flex items-center space-x-1.5 text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  <span>Origin (Start Location)</span>
                </span>
                <button
                  type="button"
                  onClick={() => setActiveSelecting(activeSelecting === 'start' ? null : 'start')}
                  className={`text-[10px] px-2 py-0.5 rounded transition-all ${
                    activeSelecting === 'start'
                      ? 'bg-emerald-500 text-slate-950 font-bold animate-pulse'
                      : 'text-slate-400 hover:text-emerald-400 bg-slate-800'
                  }`}
                >
                  {activeSelecting === 'start' ? 'Click on map...' : 'Set on map'}
                </button>
              </div>

              <select
                className="w-full bg-slate-900 text-slate-200 text-xs rounded-lg px-2.5 py-2 border border-slate-700/80 focus:outline-none focus:border-emerald-500"
                value=""
                onChange={(e) => {
                  const item = CHICAGO_LANDMARKS.find(l => l.name === e.target.value);
                  if (item) handlePresetSelect(item, 'start');
                }}
              >
                <option value="" disabled>Choose Chicago landmark or click map...</option>
                {CHICAGO_LANDMARKS.map(l => (
                  <option key={`start-${l.name}`} value={l.name}>{l.name}</option>
                ))}
              </select>

              {startPoint && (
                <div className="mt-1 text-[11px] text-slate-400 flex items-center justify-between">
                  <span className="truncate">{startPoint.name || 'Custom Coordinate'}</span>
                  <span className="text-slate-500 font-mono text-[10px]">
                    {startPoint.lat.toFixed(4)}, {startPoint.lon.toFixed(4)}
                  </span>
                </div>
              )}
            </div>

            {/* Swap Button */}
            <div className="flex justify-center -my-1">
              <button
                type="button"
                onClick={handleSwap}
                title="Swap Origin and Destination"
                className="p-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-all border border-slate-700"
              >
                <ArrowUpDown className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Destination */}
            <div>
              <div className="flex items-center justify-between text-xs font-semibold mb-1">
                <span className="flex items-center space-x-1.5 text-rose-400">
                  <span className="w-2 h-2 rounded-full bg-rose-400"></span>
                  <span>Destination (Goal)</span>
                </span>
                <button
                  type="button"
                  onClick={() => setActiveSelecting(activeSelecting === 'dest' ? null : 'dest')}
                  className={`text-[10px] px-2 py-0.5 rounded transition-all ${
                    activeSelecting === 'dest'
                      ? 'bg-rose-500 text-slate-950 font-bold animate-pulse'
                      : 'text-slate-400 hover:text-rose-400 bg-slate-800'
                  }`}
                >
                  {activeSelecting === 'dest' ? 'Click on map...' : 'Set on map'}
                </button>
              </div>

              <select
                className="w-full bg-slate-900 text-slate-200 text-xs rounded-lg px-2.5 py-2 border border-slate-700/80 focus:outline-none focus:border-rose-500"
                value=""
                onChange={(e) => {
                  const item = CHICAGO_LANDMARKS.find(l => l.name === e.target.value);
                  if (item) handlePresetSelect(item, 'dest');
                }}
              >
                <option value="" disabled>Choose Chicago landmark or click map...</option>
                {CHICAGO_LANDMARKS.map(l => (
                  <option key={`dest-${l.name}`} value={l.name}>{l.name}</option>
                ))}
              </select>

              {destPoint && (
                <div className="mt-1 text-[11px] text-slate-400 flex items-center justify-between">
                  <span className="truncate">{destPoint.name || 'Custom Coordinate'}</span>
                  <span className="text-slate-500 font-mono text-[10px]">
                    {destPoint.lat.toFixed(4)}, {destPoint.lon.toFixed(4)}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Quick Routing Parameters Accordion */}
          <div className="bg-slate-950/60 rounded-xl border border-slate-800/80 overflow-hidden text-xs">
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className="w-full px-3 py-2 flex items-center justify-between text-slate-200 hover:bg-slate-800/40 transition-colors font-semibold"
            >
              <span className="flex items-center space-x-1.5">
                <Sliders className="w-3.5 h-3.5 text-emerald-400" />
                <span>Safety & Detour Parameters (Live Tuning)</span>
              </span>
              {showSettings ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
            </button>

            {showSettings && (
              <div className="p-3 border-t border-slate-800/80 space-y-3.5 bg-slate-950/90">
                {/* Lambda Slider */}
                <div>
                  <div className="flex justify-between text-[11px] text-slate-300 mb-1">
                    <span>Crime Aversion Multiplier (&lambda;):</span>
                    <span className="font-bold text-emerald-400 text-xs">{riskLambda.toFixed(1)}x</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="6.0"
                    step="0.5"
                    value={riskLambda}
                    onChange={(e) => handleLambdaChange(e.target.value)}
                    className="w-full accent-emerald-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
                  />
                  <div className="flex justify-between text-[9px] text-slate-500 mt-0.5">
                    <span>0.0 (Shortest Only)</span>
                    <span>2.5 (Balanced)</span>
                    <span>6.0 (Max Safety)</span>
                  </div>
                </div>

                {/* Detour Slider */}
                <div>
                  <div className="flex justify-between text-[11px] text-slate-300 mb-1">
                    <span>Maximum Allowed Detour:</span>
                    <span className="font-bold text-amber-400 text-xs">+{maxDetour}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="50"
                    step="5"
                    value={maxDetour}
                    onChange={(e) => handleDetourChange(e.target.value)}
                    className="w-full accent-amber-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
                  />
                  <div className="flex justify-between text-[9px] text-slate-500 mt-0.5">
                    <span>10% (Direct)</span>
                    <span>30% (Standard)</span>
                    <span>50% (Wide Detour)</span>
                  </div>
                </div>

                {/* Buffer Slider */}
                <div>
                  <div className="flex justify-between text-[11px] text-slate-300 mb-1">
                    <span>Segment Crime Buffer:</span>
                    <span className="font-bold text-cyan-400 text-xs">{bufferMeters} meters</span>
                  </div>
                  <input
                    type="range"
                    min="30"
                    max="150"
                    step="15"
                    value={bufferMeters}
                    onChange={(e) => handleBufferChange(e.target.value)}
                    className="w-full accent-cyan-500 cursor-pointer h-2 bg-slate-800 rounded-lg"
                  />
                  <div className="flex justify-between text-[9px] text-slate-500 mt-0.5">
                    <span>30m (Immediate Sidewalk)</span>
                    <span>150m (Neighborhood Block)</span>
                  </div>
                </div>

                <div className="text-[10px] text-slate-400 bg-slate-900/80 p-2 rounded-lg border border-slate-800/80">
                  <span className="text-emerald-400 font-semibold">Tip:</span> Moving any slider immediately recalculates Route B to show the impact of safety aversion, detour tolerance, and buffer radius in real time.
                </div>
              </div>
            )}
          </div>

          {/* Calculate Button */}
          <button
            type="submit"
            disabled={!startPoint || !destPoint || isLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/25 transition-all flex items-center justify-center space-x-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></div>
                <span>Computing Dual Paths...</span>
              </>
            ) : (
              <>
                <Navigation className="w-4 h-4 fill-slate-950" />
                <span>Recalculate Routes</span>
              </>
            )}
          </button>
        </form>

        {/* Error Banner */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/50 text-rose-200 text-xs flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="leading-snug">{errorMessage}</div>
          </div>
        )}

        {/* Dual Route Comparison Results */}
        {routeResult && <RouteComparisonCard result={routeResult} />}

        {/* Empty State Instructions when no route is calculated yet */}
        {!routeResult && !isLoading && (
          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 text-xs text-slate-400 space-y-2 text-center mt-6">
            <Sparkles className="w-5 h-5 text-emerald-400 mx-auto" />
            <div className="font-semibold text-slate-200">How to Navigate</div>
            <p className="text-[11px] leading-relaxed">
              Select origin and destination from the landmarks dropdown above, or click anywhere inside the green 7 km Chicago study area on the map.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
