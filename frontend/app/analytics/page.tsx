"use client";

import React, { useSyncExternalStore } from "react";
import { useStore } from "@/store/useStore";
import { 
  TrendingUp, 
  Flame, 
  Clock, 
  PieChart as PieIcon, 
  Compass 
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";

const emptySubscribe = () => () => {};

export default function AnalyticsPage() {
  const { analytics } = useStore();
  const mounted = useSyncExternalStore(emptySubscribe, () => true, () => false);

  if (!analytics) {
    return (
      <div className="py-12 text-center text-brand-muted text-xs">
        Loading analytics profiles...
      </div>
    );
  }

  // Format Recharts data
  const weeklyData = Object.entries(analytics.daily_focus_hours || {}).map(([date, hours]) => {
    // Parse date to day name
    const dayName = new Date(date).toLocaleDateString(undefined, { weekday: "short" });
    return {
      date: dayName,
      hours: hours
    };
  });

  const categoryData = [
    {
      name: "AI Agency",
      Planned: analytics.agency_planned_hours,
      Completed: analytics.agency_completed_hours,
    },
    {
      name: "DSA Practice",
      Planned: analytics.dsa_planned_hours,
      Completed: analytics.dsa_completed_hours,
    }
  ];

  // Convert reason counters to chart representation
  const reasonKeys = Object.keys(analytics.skip_reasons_breakdown || {});
  const reasonValues = Object.values(analytics.skip_reasons_breakdown || {});
  
  return (
    <div className="flex flex-col gap-8 pb-10">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          PERFORMANCE AUDIT
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          Weekly Insights
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">
          Calculated weekly using your completion times, logged skip reasons, and gym consistency.
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Reality Score */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between h-36">
          <div className="flex justify-between items-start">
            <span className="text-[10px] text-brand-muted font-bold tracking-wider uppercase">Reality Score</span>
            <TrendingUp className="w-4 h-4 text-brand-accent" />
          </div>
          <div>
            <h4 className="text-3xl font-black tracking-tight">{analytics.reality_score}%</h4>
            <p className="text-[10px] text-brand-muted mt-1">Target consistency score: &gt; 70%</p>
          </div>
        </div>

        {/* Focus Hours */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between h-36">
          <div className="flex justify-between items-start">
            <span className="text-[10px] text-brand-muted font-bold tracking-wider uppercase">Completed Focus</span>
            <Clock className="w-4 h-4 text-brand-success" />
          </div>
          <div>
            <h4 className="text-3xl font-black tracking-tight">{analytics.total_completed_hours} hrs</h4>
            <p className="text-[10px] text-brand-muted mt-1">{analytics.total_planned_hours} total planned hours this week</p>
          </div>
        </div>

        {/* Gym Streak */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between h-36">
          <div className="flex justify-between items-start">
            <span className="text-[10px] text-brand-muted font-bold tracking-wider uppercase">Gym Streak</span>
            <Flame className="w-4 h-4 text-brand-warning" />
          </div>
          <div>
            <h4 className="text-3xl font-black tracking-tight">{analytics.gym_streak} Days</h4>
            <p className="text-[10px] text-brand-muted mt-1">Gym block is non-negotiable</p>
          </div>
        </div>

        {/* Task Completion count */}
        <div className="glass-card rounded-2xl p-5 flex flex-col justify-between h-36">
          <div className="flex justify-between items-start">
            <span className="text-[10px] text-brand-muted font-bold tracking-wider uppercase">Block Output</span>
            <PieIcon className="w-4 h-4 text-purple-400" />
          </div>
          <div>
            <h4 className="text-3xl font-black tracking-tight">{analytics.completed_blocks_count} Blocks</h4>
            <p className="text-[10px] text-brand-muted mt-1">{analytics.skipped_blocks_count} blocks skipped / rescheduled</p>
          </div>
        </div>

      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Chart 1: Focus Hours Completed vs Planned */}
        <div className="glass-card rounded-2xl p-6 flex flex-col gap-4">
          <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase">
            Time split by category (Hours)
          </h3>
          
          <div className="h-72 w-full text-xs">
            {mounted && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222B3F" />
                  <XAxis dataKey="name" stroke="#6B7280" />
                  <YAxis stroke="#6B7280" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#151B28", borderColor: "#222B3F" }} 
                    labelStyle={{ color: "#F3F4F6", fontWeight: "bold" }}
                  />
                  <Legend />
                  <Bar dataKey="Planned" fill="#222B3F" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Completed" fill="#4F8CFF" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 2: Daily Focus Hours completed */}
        <div className="glass-card rounded-2xl p-6 flex flex-col gap-4">
          <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase">
            Daily Focus Output (Hours)
          </h3>
          
          <div className="h-72 w-full text-xs">
            {mounted && weeklyData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyData} margin={{ top: 20, right: 30, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222B3F" />
                  <XAxis dataKey="date" stroke="#6B7280" />
                  <YAxis stroke="#6B7280" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#151B28", borderColor: "#222B3F" }}
                    labelStyle={{ color: "#F3F4F6" }}
                  />
                  <Bar dataKey="hours" fill="#00C853" radius={[4, 4, 0, 0]} name="Completed Focus Hours" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-brand-muted">
                No daily focus logs found for this week.
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Skip Reasons Breakdown (1 col) */}
        <div className="glass-card rounded-2xl p-6 flex flex-col gap-4">
          <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase">
            Friction & Skip Reasons
          </h3>
          
          <div className="flex flex-col gap-4 mt-2">
            {reasonKeys.length > 0 ? (
              reasonKeys.map((key, index) => {
                const count = reasonValues[index] as number;
                const total = reasonValues.reduce((a, b) => (a as number) + (b as number), 0) as number;
                const pct = Math.round((count / total) * 100);
                
                return (
                  <div key={key} className="flex flex-col gap-1.5">
                    <div className="flex justify-between text-xs font-semibold text-slate-300">
                      <span>{key}</span>
                      <span>{count} times ({pct}%)</span>
                    </div>
                    <div className="w-full bg-brand-border h-2 rounded-full overflow-hidden">
                      <div className="bg-brand-danger h-full rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-12 text-center text-brand-muted text-xs">
                No skips logged this week. Flawless output.
              </div>
            )}
          </div>
        </div>

        {/* AI Weekly Coaching Analysis (2 cols) */}
        <div className="lg:col-span-2 rounded-2xl border border-brand-border bg-gradient-to-br from-brand-card to-brand-bg p-6.5 flex flex-col gap-4 shadow-xl">
          <div className="flex items-center gap-2 text-brand-accent">
            <Compass className="w-4 h-4" />
            <h3 className="text-xs text-slate-100 font-bold uppercase tracking-wider">
              AI Coach Performance Audit
            </h3>
          </div>
          
          <div className="flex flex-col gap-3.5 text-xs text-brand-muted leading-relaxed">
            <p>
              Your reality check is currently at **{analytics.reality_score}%**. You have skipped Agency strategy or DSA practice {analytics.skipped_blocks_count} times this week, primarily citing **&quot;{reasonKeys[0] || 'tiredness'}&quot;**.
            </p>
            <p className="border-l-2 border-brand-accent pl-4 italic text-slate-200 font-medium">
              &ldquo;Your DSA practice shows a {analytics.dsa_score}% completion rate. You claim you want placements, but your schedule actions show you prioritize client reel edits and then crash due to fatigue. Move DSA to 7 AM immediately. Treat it with the same respect as the gym.&rdquo;
            </p>
            <p>
              Gym streaks remain healthy at **{analytics.gym_streak} days** in a row. This validates that you have the discipline, you are simply misallocating it on academic/career focus targets.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
