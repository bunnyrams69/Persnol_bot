"use client";

import React, { useState } from "react";
import { useStore } from "@/store/useStore";
import { 
  BookOpen, 
  Trash2, 
  Clock, 
  Calendar
} from "lucide-react";

export default function DeadlinesPage() {
  const { deadlines, createDeadline, deleteDeadline, loading } = useStore();
  
  const [title, setTitle] = useState("");
  const [clientName, setClientName] = useState("");
  const [estMinutes, setEstMinutes] = useState(60);
  const [dueDate, setDueDate] = useState("");
  const [dueTime, setDueTime] = useState("23:59");
  const [priority, setPriority] = useState(3);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !dueDate) return;
    
    const combinedDue = `${dueDate}T${dueTime}:00`;
    
    await createDeadline({
      title: title.trim(),
      client_name: clientName.trim() || undefined,
      estimated_minutes: Number(estMinutes),
      due_datetime: combinedDue,
      priority: Number(priority)
    });

    setTitle("");
    setClientName("");
    setEstMinutes(60);
    setDueDate("");
    setDueTime("23:59");
    setPriority(3);
  };

  return (
    <div className="flex flex-col gap-8 pb-10">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          TASK MANAGEMENT
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          Client Deadlines
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">
          Deadlines are allocated first by the planner, prioritizing due date, priority, and estimated duration.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        
        {/* Deadlines List (2 cols) */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="glass-card rounded-2xl p-6.5 flex flex-col gap-4">
            <h3 className="text-xs text-brand-muted font-bold tracking-wider uppercase flex items-center gap-2 mb-2">
              <BookOpen className="w-4 h-4 text-brand-accent" />
              Active Deadlines ({deadlines.length})
            </h3>
            
            <div className="flex flex-col gap-4">
              {deadlines.length > 0 ? (
                deadlines.map((item) => {
                  const isCompleted = item.status === "completed";
                  const priorityStars = "★".repeat(item.priority) + "☆".repeat(5 - item.priority);
                  const isOverdue = new Date(item.due_datetime) < new Date() && !isCompleted;
                  
                  return (
                    <div 
                      key={item.id}
                      className="p-4 rounded-xl border border-brand-border bg-brand-card/30 hover:border-brand-accent/30 transition-all flex flex-col sm:flex-row justify-between gap-4 items-start"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2.5">
                          <h4 className={`font-bold text-sm truncate ${isCompleted ? "text-brand-success line-through opacity-65" : "text-slate-100"}`}>
                            {item.title}
                          </h4>
                          {item.client_name && (
                            <span className="text-[10px] font-bold text-brand-accent bg-brand-accent/10 border border-brand-accent/20 px-2 py-0.5 rounded">
                              {item.client_name}
                            </span>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-4 mt-3 text-[10px] text-brand-muted font-medium">
                          <span className="text-brand-warning">
                            {priorityStars}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" />
                            {item.estimated_minutes} min est.
                          </span>
                          <span className={`flex items-center gap-1 ${isOverdue ? 'text-brand-danger font-bold animate-pulse' : ''}`}>
                            <Calendar className="w-3.5 h-3.5" />
                            Due: {new Date(item.due_datetime).toLocaleString()}
                          </span>
                        </div>
                      </div>

                      {/* Actions */}
                      <button
                        onClick={() => deleteDeadline(item.id)}
                        className="p-2 rounded-lg border border-brand-border hover:bg-brand-danger/10 text-slate-400 hover:text-brand-danger hover:border-brand-danger/30 transition-all self-end sm:self-center"
                        title="Delete Deadline"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })
              ) : (
                <div className="py-12 text-center text-brand-muted text-xs">
                  No active deadlines. Clear schedule.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Add Deadline Form (1 col) */}
        <div className="glass-card rounded-2xl p-6 flex flex-col gap-5">
          <h3 className="font-bold text-sm tracking-tight text-slate-100">
            Create Deadline
          </h3>
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Task Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Color Grade Promo Reel"
                className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 transition-all"
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Client Name</label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="e.g. Sunrise Corp"
                className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Est. Minutes</label>
                <input
                  type="number"
                  value={estMinutes}
                  onChange={(e) => setEstMinutes(Number(e.target.value))}
                  placeholder="60"
                  className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent focus:ring-1 focus:ring-brand-accent/50 transition-all"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Priority (1-5)</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(Number(e.target.value))}
                  className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:border-brand-accent"
                >
                  {[1, 2, 3, 4, 5].map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Due Date</label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] text-brand-muted uppercase font-bold tracking-wider">Due Time</label>
                <input
                  type="time"
                  value={dueTime}
                  onChange={(e) => setDueTime(e.target.value)}
                  className="bg-brand-bg border border-brand-border rounded-xl p-3 text-xs text-slate-100 focus:outline-none focus:border-brand-accent"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !title.trim() || !dueDate}
              className="w-full mt-2 bg-brand-accent hover:bg-brand-accent/90 disabled:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-white font-extrabold p-3.5 rounded-xl text-xs transition-all duration-200 shadow-md shadow-brand-accent/15 glow-shadow-accent"
            >
              Add Deadline
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}
