"use client";

import React, { useState, useEffect } from "react";
import { useStore } from "@/store/useStore";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Plus, 
  Check, 
  X, 
  AlertCircle, 
  Flame, 
  ArrowRight,
  Inbox as InboxIcon
} from "lucide-react";

export default function DashboardPage() {
  const {
    user,
    todaySchedule,
    inbox,
    analytics,
    setEnergy,
    updateBlockStatus,
    createInboxItem,
    error,
    clearError
  } = useStore();

  const [inboxInput, setInboxInput] = useState("");
  const [currentTime, setCurrentTime] = useState("");
  const [skipReasonId, setSkipReasonId] = useState<number | null>(null);
  const [customReason, setCustomReason] = useState("");

  // Live timer for active block detection
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toTimeString().split(" ")[0]);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleAddInbox = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inboxInput.trim()) return;
    await createInboxItem({ title: inboxInput.trim(), source: "manual" });
    setInboxInput("");
  };

  const handleSelectSkipReason = async (blockId: number, reason: string) => {
    await updateBlockStatus(blockId, "skipped", reason);
    setSkipReasonId(null);
    setCustomReason("");
  };

  // Detect currently active focus block
  const getActiveBlock = () => {
    if (!todaySchedule || !todaySchedule.blocks) return null;
    return todaySchedule.blocks.find(b => {
      if (b.status !== "pending") return false;
      // Fixed blocks like college or breaks might not need focus actions, but deadlines, agency, and dsa do.
      return b.planned_start <= currentTime && b.planned_end >= currentTime;
    });
  };

  // Find next upcoming block
  const getNextBlock = () => {
    if (!todaySchedule || !todaySchedule.blocks) return null;
    return todaySchedule.blocks.find(b => b.planned_start > currentTime && b.status === "pending");
  };

  const activeBlock = getActiveBlock();
  const nextBlock = getNextBlock();
  const todayStr = new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="flex flex-col gap-8 pb-10">
      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl border border-brand-danger bg-brand-danger/10 text-brand-danger flex justify-between items-center text-sm">
          <span className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </span>
          <button onClick={clearError} className="hover:opacity-80">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header Block */}
      <div className="flex justify-between items-end">
        <div>
          <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
            STUDENT / FREELANCER / CREATOR
          </span>
          <h2 className="text-3xl font-extrabold tracking-tight mt-1">
            {user?.name ? `${user.name}'s Command Center` : "Command Center"}
          </h2>
          <p className="text-sm text-brand-muted mt-0.5">{todayStr}</p>
        </div>
        
        {analytics && (
          <div className="flex items-center gap-4 bg-brand-card/20 border border-brand-border rounded-xl p-3.5 px-5">
            <div className="flex flex-col text-right">
              <span className="text-[10px] text-brand-muted font-bold tracking-wider uppercase">
                TODAY FOCUS HOURS
              </span>
              <span className="text-xl font-bold text-brand-accent">
                {analytics.total_completed_hours} hrs / {analytics.total_planned_hours} planned
              </span>
            </div>
            <div className="w-px h-8 bg-brand-border" />
            <div className="flex items-center gap-1.5 text-brand-warning">
              <Flame className="w-5 h-5 fill-brand-warning/20" />
              <span className="text-xl font-black">{analytics.gym_streak}</span>
            </div>
          </div>
        )}
      </div>

      {/* Inbox Quick Add Capture */}
      <form onSubmit={handleAddInbox} className="w-full relative group">
        <input
          type="text"
          value={inboxInput}
          onChange={(e) => setInboxInput(e.target.value)}
          placeholder="Capture anything here... (e.g. 'Pay Gym fee' or 'Edit client promo reel tomorrow urgent')"
          className="w-full bg-brand-card/40 border border-brand-border rounded-2xl p-4.5 px-6 pl-14 text-slate-100 placeholder-brand-muted focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 transition-all duration-300 rounded-2xl shadow-xl shadow-black/10 group-hover:border-brand-border/80"
        />
        <InboxIcon className="w-5 h-5 text-brand-muted absolute left-5 top-1/2 -translate-y-1/2 group-focus-within:text-brand-accent transition-colors duration-300" />
        <button 
          type="submit"
          className="absolute right-3.5 top-1/2 -translate-y-1/2 bg-brand-accent hover:bg-brand-accent/90 text-white font-bold p-2.5 rounded-xl transition-all duration-200"
        >
          <Plus className="w-4 h-4" />
        </button>
      </form>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column (2 cols): Core Actions & Timeline */}
        <div className="lg:col-span-2 flex flex-col gap-8">
          
          {/* Energy Survey Alert */}
          {todaySchedule && todaySchedule.energy_score === null && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card rounded-2xl p-6 flex flex-col items-center gap-4 glow-shadow-accent"
            >
              <div className="text-center">
                <h3 className="font-bold text-base">How are you feeling this morning?</h3>
                <p className="text-xs text-brand-muted mt-1">Life OS uses your energy score to calculate failure risk and stats.</p>
              </div>
              <div className="flex gap-4">
                {[
                  { score: 1, emoji: "🥱", label: "Tired" },
                  { score: 2, emoji: "💤", label: "Slow" },
                  { score: 3, emoji: "😐", label: "Okay" },
                  { score: 4, emoji: "⚡", label: "Good" },
                  { score: 5, emoji: "🚀", label: "Crushing" },
                ].map((item) => (
                  <button
                    key={item.score}
                    onClick={() => setEnergy(item.score)}
                    className="flex flex-col items-center gap-1.5 p-3 px-4 rounded-xl border border-brand-border bg-brand-card/40 hover:border-brand-accent hover:bg-brand-accent/10 hover:scale-105 transition-all duration-200"
                  >
                    <span className="text-2xl">{item.emoji}</span>
                    <span className="text-[10px] text-brand-muted uppercase font-semibold">{item.label}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Active Focus Block */}
          <div className="glass-card rounded-2xl p-6.5 flex flex-col gap-4">
            <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-accent animate-ping" />
              Active Focus Target
            </h3>
            
            {activeBlock ? (
              <div className="flex justify-between items-center gap-6 py-2">
                <div className="flex-1 min-w-0">
                  <h4 className="text-2xl font-black tracking-tight text-white truncate">{activeBlock.title}</h4>
                  <span className="text-xs text-brand-accent font-semibold tracking-wide uppercase mt-1 inline-block">
                    {activeBlock.planned_start.slice(0, 5)} - {activeBlock.planned_end.slice(0, 5)}
                  </span>
                </div>
                
                {/* Completed / Skipped buttons */}
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => updateBlockStatus(activeBlock.id, "completed")}
                    className="flex items-center gap-1.5 bg-brand-success/15 hover:bg-brand-success text-brand-success hover:text-white border border-brand-success/30 rounded-xl px-5 py-3 text-sm font-bold transition-all duration-200 shadow-lg hover:glow-shadow-success"
                  >
                    <Check className="w-4 h-4" />
                    Done
                  </button>
                  <button 
                    onClick={() => setSkipReasonId(activeBlock.id)}
                    className="flex items-center gap-1.5 bg-brand-danger/15 hover:bg-brand-danger text-brand-danger hover:text-white border border-brand-danger/30 rounded-xl px-5 py-3 text-sm font-bold transition-all duration-200 shadow-lg hover:glow-shadow-danger"
                  >
                    <X className="w-4 h-4" />
                    Skip
                  </button>
                </div>
              </div>
            ) : nextBlock ? (
              <div className="py-2">
                <p className="text-slate-400 text-sm">No active focus block right now. Gaps are breaks. ☕</p>
                <div className="mt-4 p-4 rounded-xl border border-brand-border bg-brand-card/40 flex justify-between items-center">
                  <div>
                    <span className="text-[10px] text-brand-muted font-bold tracking-wider uppercase">NEXT FOCUS</span>
                    <h5 className="font-bold text-slate-200 text-base mt-0.5">{nextBlock.title}</h5>
                  </div>
                  <span className="text-xs text-brand-accent font-semibold">{nextBlock.planned_start.slice(0, 5)}</span>
                </div>
              </div>
            ) : (
              <div className="py-4 text-center">
                <p className="text-sm text-brand-muted">All scheduled blocks complete. Sleep is the only thing left. 💤</p>
              </div>
            )}

            {/* Skip Reason Modal overlay */}
            <AnimatePresence>
              {skipReasonId && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                >
                  <motion.div 
                    initial={{ scale: 0.95 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0.95 }}
                    className="bg-brand-card border border-brand-border rounded-2xl p-6.5 max-w-md w-full flex flex-col gap-4 shadow-2xl"
                  >
                    <div>
                      <h4 className="font-bold text-lg text-slate-100">Why are you skipping?</h4>
                      <p className="text-xs text-brand-muted mt-1">Honesty builds memory profiles. Lies skew predictions.</p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        "Too tired", "Unexpected work", "Bad planning", 
                        "Distraction", "Low motivation"
                      ].map(r => (
                        <button
                          key={r}
                          onClick={() => handleSelectSkipReason(skipReasonId, r)}
                          className="p-3 text-xs font-semibold rounded-xl border border-brand-border bg-brand-bg/50 text-left hover:border-brand-danger hover:bg-brand-danger/10 text-slate-300 transition-all"
                        >
                          {r}
                        </button>
                      ))}
                    </div>

                    <div className="flex flex-col gap-2 mt-2">
                      <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Custom Reason</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={customReason}
                          onChange={(e) => setCustomReason(e.target.value)}
                          placeholder="e.g. gym injury, power outage"
                          className="flex-1 bg-brand-bg border border-brand-border rounded-xl p-2.5 text-xs focus:outline-none focus:border-brand-danger text-slate-200"
                        />
                        <button
                          onClick={() => handleSelectSkipReason(skipReasonId, customReason.trim() || "Other")}
                          className="bg-brand-danger text-white font-bold p-2.5 px-4 rounded-xl text-xs hover:bg-brand-danger/90 transition-all"
                        >
                          Save
                        </button>
                      </div>
                    </div>

                    <button 
                      onClick={() => setSkipReasonId(null)}
                      className="text-xs text-brand-muted hover:text-slate-300 mt-2 underline"
                    >
                      Cancel
                    </button>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Today Timeline */}
          <div className="glass-card rounded-2xl p-6.5 flex flex-col gap-6">
            <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase">
              Today Schedule Blocks
            </h3>
            
            <div className="flex flex-col relative border-l border-brand-border ml-2 pl-6 gap-6">
              {todaySchedule && todaySchedule.blocks && todaySchedule.blocks.length > 0 ? (
                todaySchedule.blocks.map((block) => {
                  const isCompleted = block.status === "completed";
                  const isSkipped = block.status === "skipped";
                  const isPending = block.status === "pending";
                  const isBreak = block.type === "break";
                  
                  return (
                    <div key={block.id} className="relative group">
                      {/* Timeline dot */}
                      <span className={`w-3.5 h-3.5 rounded-full absolute -left-[31px] top-1 border-2 border-brand-bg z-10 transition-all ${
                        isCompleted 
                          ? "bg-brand-success glow-shadow-success" 
                          : isSkipped 
                            ? "bg-brand-danger glow-shadow-danger" 
                            : isBreak
                              ? "bg-slate-700"
                              : "bg-brand-accent/70"
                      }`} />
                      
                      {/* Block Contents */}
                      <div className="flex justify-between items-start gap-4">
                        <div>
                          <h5 className={`font-bold text-sm tracking-tight transition-colors duration-200 ${
                            isCompleted 
                              ? "text-brand-success line-through opacity-60" 
                              : isSkipped 
                                ? "text-brand-danger opacity-70"
                                : "text-slate-200"
                          }`}>
                            {block.title}
                          </h5>
                          <span className="text-[10px] text-brand-muted tracking-wide font-semibold mt-0.5 inline-block uppercase">
                            {block.planned_start.slice(0, 5)} - {block.planned_end.slice(0, 5)} 
                            {block.reason && <span className="text-brand-danger italic ml-1">({block.reason})</span>}
                          </span>
                        </div>
                        
                        {/* Interactive status toggles for pending blocks */}
                        {isPending && !isBreak && (
                          <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            <button
                              onClick={() => updateBlockStatus(block.id, "completed")}
                              className="p-1.5 rounded-lg border border-brand-success/20 bg-brand-success/10 hover:bg-brand-success text-brand-success hover:text-white transition-all"
                              title="Mark as completed"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setSkipReasonId(block.id)}
                              className="p-1.5 rounded-lg border border-brand-danger/20 bg-brand-danger/10 hover:bg-brand-danger text-brand-danger hover:text-white transition-all"
                              title="Mark as skipped"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                        
                        {/* Completed / Skipped badges */}
                        {!isPending && (
                          <span className={`text-[9px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-md ${
                            isCompleted 
                              ? "bg-brand-success/15 text-brand-success border border-brand-success/30" 
                              : "bg-brand-danger/15 text-brand-danger border border-brand-danger/30"
                          }`}>
                            {block.status}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-brand-muted text-xs">No schedule generated for today yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column (1 col): Inbox Preview & Analytics Snippet */}
        <div className="flex flex-col gap-8">
          
          {/* Inbox Preview Widget */}
          <div className="glass-card rounded-2xl p-6 flex flex-col justify-between h-[360px]">
            <div className="flex flex-col gap-4 overflow-hidden">
              <div className="flex justify-between items-center">
                <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase flex items-center gap-2">
                  <InboxIcon className="w-3.5 h-3.5 text-brand-accent" />
                  Active Inbox ({inbox.length})
                </h3>
                <a href="/inbox" className="text-brand-accent text-xs hover:underline flex items-center gap-0.5">
                  View All
                  <ArrowRight className="w-3 h-3" />
                </a>
              </div>
              
              <div className="flex flex-col gap-2.5 overflow-y-auto max-h-[250px] pr-1">
                {inbox.length > 0 ? (
                  inbox.slice(0, 5).map((item) => (
                    <div 
                      key={item.id}
                      className="p-3 rounded-xl border border-brand-border bg-brand-bg/50 flex justify-between items-start"
                    >
                      <div className="min-w-0">
                        <h5 className="font-semibold text-xs text-slate-200 truncate">{item.title}</h5>
                        <span className="text-[9px] text-brand-muted uppercase font-bold tracking-wide mt-1 inline-block">
                          {item.suggested_type}
                        </span>
                      </div>
                      <span className={`text-[8px] font-extrabold tracking-wider uppercase px-1.5 py-0.5 rounded ${
                        item.priority === "urgent" 
                          ? "bg-brand-danger/10 text-brand-danger border border-brand-danger/20" 
                          : item.priority === "high"
                            ? "bg-brand-warning/10 text-brand-warning border border-brand-warning/20"
                            : "bg-slate-700 text-slate-300"
                      }`}>
                        {item.priority}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-brand-muted text-xs py-8 text-center">Your inbox is clean. Send a message to bot to add items. 📥</p>
                )}
              </div>
            </div>
            
            <a 
              href="/inbox"
              className="w-full text-center border border-brand-border bg-brand-card/40 hover:bg-brand-card hover:border-brand-accent/50 text-slate-200 font-bold p-3 rounded-xl text-xs transition-all duration-200 flex justify-center items-center gap-1.5"
            >
              Configure Inbox
            </a>
          </div>

          {/* Coaching Quote Widget */}
          <div className="rounded-2xl border border-brand-border bg-gradient-to-br from-brand-card to-brand-bg p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-accent" />
              <h4 className="text-xs text-brand-muted font-bold tracking-wider uppercase">Coach Memory Hook</h4>
            </div>
            
            <blockquote className="text-sm font-medium text-slate-200 italic leading-relaxed">
              {analytics && analytics.dsa_score < 50 ? (
                "\"You told me placements matter. But you've skipped DSA practice 3 times this week. Your scheduling is fine. Your discipline is not. Let's fix this.\""
              ) : (
                "\"Focus is a choice. You never skip the gym because it is a non-negotiable identity. AI Agency outreach must become the same. Do the outreach today.\""
              )}
            </blockquote>
            
            <a 
              href="/coach"
              className="text-xs text-brand-accent hover:underline flex items-center gap-0.5 font-semibold mt-1"
            >
              Start Chat Session
              <ArrowRight className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
