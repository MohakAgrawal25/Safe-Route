import React from 'react';
import { BookOpen, Scale, Database, Compass, ShieldAlert, FileText, CheckCircle } from 'lucide-react';

const CATEGORY_WEIGHTS_DOC = [
  { category: 'Homicide', weight: 1.00, rationale: 'Extreme violent crime resulting in loss of life.' },
  { category: 'Criminal Sexual Assault', weight: 0.95, rationale: 'High-severity violent crime against person.' },
  { category: 'Robbery', weight: 0.85, rationale: 'Violent confrontation involving theft with force or threat.' },
  { category: 'Weapons Violation', weight: 0.80, rationale: 'Unlawful firearm possession or discharge.' },
  { category: 'Assault', weight: 0.75, rationale: 'Intentional threat or attempt of bodily harm.' },
  { category: 'Battery', weight: 0.70, rationale: 'Physical contact causing bodily injury or harm.' },
  { category: 'Burglary', weight: 0.55, rationale: 'Unlawful entry into building/structure to commit crime.' },
  { category: 'Motor Vehicle Theft', weight: 0.50, rationale: 'Grand theft of automobiles and vehicular property.' },
  { category: 'Theft', weight: 0.35, rationale: 'Larceny / non-violent property theft.' },
  { category: 'Narcotics', weight: 0.30, rationale: 'Controlled substance possession/sale.' },
  { category: 'Criminal Damage', weight: 0.25, rationale: 'Vandalism and property defacement.' },
  { category: 'Deceptive Practice', weight: 0.15, rationale: 'Fraud, counterfeit, financial non-violent offenses.' },
];

export default function AboutView() {
  return (
    <div className="h-full overflow-y-auto bg-slate-950 p-6 space-y-6 text-slate-100 max-w-5xl mx-auto">
      {/* Title */}
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2">
          <BookOpen className="w-5 h-5 text-emerald-400" />
          <span>System Methodology, Formulas & Ethical Notice</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Full technical documentation of SafeRoute AI's data sources, graph algorithms, and ethical limitations.
        </p>
      </div>

      {/* Grid: Objective & Data Portal Source */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-3">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
            <Compass className="w-4 h-4 text-emerald-400" />
            <span>1. Geographic Scope: Chicago Study Area</span>
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            SafeRoute AI focuses specifically on the configured <strong>7 km radius</strong> around Chicago's Near West Side
            (<code className="text-emerald-400">41.8700&deg; N, -87.6700&deg; W</code>).
            All crime records, pedestrian paths, and analytics are clipped strictly to this boundary to maintain high local fidelity
            without processing irrelevant outer suburban geographies.
          </p>
        </div>

        <div className="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-3">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
            <Database className="w-4 h-4 text-cyan-400" />
            <span>2. Public Data Ingestion Pipeline</span>
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Historical crime incident data is obtained from the official <strong>City of Chicago Data Portal</strong>
            (Chicago Police Department dataset API). Records are parsed, deduplicated by CPD Case Number,
            geospatially validated, and enriched with category severity weights and exponential recency decay.
          </p>
        </div>
      </div>

      {/* Mathematical Routing Formulation */}
      <div className="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
          <Scale className="w-4 h-4 text-amber-400" />
          <span>3. Mathematical Cost Formulation</span>
        </h3>
        <p className="text-xs text-slate-300 leading-relaxed">
          Rather than naively adding crime points after calculating a shortest route, SafeRoute AI evaluates edge weights directly inside Dijkstra's graph traversal algorithm using:
        </p>
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 font-mono text-emerald-400 text-xs sm:text-sm text-center">
          SegmentCost(e) = Length(e) &times; [ 1 + &lambda; &times; SegmentRisk(e) ]
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-300 pt-1">
          <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
            <span className="font-semibold text-white block mb-0.5">Length(e)</span>
            Physical metric road-segment distance in meters computed via geodesic Haversine formula.
          </div>
          <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
            <span className="font-semibold text-white block mb-0.5">&lambda; (Lambda)</span>
            User-configured crime aversion multiplier (default 2.5x) balancing walking speed vs historical exposure.
          </div>
          <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
            <span className="font-semibold text-white block mb-0.5">Max Detour Cap</span>
            Strict threshold (default 30%) preventing the algorithm from proposing unreasonably long detours.
          </div>
        </div>
      </div>

      {/* Category Severity Weights Table */}
      <div className="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
            <FileText className="w-4 h-4 text-emerald-400" />
            <span>4. Transparent Category Severity Weights</span>
          </h3>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">Scale: 0.10 to 1.00</span>
        </div>
        <p className="text-xs text-slate-400">
          Not all crimes present equal pedestrian risk. Transparent weights are assigned based on violent vs property distinctions:
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2 px-3">Crime Category</th>
                <th className="py-2 px-3">Severity Weight</th>
                <th className="py-2 px-3">Criminological Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {CATEGORY_WEIGHTS_DOC.map(row => (
                <tr key={row.category} className="hover:bg-slate-800/30">
                  <td className="py-2 px-3 font-semibold text-slate-200">{row.category}</td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                      row.weight >= 0.70 ? 'bg-rose-500/20 text-rose-300' :
                      row.weight >= 0.40 ? 'bg-amber-500/20 text-amber-300' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {row.weight.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-300">{row.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ethical Guidelines & Data Limitations */}
      <div className="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-3">
        <h3 className="text-sm font-bold text-amber-400 flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <span>5. Ethical Guidelines & Data Limitations</span>
        </h3>
        <ul className="space-y-2 text-xs text-slate-300 list-disc list-inside leading-relaxed">
          <li>
            <strong>Historical Records &ne; Future Safety:</strong> Crime patterns represent historical reported police incidents. They do not predict or guarantee individual safety on any street.
          </li>
          <li>
            <strong>Reporting Bias:</strong> Low reported crime in an area may reflect under-reporting or differences in policing presence rather than genuine safety.
          </li>
          <li>
            <strong>No Stigmatization:</strong> SafeRoute AI analyzes road segments solely for mathematical graph cost optimization. It does not label neighborhoods or communities as inherently dangerous.
          </li>
          <li>
            <strong>Relative Index (0-100):</strong> The risk index is a project-specific comparative score, not a statistical probability of victimization.
          </li>
        </ul>
      </div>
    </div>
  );
}
