import React from 'react';
import { ShieldCheck, ShieldAlert, Clock, ArrowRight, TrendingDown, AlertCircle, Info, Footprints } from 'lucide-react';

export default function RouteComparisonCard({ result }) {
  if (!result) return null;

  const shortest = result.shortest_route;
  const safe = result.crime_aware_route;
  const detourPct = result.detour_percentage;
  const riskReductionPct = result.risk_reduction_percentage;
  const isAlternativeSame = shortest.coordinates?.length === safe.coordinates?.length
    && shortest.coordinates?.every((point, index) => (
      point[0] === safe.coordinates[index][0]
      && point[1] === safe.coordinates[index][1]
    ));
  const hasLowerExposure = riskReductionPct > 0;

  return (
    <div className="space-y-3 mt-4 text-xs">
      {/* Route Cards Grid */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* Route B: Safe Route Card */}
        <div className="bg-emerald-950/40 border-2 border-emerald-500/80 rounded-xl p-3 shadow-lg shadow-emerald-500/10 relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-emerald-500 text-slate-950 font-bold px-2 py-0.5 rounded-bl-lg text-[9px] uppercase tracking-wider">
            {hasLowerExposure ? 'Lower Exposure' : 'Alternative'}
          </div>
          <div className="flex items-center space-x-1.5 text-emerald-400 font-bold mb-2">
            <ShieldCheck className="w-4 h-4" />
            <span>Route B: Crime-Aware</span>
          </div>

          <div className="space-y-1.5 text-slate-200">
            <div className="flex justify-between items-baseline">
              <span className="text-slate-400">Distance</span>
              <span className="font-bold text-sm text-slate-100">{safe.distance_meters} m</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-slate-400">Walking Time</span>
              <span className="font-semibold text-emerald-300">{safe.walking_time_formatted}</span>
            </div>
            <div className="flex justify-between items-baseline pt-1 border-t border-emerald-900/60">
              <span className="text-slate-400">Risk Index</span>
              <span className="font-extrabold text-base text-emerald-400">
                {safe.historical_risk_index}
                <span className="text-[10px] font-normal text-slate-500">/100</span>
              </span>
            </div>
            <div className="flex justify-between items-baseline text-[11px]">
              <span className="text-slate-400">Recorded Incidents</span>
              <span className="text-slate-300 font-medium">{safe.incident_exposure_count}</span>
            </div>
          </div>
        </div>

        {/* Route A: Shortest Route Card */}
        <div className="bg-slate-900/60 border border-blue-500/50 rounded-xl p-3 shadow-md">
          <div className="flex items-center space-x-1.5 text-blue-400 font-bold mb-2">
            <Footprints className="w-4 h-4" />
            <span>Route A: Shortest</span>
          </div>

          <div className="space-y-1.5 text-slate-200">
            <div className="flex justify-between items-baseline">
              <span className="text-slate-400">Distance</span>
              <span className="font-bold text-sm text-slate-100">{shortest.distance_meters} m</span>
            </div>
            <div className="flex justify-between items-baseline">
              <span className="text-slate-400">Walking Time</span>
              <span className="font-semibold text-blue-300">{shortest.walking_time_formatted}</span>
            </div>
            <div className="flex justify-between items-baseline pt-1 border-t border-slate-800">
              <span className="text-slate-400">Risk Index</span>
              <span className="font-extrabold text-base text-amber-400">
                {shortest.historical_risk_index}
                <span className="text-[10px] font-normal text-slate-500">/100</span>
              </span>
            </div>
            <div className="flex justify-between items-baseline text-[11px]">
              <span className="text-slate-400">Recorded Incidents</span>
              <span className="text-slate-300 font-medium">{shortest.incident_exposure_count}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Trade-off Comparison Bar */}
      <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800 flex items-center justify-between text-[11px]">
        <div className="flex items-center space-x-1.5">
          <TrendingDown className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-300">Safety Improvement:</span>
          <span className="font-bold text-emerald-400">
            {hasLowerExposure ? `-${riskReductionPct}%` : 'No lower-risk route found'}
          </span>
        </div>
        <div className="flex items-center space-x-1 text-slate-400">
          <span>Detour:</span>
          <span className={`font-semibold ${detourPct > 15 ? 'text-amber-400' : 'text-slate-200'}`}>
            +{detourPct}% ({Math.max(0, Math.round(safe.distance_meters - shortest.distance_meters))}m)
          </span>
        </div>
      </div>

      {/* AI Explanation Box */}
      <div className="bg-slate-950/70 rounded-xl p-3 border border-slate-800 space-y-1.5">
        <div className="font-semibold text-slate-200 flex items-center space-x-1.5 text-xs">
          <Info className="w-3.5 h-3.5 text-teal-400" />
          <span>{isAlternativeSame ? 'Route comparison:' : 'Why this route differs:'}</span>
        </div>
        <p className="text-slate-300 leading-relaxed text-[11px]">
          {result.explanation}
        </p>

        {/* Categories Avoided chips */}
        {safe.top_categories_along_route && Object.keys(safe.top_categories_along_route).length > 0 && (
          <div className="pt-1.5 mt-1 border-t border-slate-800/80 flex flex-wrap gap-1 items-center">
            <span className="text-[10px] text-slate-400">Incident breakdown along safe path:</span>
            {Object.entries(safe.top_categories_along_route).slice(0, 4).map(([cat, count]) => (
              <span key={cat} className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded font-medium">
                {cat}: {count}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Uncertainty Alert if applicable */}
      {result.uncertainty_warning && (
        <div className="bg-amber-950/30 border border-amber-600/40 rounded-xl p-2.5 flex items-start space-x-2 text-[11px] text-amber-200">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>{result.uncertainty_warning}</span>
        </div>
      )}

      {/* Mandatory Ethical Disclaimer */}
      <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800 text-[10px] text-slate-400 leading-normal">
        <span className="font-semibold text-slate-300 block mb-0.5">Notice & Research Disclaimer:</span>
        {result.disclaimer}
      </div>
    </div>
  );
}
