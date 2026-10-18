"use client";

import React, { useState } from "react";
import { useStore } from "@/store/useStore";
import { 
  Sliders, 
  AlertCircle, 
  Check, 
  Info 
} from "lucide-react";

export default function GoalsPage() {
  const { goals, updateGoalRatios, loading } = useStore();
  const [editedRatios, setEditedRatios] = useState<Record<number, number>>({});
  const [valError, setValError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Derive current ratios: use editedRatios if modified by user, otherwise fallback to store goals
  const localRatios: Record<number, number> = {};
  if (goals && goals.length > 0) {
    goals.forEach(g => {
      localRatios[g.id] = g.id in editedRatios ? editedRatios[g.id] : Math.round(g.ratio * 100);
    });
  }

  const handleRatioChange = (id: number, val: number) => {
    setSuccess(false);
    setValError(null);
    setEditedRatios(prev => ({
      ...prev,
      [id]: Math.min(100, Math.max(0, val))
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccess(false);
    setValError(null);

    // Sum ratios
    const sum = Object.values(localRatios).reduce((acc, curr) => acc + curr, 0);
    if (sum !== 100) {
      setValError(`Ratios must sum up to exactly 100%. Current sum: ${sum}%`);
      return;
    }

    // Convert back to fractions (0.0 to 1.0)
    const payload = Object.entries(localRatios).map(([idStr, val]) => ({
      id: Number(idStr),
      ratio: val / 100
    }));

    try {
      await updateGoalRatios(payload);
      setEditedRatios({});
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update ratios.";
      setValError(msg);
    }
  };

  const totalSum = Object.values(localRatios).reduce((acc, curr) => acc + curr, 0);

  return (
    <div className="flex flex-col gap-8 pb-10">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          STRATEGIC WEIGHTS
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          Recurring Goals
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">
          Leftover daily minutes are split between goals based on these ratios. Minimum session limits apply.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        
        {/* Goals Config Form (2 cols) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <form onSubmit={handleSave} className="glass-card rounded-2xl p-6.5 flex flex-col gap-6">
            <div className="flex justify-between items-center border-b border-brand-border pb-4">
              <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase flex items-center gap-2">
                <Sliders className="w-4 h-4 text-brand-accent" />
                Goal Time Ratios
              </h3>
              
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                totalSum === 100 
                  ? "bg-brand-success/15 text-brand-success border border-brand-success/30" 
                  : "bg-brand-danger/15 text-brand-danger border border-brand-danger/30"
              }`}>
                Sum: {totalSum}%
              </span>
            </div>

            {valError && (
              <div className="p-4 rounded-xl border border-brand-danger bg-brand-danger/10 text-brand-danger flex items-center gap-2 text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {valError}
              </div>
            )}

            {success && (
              <div className="p-4 rounded-xl border border-brand-success bg-brand-success/10 text-brand-success flex items-center gap-2 text-xs">
                <Check className="w-4 h-4 flex-shrink-0" />
                Goal ratios updated successfully! Tomorrow&apos;s schedule regenerated.
              </div>
            )}

            <div className="flex flex-col gap-6">
              {goals.map((goal) => {
                const currentVal = localRatios[goal.id] || 0;
                
                return (
                  <div key={goal.id} className="p-4 rounded-xl border border-brand-border bg-brand-card/30 flex flex-col gap-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-bold text-sm text-slate-100">{goal.name}</h4>
                        <p className="text-[10px] text-brand-muted mt-0.5">
                          Min Session: {goal.minimum_minutes} minutes | Priority: {goal.priority}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={currentVal}
                          onChange={(e) => handleRatioChange(goal.id, Number(e.target.value))}
                          className="w-16 bg-brand-bg border border-brand-border rounded-lg p-2 text-center text-xs font-bold focus:outline-none focus:border-brand-accent"
                          min={0}
                          max={100}
                        />
                        <span className="text-xs text-brand-muted font-bold">%</span>
                      </div>
                    </div>
                    
                    {/* Range Slider */}
                    <div className="w-full">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={currentVal}
                        onChange={(e) => handleRatioChange(goal.id, Number(e.target.value))}
                        className="w-full accent-brand-accent h-1 bg-brand-border rounded-lg appearance-none cursor-pointer"
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <button
              type="submit"
              disabled={loading || totalSum !== 100}
              className="w-full mt-4 bg-brand-accent hover:bg-brand-accent/90 disabled:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-white font-extrabold p-3.5 rounded-xl text-xs transition-all duration-200 shadow-md shadow-brand-accent/15 glow-shadow-accent"
            >
              Save Configuration
            </button>
          </form>
        </div>

        {/* Explain Card (1 col) */}
        <div className="flex flex-col gap-6">
          <div className="rounded-2xl border border-brand-border bg-brand-card/20 p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2 text-brand-accent">
              <Info className="w-4 h-4" />
              <h4 className="text-xs text-slate-200 font-bold uppercase tracking-wider">How Ratios Work</h4>
            </div>
            
            <p className="text-xs text-brand-muted leading-relaxed">
              Every day, after blocking fixed slots (College, Gym, Travel) and scheduling near-due client deadlines, the planner calculates the remaining open minutes.
            </p>
            <p className="text-xs text-brand-muted leading-relaxed">
              If 300 open minutes remain:
            </p>
            <ul className="text-xs text-slate-300 pl-4 list-disc flex flex-col gap-1">
              <li>60% AI Agency = 180 min</li>
              <li>40% DSA Practice = 120 min</li>
            </ul>
            <p className="text-xs text-brand-muted leading-relaxed italic border-t border-brand-border/60 pt-3 mt-1">
              Changing these ratios immediately triggers a re-plan for tomorrow so you can negotiate the new structure tonight.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
