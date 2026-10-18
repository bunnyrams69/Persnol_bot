"use client";

import React, { useState, useEffect } from "react";
import { useStore } from "@/store/useStore";
import { api } from "@/lib/api";
import { 
  MessageSquare, 
  Send, 
  Loader2, 
  ShieldCheck, 
  Database
} from "lucide-react";

interface ProfileFact {
  key: string;
  value: string;
}

interface MemoryGoalItem {
  goal: string;
  priority: number;
  deadline?: string;
}

export default function CoachChatPage() {
  const { chatHistory, coachLoading, sendCoachMessage } = useStore();
  const [inputMessage, setInputMessage] = useState("");
  
  // Local memory variables loaded from coach chat endpoint
  const [profileFacts, setProfileFacts] = useState<ProfileFact[]>([]);
  const [beliefs, setBeliefs] = useState<string[]>([]);
  const [goals, setGoals] = useState<MemoryGoalItem[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(true);

  useEffect(() => {
    const fetchMemory = async () => {
      try {
        const data = await api.getCoachContext();
        setProfileFacts(data.profile || []);
        setBeliefs(data.beliefs || []);
        setGoals(data.goals || []);
      } catch (err) {
        console.error("Failed to load memory context:", err);
      } finally {
        setMemoryLoading(false);
      }
    };
    fetchMemory();
  }, [chatHistory]); // reload memory when chat history updates (as chat updates memory!)

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || coachLoading) return;
    const msg = inputMessage;
    setInputMessage("");
    await sendCoachMessage(msg);
  };

  return (
    <div className="flex flex-col gap-6 pb-10 h-full">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          EXECUTIVE MENTORSHIP
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          AI Coach Conversation
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">
          Steve Jobs as planner, Naval as coach, a strict friend as accountability partner.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start flex-1 min-h-0">
        
        {/* Left Column (4 cols): Long-Term Memory Profile */}
        <div className="lg:col-span-4 flex flex-col gap-6 h-full">
          <div className="glass-card rounded-2xl p-6.5 flex flex-col gap-5 flex-1 min-h-0 overflow-y-auto max-h-[580px]">
            <h3 className="font-bold text-xs text-slate-100 flex items-center gap-2 uppercase tracking-wider border-b border-brand-border pb-3">
              <Database className="w-4 h-4 text-brand-accent" />
              Long-Term Memory Model
            </h3>

            {memoryLoading ? (
              <div className="py-12 text-center text-xs text-brand-muted flex justify-center items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-brand-accent" />
                Querying memory vector store...
              </div>
            ) : (
              <div className="flex flex-col gap-5 text-xs text-slate-300">
                {/* Profile Facts */}
                <div className="flex flex-col gap-2">
                  <h4 className="font-bold text-brand-accent uppercase tracking-wide text-[10px]">Demographic Profile</h4>
                  {profileFacts.length > 0 ? (
                    <ul className="flex flex-col gap-1.5 list-disc pl-4 text-brand-muted">
                      {profileFacts.map(p => (
                        <li key={p.key}>
                          <span className="text-slate-300 capitalize">{p.key.replace("_", " ")}:</span> {p.value}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-brand-muted italic">No profile variables populated.</p>
                  )}
                </div>

                {/* Beliefs */}
                <div className="flex flex-col gap-2">
                  <h4 className="font-bold text-brand-accent uppercase tracking-wide text-[10px]">Stated Beliefs & Rules</h4>
                  {beliefs.length > 0 ? (
                    <ul className="flex flex-col gap-1.5 list-disc pl-4 text-brand-muted">
                      {beliefs.map((b, i) => (
                        <li key={i}>{b}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-brand-muted italic">No belief statements parsed yet.</p>
                  )}
                </div>

                {/* Active Goals */}
                <div className="flex flex-col gap-2">
                  <h4 className="font-bold text-brand-accent uppercase tracking-wide text-[10px]">Focus Milestones</h4>
                  {goals.length > 0 ? (
                    <ul className="flex flex-col gap-1.5 list-disc pl-4 text-brand-muted">
                      {goals.map((g, i) => (
                        <li key={i}>
                          <span className="text-slate-300">{g.goal}</span>
                          {g.deadline && ` (Due: ${new Date(g.deadline).toLocaleDateString()})`}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-brand-muted italic">No target milestones logged.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column (8 cols): Coach Chat Conversation */}
        <div className="lg:col-span-8 flex flex-col h-[580px] glass-card rounded-2xl overflow-hidden border border-brand-border">
          {/* Header */}
          <div className="p-4 border-b border-brand-border bg-brand-card/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brand-accent" />
              <h3 className="font-bold text-sm text-slate-100">Direct Chat Thread</h3>
            </div>
            <span className="text-[10px] text-brand-success font-semibold flex items-center gap-1 bg-brand-success/10 px-2 py-0.5 rounded">
              <ShieldCheck className="w-3.5 h-3.5" />
              Blunt Personality Active
            </span>
          </div>

          {/* Messages */}
          <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4 bg-brand-bg/40">
            {chatHistory.map((msg) => {
              const isCoach = msg.role === "coach";
              return (
                <div 
                  key={msg.id}
                  className={`flex ${isCoach ? "justify-start" : "justify-end"}`}
                >
                  <div className={`max-w-[80%] p-4 rounded-2xl text-xs leading-relaxed ${
                    isCoach 
                      ? "bg-brand-card border border-brand-border text-slate-200 rounded-tl-sm"
                      : "bg-brand-accent text-white font-medium rounded-tr-sm shadow-md"
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
                  Coach is reasoning...
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
              disabled={coachLoading}
              placeholder="Ask anything or discuss productivity blockers..."
              className="flex-1 bg-brand-bg border border-brand-border rounded-xl p-3 px-4 text-xs text-slate-100 placeholder-brand-muted focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 disabled:opacity-50 transition-all"
            />
            <button
              type="submit"
              disabled={coachLoading || !inputMessage.trim()}
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
