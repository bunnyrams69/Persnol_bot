"use client";

import React, { useState } from "react";
import { useStore } from "@/store/useStore";
import { 
  Inbox, 
  Archive, 
  Calendar, 
  Clock
} from "lucide-react";

export default function InboxPage() {
  const { inbox, createInboxItem, updateInboxStatus, loading } = useStore();
  
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [type, setType] = useState("personal");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await createInboxItem({
      title: title.trim(),
      description: description.trim() || undefined,
      priority,
      suggested_type: type,
      source: "manual"
    });
    setTitle("");
    setDescription("");
    setPriority("medium");
    setType("personal");
  };

  return (
    <div className="flex flex-col gap-8 pb-10">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          INCOMING CAPTURE
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          Life Inbox
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">
          Everything goes here first. Claude extracts parameters and helps schedule them.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        
        {/* Inbox List (2 cols) */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="glass-card rounded-2xl p-6.5 flex flex-col gap-4">
            <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase flex items-center gap-2 mb-2">
              <Inbox className="w-4 h-4 text-brand-accent" />
              Active Cards ({inbox.length})
            </h3>
            
            <div className="flex flex-col gap-4">
              {inbox.length > 0 ? (
                inbox.map((item) => {
                  const p_color = 
                    item.priority === "urgent" 
                      ? "text-brand-danger bg-brand-danger/10 border-brand-danger/20" 
                      : item.priority === "high"
                        ? "text-brand-warning bg-brand-warning/10 border-brand-warning/20"
                        : "text-slate-300 bg-slate-800 border-slate-700/50";
                        
                  return (
                    <div 
                      key={item.id}
                      className="p-4 rounded-xl border border-brand-border bg-brand-card/30 hover:border-brand-accent/30 transition-all flex flex-col sm:flex-row justify-between gap-4 items-start"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2.5">
                          <h4 className="font-bold text-sm text-slate-100 truncate">{item.title}</h4>
                          <span className={`text-[8px] font-black tracking-wider uppercase px-2 py-0.5 rounded border ${p_color}`}>
                            {item.priority}
                          </span>
                        </div>
                        {item.description && (
                          <p className="text-xs text-brand-muted mt-1.5 leading-relaxed">{item.description}</p>
                        )}
                        
                        <div className="flex items-center gap-3 mt-3 text-[10px] text-brand-muted font-medium">
                          <span className="bg-brand-border/40 px-2 py-0.5 rounded uppercase">
                            Source: {item.source}
                          </span>
                          <span className="bg-brand-border/40 px-2 py-0.5 rounded uppercase">
                            Category: {item.suggested_type}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(item.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <button
                          onClick={() => updateInboxStatus(item.id, "scheduled")}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-brand-accent/20 bg-brand-accent/10 hover:bg-brand-accent text-brand-accent hover:text-white transition-all text-xs font-bold"
                          title="Schedule this card"
                        >
                          <Calendar className="w-3.5 h-3.5" />
                          Schedule
                        </button>
                        <button
                          onClick={() => updateInboxStatus(item.id, "archived")}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-brand-border hover:bg-brand-card/60 text-slate-400 hover:text-slate-200 transition-all text-xs font-bold"
                          title="Archive card"
                        >
                          <Archive className="w-3.5 h-3.5" />
                          Archive
                        </button>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="py-12 text-center text-brand-muted text-xs">
                  Your inbox is clean. Excellent organization.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Add Card Form (1 col) */}
        <div className="glass-card rounded-2xl p-6 flex flex-col gap-5">
          <h3 className="font-bold text-sm tracking-tight text-slate-100">
            Create Inbox Card
          </h3>
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Finish client reel"
                className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 transition-all"
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional details, links, checklists..."
                rows={3}
                className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 transition-all resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Priority</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:border-brand-accent"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Type</label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:border-brand-accent"
                >
                  <option value="personal">Personal</option>
                  <option value="deadline">Deadline</option>
                  <option value="dsa">DSA</option>
                  <option value="agency">AI Agency</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="w-full mt-2 bg-brand-accent hover:bg-brand-accent/90 disabled:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-white font-extrabold p-3.5 rounded-xl text-xs transition-all duration-200 shadow-md shadow-brand-accent/15 glow-shadow-accent"
            >
              Add to Inbox
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}
