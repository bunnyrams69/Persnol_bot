"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useStore, PatternCell } from "@/store/useStore";
import { 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingDown, 
  ShieldAlert, 
  Activity, 
  RefreshCw, 
  Calendar, 
  Dumbbell, 
  Code, 
  Briefcase, 
  Clock, 
  Info, 
  ChevronRight
} from "lucide-react";

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  gym: Dumbbell,
  agency: Briefcase,
  dsa: Code,
  deadline: Clock,
};

const CATEGORIES = ["gym", "agency", "dsa", "deadline"];

const WEEKDAYS = [
  { idx: 0, name: "Monday", short: "Mon" },
  { idx: 1, name: "Tuesday", short: "Tue" },
  { idx: 2, name: "Wednesday", short: "Wed" },
  { idx: 3, name: "Thursday", short: "Thu" },
  { idx: 4, name: "Friday", short: "Fri" },
  { idx: 5, name: "Saturday", short: "Sat" },
  { idx: 6, name: "Sunday", short: "Sun" },
];

export default function PatternsPage() {
  const data = useStore((state) => state.patterns);
  const fetchPatterns = useStore((state) => state.fetchPatterns);
  const [days, setDays] = useState<number>(28);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [selectedCell, setSelectedCell] = useState<PatternCell | null>(null);

  useEffect(() => {
    if (!data) {
      fetchPatterns(28);
    }
  }, [data, fetchPatterns]);

  const handleSelectDays = async (selectedDays: number) => {
    setDays(selectedDays);
    setIsRefreshing(true);
    try {
      await fetchPatterns(selectedDays);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await fetchPatterns(days);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Compute cell lookup: map `${weekday}_${category}` -> PatternCell
  const cellMap = useMemo(() => {
    const map = new Map<string, PatternCell>();
    if (data?.matrix) {
      for (const cell of data.matrix) {
        map.set(`${cell.weekday}_${cell.category}`, cell);
      }
    }
    return map;
  }, [data]);

  const flaggedPatterns = data?.flagged_patterns || [];
  const totalBlocks = data?.summary?.total_blocks || 0;
  const totalCompleted = data?.summary?.total_completed || 0;
  const totalSkipped = data?.summary?.total_skipped || 0;
  const overallCompletionRate = totalBlocks > 0 ? Math.round((totalCompleted / totalBlocks) * 100) : 0;

  const getHeatmapColor = (cell: PatternCell | undefined) => {
    if (!cell || cell.total === 0) {
      return "bg-brand-card/30 border-brand-border/40 text-slate-500 hover:border-slate-600";
    }
    if (cell.is_flagged) {
      return "bg-rose-950/60 border-rose-500/70 text-rose-200 shadow-md shadow-rose-950/50 hover:border-rose-400";
    }
    if (cell.skip_rate === 0) {
      return "bg-emerald-950/50 border-emerald-500/40 text-emerald-300 hover:border-emerald-400";
    }
    if (cell.skip_rate <= 0.25) {
      return "bg-teal-950/50 border-teal-500/40 text-teal-300 hover:border-teal-400";
    }
    if (cell.skip_rate <= 0.5) {
      return "bg-amber-950/50 border-amber-500/40 text-amber-300 hover:border-amber-400";
    }
    return "bg-orange-950/60 border-orange-500/50 text-orange-200 hover:border-orange-400";
  };

  return (
    <div className="flex-1 w-full pb-16 text-slate-100">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-brand-border/60">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-gradient-to-tr from-brand-accent/20 to-indigo-500/20 border border-brand-accent/30 text-brand-accent">
                <Sparkles className="w-5 h-5" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                Habit Pattern Intelligence
              </h1>
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-brand-accent/15 border border-brand-accent/30 text-brand-accent">
                Autonomous Detector
              </span>
            </div>
            <p className="text-xs text-brand-muted mt-1.5 max-w-2xl">
              Deterministic pattern engine analyzing 28 days of logged blocks. Flags repeat habit failures (&ge;3 samples, &ge;60% skip rate) and injects proactive warnings into the AI Chief of Staff.
            </p>
          </div>

          {/* Time range selector & refresh */}
          <div className="flex items-center gap-3">
            <div className="flex items-center bg-brand-card/60 p-1 rounded-xl border border-brand-border">
              {[14, 28, 60].map((d) => (
                <button
                  key={d}
                  onClick={() => handleSelectDays(d)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 ${
                    days === d
                      ? "bg-brand-accent text-white shadow-sm"
                      : "text-brand-muted hover:text-slate-200 hover:bg-brand-border/40"
                  }`}
                >
                  {d} Days
                </button>
              ))}
            </div>

            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-xl border border-brand-border bg-brand-card/60 hover:bg-brand-card text-slate-200 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-brand-accent" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Stats Ribbon */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between border border-brand-border/70 hover:border-brand-accent/40 transition-colors">
            <div className="flex justify-between items-start">
              <span className="text-xs font-medium text-brand-muted uppercase tracking-wider">Tracked Activity</span>
              <Activity className="w-4 h-4 text-brand-accent" />
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold tracking-tight text-white">{totalBlocks}</div>
              <span className="text-[11px] text-brand-muted">Total logged schedule blocks</span>
            </div>
          </div>

          <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between border border-brand-border/70 hover:border-emerald-500/40 transition-colors">
            <div className="flex justify-between items-start">
              <span className="text-xs font-medium text-brand-muted uppercase tracking-wider">Completed</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold tracking-tight text-emerald-400">{totalCompleted}</div>
              <span className="text-[11px] text-brand-muted">{overallCompletionRate}% total completion rate</span>
            </div>
          </div>

          <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between border border-brand-border/70 hover:border-amber-500/40 transition-colors">
            <div className="flex justify-between items-start">
              <span className="text-xs font-medium text-brand-muted uppercase tracking-wider">Total Skips</span>
              <TrendingDown className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold tracking-tight text-amber-400">{totalSkipped}</div>
              <span className="text-[11px] text-brand-muted">Missed habit opportunities</span>
            </div>
          </div>

          <div className="glass-panel p-5 rounded-2xl flex flex-col justify-between border border-brand-border/70 hover:border-rose-500/40 transition-colors">
            <div className="flex justify-between items-start">
              <span className="text-xs font-medium text-brand-muted uppercase tracking-wider">Flagged Patterns</span>
              <ShieldAlert className="w-4 h-4 text-rose-400" />
            </div>
            <div className="mt-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold tracking-tight text-rose-400">{flaggedPatterns.length}</span>
                {flaggedPatterns.length > 0 && (
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-rose-950/80 border border-rose-500/40 text-rose-300 animate-pulse">
                    Active Alert
                  </span>
                )}
              </div>
              <span className="text-[11px] text-brand-muted">Recurring failure loops identified</span>
            </div>
          </div>
        </div>

        {/* Flagged Patterns Cards Section */}
        {flaggedPatterns.length > 0 && (
          <div className="space-y-3.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <h2 className="text-base font-semibold text-white">Active Habit Interventions</h2>
              </div>
              <span className="text-xs text-brand-muted">
                These patterns trigger proactive alerts at 9 PM and arm the AI Coach during negotiation
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {flaggedPatterns.map((pat, idx) => {
                const Icon = CATEGORY_ICONS[pat.category] || Activity;
                return (
                  <div 
                    key={idx}
                    className="p-5 rounded-2xl border border-rose-500/40 bg-gradient-to-br from-rose-950/40 via-brand-card/80 to-brand-card/50 backdrop-blur-md shadow-xl flex flex-col justify-between gap-4"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="p-2 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300">
                            <Icon className="w-4 h-4" />
                          </div>
                          <div>
                            <span className="text-sm font-bold text-white capitalize">
                              {pat.category_display}
                            </span>
                            <span className="text-xs text-brand-muted ml-2">
                              Every {pat.weekday_name}
                            </span>
                          </div>
                        </div>

                        <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-rose-900/60 border border-rose-500/50 text-rose-200">
                          {Math.round(pat.skip_rate * 100)}% Skip Rate
                        </span>
                      </div>

                      <p className="text-sm font-medium text-slate-100 mt-3 leading-relaxed">
                        &ldquo;{pat.message}&rdquo;
                      </p>
                    </div>

                    <div className="space-y-2 pt-3 border-t border-rose-500/20 text-xs">
                      <div className="flex justify-between items-center text-slate-300">
                        <span className="text-brand-muted">Confidence Score</span>
                        <span className="font-semibold text-rose-300">{Math.round(pat.confidence * 100)}% ({pat.total} samples)</span>
                      </div>
                      <div className="w-full bg-brand-border h-1.5 rounded-full overflow-hidden">
                        <div 
                          className="bg-rose-500 h-full rounded-full transition-all duration-500"
                          style={{ width: `${Math.round(pat.confidence * 100)}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between pt-1 text-[11px] text-brand-muted">
                        <span>Skipped: <strong className="text-rose-300">{pat.skipped}</strong> / {pat.total}</span>
                        {pat.most_common_reason && (
                          <span>Common Reason: <strong className="text-slate-200">{pat.most_common_reason}</strong></span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Heatmap Section */}
        <div className="glass-panel p-6 rounded-2xl border border-brand-border/70 space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-brand-accent" />
                Execution Heatmap: Weekday &times; Category
              </h2>
              <p className="text-xs text-brand-muted mt-0.5">
                Cells show <strong>done / total</strong> attempts. Red cells indicate statistical skip risk (&ge;60% skip rate with &ge;3 samples).
              </p>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-3 text-[11px] text-brand-muted">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-md bg-emerald-950/80 border border-emerald-500/50 inline-block" />
                Done (&le;25% skip)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-md bg-amber-950/80 border border-amber-500/50 inline-block" />
                Moderate (26-50%)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-md bg-rose-950/80 border border-rose-500/70 inline-block" />
                Flagged (&ge;60%)
              </span>
            </div>
          </div>

          {/* Heatmap Table Grid */}
          <div className="overflow-x-auto">
            <div className="min-w-[700px]">
              {/* Header row: Weekdays */}
              <div className="grid grid-cols-8 gap-2.5 pb-2 border-b border-brand-border/60 text-xs font-semibold text-slate-400">
                <div className="p-2">Category</div>
                {WEEKDAYS.map((w) => (
                  <div key={w.idx} className="p-2 text-center text-slate-300">
                    {w.short}
                  </div>
                ))}
              </div>

              {/* Data rows by Category */}
              <div className="space-y-2.5 pt-2.5">
                {CATEGORIES.map((catKey) => {
                  const Icon = CATEGORY_ICONS[catKey] || Activity;
                  const catLabel = catKey === "dsa" ? "DSA" : catKey === "agency" ? "AI Agency" : catKey.charAt(0).toUpperCase() + catKey.slice(1);

                  return (
                    <div key={catKey} className="grid grid-cols-8 gap-2.5 items-center">
                      {/* Row Label */}
                      <div className="flex items-center gap-2 px-2 py-3 rounded-xl bg-brand-card/40 border border-brand-border/50 text-xs font-semibold text-slate-200">
                        <Icon className="w-4 h-4 text-brand-accent flex-shrink-0" />
                        <span className="truncate">{catLabel}</span>
                      </div>

                      {/* 7 Weekday Cells */}
                      {WEEKDAYS.map((w) => {
                        const cell = cellMap.get(`${w.idx}_${catKey}`);
                        const colorClass = getHeatmapColor(cell);
                        const isSelected = selectedCell?.weekday === w.idx && selectedCell?.category === catKey;

                        return (
                          <button
                            key={w.idx}
                            onClick={() => cell && setSelectedCell(cell)}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all duration-200 text-center relative group ${colorClass} ${
                              isSelected ? "ring-2 ring-brand-accent ring-offset-2 ring-offset-brand-bg" : ""
                            }`}
                          >
                            {cell?.is_flagged && (
                              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-400 animate-ping" />
                            )}
                            <span className="text-sm font-bold tracking-tight">
                              {cell && cell.total > 0 ? `${cell.done}/${cell.total}` : "—"}
                            </span>
                            <span className="text-[10px] opacity-80 mt-0.5">
                              {cell && cell.total > 0 ? `${Math.round(cell.skip_rate * 100)}% skip` : "no data"}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Selected Cell Drilldown */}
          {selectedCell && (
            <div className="mt-4 p-4 rounded-xl border border-brand-accent/30 bg-brand-card/80 backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-in fade-in">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-xl border ${selectedCell.is_flagged ? "bg-rose-950/60 border-rose-500/40 text-rose-300" : "bg-brand-accent/15 border-brand-accent/30 text-brand-accent"}`}>
                  {selectedCell.is_flagged ? <AlertTriangle className="w-5 h-5" /> : <Info className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">
                    {selectedCell.category_display} on {selectedCell.weekday_name}s
                  </h4>
                  <p className="text-xs text-brand-muted mt-0.5">
                    {selectedCell.done} completed, {selectedCell.skipped} skipped out of {selectedCell.total} attempts ({Math.round(selectedCell.skip_rate * 100)}% skip rate).
                    {selectedCell.most_common_reason ? ` Primary reason: &ldquo;${selectedCell.most_common_reason}&rdquo;.` : ""}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {selectedCell.is_flagged ? (
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-rose-950/80 border border-rose-500/40 text-rose-300">
                    Flagged Pattern Trigger
                  </span>
                ) : (
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/80 border border-emerald-500/30 text-emerald-300">
                    Within Safe Variance
                  </span>
                )}
                <button
                  onClick={() => setSelectedCell(null)}
                  className="text-xs text-brand-muted hover:text-white px-2 py-1"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Empty State when no blocks exist */}
        {totalBlocks === 0 && (
          <div className="glass-panel p-10 rounded-2xl border border-brand-border text-center space-y-4">
            <div className="w-12 h-12 mx-auto rounded-2xl bg-brand-card border border-brand-border flex items-center justify-center text-brand-muted">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">No Activity Logs Found</h3>
              <p className="text-xs text-brand-muted mt-1 max-w-md mx-auto">
                No activity blocks were completed or skipped in the last {days} days. Seed demo data to see the pattern detector and AI Coach interventions in action.
              </p>
            </div>
            <div className="pt-2">
              <span className="inline-flex items-center gap-1.5 text-xs text-brand-accent font-medium bg-brand-accent/10 px-3.5 py-1.5 rounded-xl border border-brand-accent/20">
                Run: python scripts/seed_demo_data.py
                <ChevronRight className="w-3.5 h-3.5" />
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
