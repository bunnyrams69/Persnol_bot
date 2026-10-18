"use client";

import React, { useState } from "react";
import { useStore } from "@/store/useStore";
import { api } from "@/lib/api";
import { 
  User as UserIcon, 
  Check, 
  AlertCircle,
  ShieldAlert
} from "lucide-react";

export default function SettingsPage() {
  const { user, fetchInitialData } = useStore();
  
  const [nameInput, setNameInput] = useState<string | null>(null);
  const [wakeTimeInput, setWakeTimeInput] = useState<string | null>(null);
  const [sleepTimeInput, setSleepTimeInput] = useState<string | null>(null);
  
  const name = nameInput !== null ? nameInput : (user?.name || "");
  const wakeTime = wakeTimeInput !== null ? wakeTimeInput : (user?.wake_time || "");
  const sleepTime = sleepTimeInput !== null ? sleepTimeInput : (user?.sleep_time || "");

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    setError(null);

    try {
      await api.updateUser({
        name,
        wake_time: wakeTime,
        sleep_time: sleepTime
      });
      setSuccess(true);
      await fetchInitialData(); // reload store state
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update settings.";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-8 pb-10">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          SYSTEM CONFIGURATION
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          Settings
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">
          Configure sleep windows, owner credentials, and timezone constraints.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        
        {/* Left Column (2 cols): Profile Configuration */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <form onSubmit={handleSave} className="glass-card rounded-2xl p-6.5 flex flex-col gap-6">
            <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase flex items-center gap-2 border-b border-brand-border pb-4">
              <UserIcon className="w-4 h-4 text-brand-accent" />
              Owner Config Details
            </h3>

            {error && (
              <div className="p-4 rounded-xl border border-brand-danger bg-brand-danger/10 text-brand-danger flex items-center gap-2 text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {success && (
              <div className="p-4 rounded-xl border border-brand-success bg-brand-success/10 text-brand-success flex items-center gap-2 text-xs">
                <Check className="w-4 h-4 flex-shrink-0" />
                Profile configurations updated successfully!
              </div>
            )}

            <div className="flex flex-col gap-4">
              {/* Name */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Owner Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setNameInput(e.target.value)}
                  placeholder="Your Name"
                  className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent"
                  required
                />
              </div>

              {/* Wake & Sleep times */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Wake Time (HH:MM:SS)</label>
                  <input
                    type="text"
                    value={wakeTime}
                    onChange={(e) => setWakeTimeInput(e.target.value)}
                    placeholder="07:00:00"
                    className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent"
                    required
                  />
                  <span className="text-[9px] text-brand-muted">Standard daily energy questionnaire starts here.</span>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Sleep Time (HH:MM:SS)</label>
                  <input
                    type="text"
                    value={sleepTime}
                    onChange={(e) => setSleepTimeInput(e.target.value)}
                    placeholder="23:00:00"
                    className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent"
                    required
                  />
                  <span className="text-[9px] text-brand-muted">End of sleep window bounding for planner.</span>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full mt-2 bg-brand-accent hover:bg-brand-accent/90 disabled:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-white font-extrabold p-3.5 rounded-xl text-xs transition-all duration-200 shadow-md shadow-brand-accent/15 glow-shadow-accent"
            >
              {saving ? "Saving..." : "Save Settings"}
            </button>
          </form>
        </div>

        {/* Right Column (1 col): System Variables Check */}
        <div className="flex flex-col gap-6">
          <div className="glass-card rounded-2xl p-6 flex flex-col gap-4">
            <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase flex items-center gap-2 border-b border-brand-border pb-3">
              <ShieldAlert className="w-4 h-4 text-brand-warning" />
              Environment Check
            </h3>
            
            <div className="flex flex-col gap-3 text-xs text-brand-muted font-medium">
              <div className="flex justify-between border-b border-brand-border/40 pb-2">
                <span>Timezone</span>
                <span className="text-slate-300 font-semibold">{user?.timezone || "Asia/Kolkata"}</span>
              </div>
              <div className="flex justify-between border-b border-brand-border/40 pb-2">
                <span>Telegram ID</span>
                <span className="text-slate-300 font-semibold">{user?.telegram_id || "123456789"}</span>
              </div>
              <div className="flex justify-between border-b border-brand-border/40 pb-2">
                <span>LLM Engine</span>
                <span className="text-slate-300 font-semibold">Claude Sonnet 3.5</span>
              </div>
              <div className="flex justify-between">
                <span>App Mode</span>
                <span className="text-brand-success font-semibold">Development</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
