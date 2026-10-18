"use client";

import React, { useState, useMemo } from "react";
import { useStore } from "@/store/useStore";
import { 
  Check, 
  MessageSquare, 
  Lock, 
  Unlock, 
  Send,
  Loader2,
  CalendarDays
} from "lucide-react";

export default function TomorrowPage() {
  const {
    tomorrowSchedule,
    chatHistory,
    coachLoading,
    sendCoachMessage,
    loading
  } = useStore();

  const [inputMessage, setInputMessage] = useState("");

  const tomorrowStr = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toLocaleDateString(undefined, { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || coachLoading) return;
    const msg = inputMessage;
    setInputMessage("");
    await sendCoachMessage(msg);
  };

  const handleApprove = async () => {
    if (!tomorrowSchedule) return;
    // Set chat state to idle and lock schedule
    await sendCoachMessage("looks good, approve tomorrow's schedule");
  };

  return (
    <div className="flex flex-col gap-6 pb-10 h-full">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          AI PLAN NEGOTIATION
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          Tomorrow&apos;s Plan
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">{tomorrowStr}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start flex-1 min-h-0">
        
        {/* Left Column (5 cols): Tomorrow's Schedule */}
        <div className="lg:col-span-5 flex flex-col gap-6 h-full">
          <div className="glass-card rounded-2xl p-6 flex flex-col gap-5 flex-1 min-h-0 overflow-y-auto">
            <div className="flex justify-between items-center border-b border-brand-border pb-4">
              <h3 className="font-bold text-sm tracking-tight text-slate-100 flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-brand-accent" />
                Proposed Timeline
              </h3>
              
              {tomorrowSchedule && tomorrowSchedule.is_locked ? (
                <span className="text-[10px] font-bold text-brand-success bg-brand-success/15 border border-brand-success/30 px-2 py-0.5 rounded-md flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  LOCKED
                </span>
              ) : (
                <span className="text-[10px] font-bold text-brand-warning bg-brand-warning/15 border border-brand-warning/30 px-2 py-0.5 rounded-md flex items-center gap-1">
                  <Unlock className="w-3 h-3" />
                  UNLOCKED
                </span>
              )}
            </div>

            <div className="flex flex-col gap-4">
              {tomorrowSchedule && tomorrowSchedule.blocks && tomorrowSchedule.blocks.length > 0 ? (
                tomorrowSchedule.blocks.map((block) => {
                  const isBreak = block.type === "break";
                  
                  return (
                    <div 
                      key={block.id}
                      className={`p-3.5 rounded-xl border transition-all duration-300 ${
                        isBreak 
                          ? "border-brand-border/40 bg-brand-card/20 opacity-60" 
                          : "border-brand-border bg-brand-card/50 hover:border-brand-accent/50"
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <div className="min-w-0">
                          <h4 className="font-bold text-xs text-slate-200 truncate">{block.title}</h4>
                          <span className="text-[9px] text-brand-muted tracking-wider uppercase font-semibold mt-1 inline-block">
                            {block.planned_start.slice(0, 5)} - {block.planned_end.slice(0, 5)}
                          </span>
                        </div>
                        <span className={`text-[8px] font-black tracking-wider uppercase px-2 py-0.5 rounded ${
                          block.type === "agency" 
                            ? "bg-brand-accent/10 text-brand-accent border border-brand-accent/20" 
                            : block.type === "dsa"
                              ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                              : block.type === "deadline"
                                ? "bg-brand-success/10 text-brand-success border border-brand-success/20"
                                : "bg-slate-700 text-slate-400"
                        }`}>
                          {block.type}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="py-12 text-center text-brand-muted text-xs">
                  {loading ? "Generating timeline..." : "No timeline generated for tomorrow."}
                </div>
              )}
            </div>

            {tomorrowSchedule && !tomorrowSchedule.is_locked && (
              <button
                onClick={handleApprove}
                className="w-full mt-4 bg-brand-success hover:bg-brand-success/90 text-white font-extrabold p-4 rounded-xl text-xs transition-all duration-200 flex justify-center items-center gap-1.5 shadow-lg shadow-brand-success/15 glow-shadow-success"
              >
                <Check className="w-4 h-4" />
                Approve Schedule
              </button>
            )}
          </div>
        </div>

        {/* Right Column (7 cols): Claude Negotiation Chat */}
        <div className="lg:col-span-7 flex flex-col h-[580px] glass-card rounded-2xl overflow-hidden border border-brand-border">
          {/* Chat Header */}
          <div className="p-4 border-b border-brand-border bg-brand-card/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brand-accent" />
              <h3 className="font-bold text-sm text-slate-100">AI Chief of Staff</h3>
            </div>
            <span className="text-[10px] text-brand-success font-semibold flex items-center gap-1 bg-brand-success/10 px-2 py-0.5 rounded">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-success animate-pulse" />
              Active Negotiation
            </span>
          </div>

          {/* Messages Thread */}
          <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4 bg-brand-bg/40">
            {chatHistory.map((msg) => {
              const isCoach = msg.role === "coach";
              return (
                <div 
                  key={msg.id}
                  className={`flex ${isCoach ? "justify-start" : "justify-end"}`}
                >
                  <div className={`max-w-[85%] p-4 rounded-2xl text-xs leading-relaxed ${
                    isCoach 
                      ? "bg-brand-card border border-brand-border text-slate-200 rounded-tl-sm"
                      : "bg-brand-accent text-white font-medium rounded-tr-sm shadow-md shadow-brand-accent/10"
                  }`}>
                    {msg.content}
                  </div>
                </div>
              );
            })}
            
            {coachLoading && (
              <div className="flex justify-start">
                <div className="bg-brand-card border border-brand-border p-4 rounded-2xl rounded-tl-sm flex items-center gap-2 text-xs text-brand-muted">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-accent" />
                  Coach is validating & re-planning...
                </div>
              </div>
            )}
          </div>

          {/* Input Panel */}
          <form 
            onSubmit={handleSendMessage}
            className="p-4 border-t border-brand-border bg-brand-card/20 flex gap-2"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={tomorrowSchedule?.is_locked || coachLoading}
              placeholder={tomorrowSchedule?.is_locked ? "Tomorrow's schedule is locked." : "Negotiate times, e.g., 'Move DSA to 6 AM'..."}
              className="flex-1 bg-brand-bg border border-brand-border rounded-xl p-3 px-4 text-xs text-slate-100 placeholder-brand-muted focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            />
            <button
              type="submit"
              disabled={tomorrowSchedule?.is_locked || coachLoading || !inputMessage.trim()}
              className="bg-brand-accent hover:bg-brand-accent/90 disabled:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold p-3 px-5 rounded-xl text-xs transition-all flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              Send
            </button>
          </form>
        </div>
        
      </div>
    </div>
  );
}
