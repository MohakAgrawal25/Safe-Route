import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from 'recharts';
import { BrainCircuit, CheckCircle2, AlertTriangle, Cpu, TrendingUp, Info } from 'lucide-react';
import { fetchModelMetrics } from '../services/api';

export default function ModelInsightsView() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchModelMetrics()
      .then(data => {
        setMetrics(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950 text-slate-300">
        <div className="flex flex-col items-center space-y-2">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs">Loading Model Evaluation Metrics...</p>
        </div>
      </div>
    );
  }

  const evalData = metrics?.evaluation || {};
  const featureData = Object.entries(metrics?.feature_importance || {}).map(([feature, importance]) => ({
    feature: feature.replace('_', ' ').toUpperCase(),
    importance: Math.round(importance * 1000) / 10
  })).sort((a, b) => b.importance - a.importance);

  return (
    <div className="h-full overflow-y-auto bg-slate-950 p-6 space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div>
          <div className="flex items-center space-x-2">
            <BrainCircuit className="w-5 h-5 text-emerald-400" />
            <h2 className="text-xl font-bold tracking-tight text-white">
              Explainable ML: Spatio-Temporal Intensity Regressor
            </h2>
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
              Experimental Baseline
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Evaluated on historical CPD incident patterns using strict time-split validation.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl">
          <Cpu className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-300">Architecture:</span>
          <span className="font-semibold text-white">{metrics?.model_type}</span>
        </div>
      </div>

      {/* Experimental Disclaimer Banner */}
      <div className="bg-amber-950/30 border border-amber-600/40 rounded-2xl p-4 flex items-start space-x-3 text-xs text-amber-200">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-amber-300">Model Scope & Ethical Disclaimer</div>
          <p className="text-[11px] text-amber-200/90 leading-relaxed">
            {metrics?.disclaimer}
          </p>
        </div>
      </div>

      {/* Evaluation Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-lg">
          <div className="text-xs text-slate-400 font-medium">Model Test MAE</div>
          <div className="text-2xl font-black text-emerald-400 mt-1">
            {evalData.test_mae !== undefined ? evalData.test_mae : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Mean Absolute Error</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-lg">
          <div className="text-xs text-slate-400 font-medium">Baseline Mean MAE</div>
          <div className="text-2xl font-black text-slate-300 mt-1">
            {evalData.baseline_mean_mae !== undefined ? evalData.baseline_mean_mae : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Historical Mean Predictor</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-lg">
          <div className="text-xs text-slate-400 font-medium">Test RMSE</div>
          <div className="text-2xl font-black text-cyan-400 mt-1">
            {evalData.test_rmse !== undefined ? evalData.test_rmse : 'N/A'}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Root Mean Squared Error</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-lg">
          <div className="text-xs text-slate-400 font-medium">Validation Split</div>
          <div className="text-sm font-bold text-white mt-2">75% Train / 25% Test</div>
          <div className="text-[10px] text-emerald-400 mt-1">Chronological Time Split</div>
        </div>
      </div>

      {/* Feature Importance & Methodology Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Feature Importance Bar Chart */}
        <div className="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200">Feature Importance Breakdown</h3>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">Gini Importance (%)</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={featureData} margin={{ top: 10, right: 20, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis dataKey="feature" type="category" stroke="#94a3b8" tick={{ fontSize: 10 }} width={85} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                />
                <Bar dataKey="importance" fill="#10b981" radius={[0, 4, 4, 0]}>
                  {featureData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#10b981' : '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Methodology & Target Leakage Prevention */}
        <div className="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-4">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Methodology & Target Leakage Prevention</span>
          </h3>

          <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="font-semibold text-white block mb-1">1. Chronological Splitting</span>
              Observations are strictly sorted by date. The model is trained solely on past time windows and tested on subsequent future windows to prevent data leakage.
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="font-semibold text-white block mb-1">2. Cyclical Temporal Encodings</span>
              Hour-of-day and day-of-week are converted into continuous sine and cosine cyclic transformations:
              <code className="text-emerald-400 block mt-1 text-[11px] font-mono">
                hour_sin = sin(2&pi; &times; hour / 24), dow_cos = cos(2&pi; &times; dow / 7)
              </code>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
              <span className="font-semibold text-white block mb-1">3. Fallback Gracefulness</span>
              If the ML model is disabled or uninitialized, SafeRoute AI routes immediately via the spatial index kernel density estimates with zero downtime.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
