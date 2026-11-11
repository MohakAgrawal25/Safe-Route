import React from 'react';
import { Shield, Navigation, RefreshCw } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, healthData, onRefreshData, isRefreshing }) {
  return (
    <header className="app-header bg-slate-900/90 backdrop-blur-md border-b border-slate-800 text-slate-100 px-4 py-3 flex items-center justify-between z-20 sticky top-0 shadow-lg">
      <div className="app-brand flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('navigation')}>
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
          <Shield className="w-5 h-5 text-slate-950 stroke-[2.5]" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="app-brand-title font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
              SafeRoute AI
            </span>
            <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              Chicago 7km
            </span>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">
            Crime-Aware Pedestrian Navigation System
          </p>
        </div>
      </div>

      <nav className="app-tabs flex items-center space-x-1 sm:space-x-2 bg-slate-950/60 p-1 rounded-xl border border-slate-800/80">
        <button
          onClick={() => setActiveTab('navigation')}
          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'navigation'
              ? 'bg-emerald-500 text-slate-950 shadow-md font-semibold'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Navigation className="w-3.5 h-3.5" />
          <span>Navigation</span>
        </button>
      </nav>

      {/* Status & Refresh */}
      <div className="app-status flex items-center space-x-3">
        <div className="hidden md:flex flex-col items-end text-[11px] leading-tight">
          <span className="text-slate-400 flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>{healthData?.crime_incident_count || '...'} incidents</span>
          </span>
          <span className="text-slate-500 truncate max-w-[150px]">
            {healthData?.data_source || 'Connecting...'}
          </span>
        </div>

        <button
          onClick={onRefreshData}
          disabled={isRefreshing}
          title="Refresh Data from Chicago Police Department API"
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
        </button>
      </div>
    </header>
  );
}
