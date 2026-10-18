"use client";

import React, { useState, useEffect } from "react";
import { DailySchedule, ScheduleBlock } from "@/store/useStore";
import { api } from "@/lib/api";
import { 
  CalendarDays, 
  Clock, 
  Loader2
} from "lucide-react";

export default function CalendarPage() {
  const [selectedOffset, setSelectedOffset] = useState(0); // 0 = today, 1 = tomorrow, etc.
  const [scheduleData, setScheduleData] = useState<DailySchedule | null>(null);
  const [loadingSchedule, setLoadingSchedule] = useState(true);

  // Generate the next 7 days dates list
  const next7Days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return {
      offset: i,
      dayName: d.toLocaleDateString(undefined, { weekday: "short" }),
      dateNum: d.getDate(),
      dateStr: d.toISOString().split("T")[0],
      isToday: i === 0,
    };
  });

  const activeDay = next7Days[selectedOffset];

  // Fetch schedule whenever active day changes
  useEffect(() => {
    const fetchDaySchedule = async () => {
      setLoadingSchedule(true);
      try {
        const data = await api.getSchedule(activeDay.dateStr);
        setScheduleData(data);
      } catch (err) {
        console.error("Failed to load schedule for calendar date:", err);
      } finally {
        setLoadingSchedule(false);
      }
    };
    fetchDaySchedule();
  }, [activeDay.dateStr]);

  return (
    <div className="flex flex-col gap-8 pb-10">
      {/* Header */}
      <div>
        <span className="text-xs text-brand-muted font-semibold tracking-wider uppercase">
          SCHEDULE AGENDA
        </span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-1">
          Calendar View
        </h2>
        <p className="text-sm text-brand-muted mt-0.5">
          Inspect daily plans, review past logs, and check completed blocks.
        </p>
      </div>

      {/* Horizontal Day Selector */}
      <div className="grid grid-cols-7 gap-3.5 bg-brand-card/25 border border-brand-border rounded-2xl p-4.5">
        {next7Days.map((day) => {
          const isActive = selectedOffset === day.offset;
          
          return (
            <button
              key={day.offset}
              onClick={() => setSelectedOffset(day.offset)}
              className={`flex flex-col items-center gap-1 p-3 rounded-xl border transition-all duration-200 ${
                isActive 
                  ? "bg-brand-accent/15 border-brand-accent text-brand-accent shadow-lg shadow-brand-accent/5" 
                  : "bg-brand-card/40 border-brand-border/60 text-slate-400 hover:text-slate-200 hover:border-brand-border"
              }`}
            >
              <span className="text-[10px] uppercase font-bold tracking-wider">{day.dayName}</span>
              <span className="text-xl font-black">{day.dateNum}</span>
              {day.isToday && (
                <span className="w-1.5 h-1.5 rounded-full bg-brand-accent mt-1" />
              )}
            </button>
          );
        })}
      </div>

      {/* Daily Timeline */}
      <div className="glass-card rounded-2xl p-6.5 min-h-[400px] flex flex-col gap-6">
        <div className="flex justify-between items-center border-b border-brand-border pb-4">
          <h3 className="font-bold text-sm tracking-tight text-slate-100 flex items-center gap-2">
            <CalendarDays className="w-4 h-4 text-brand-accent" />
            Agenda for {new Date(activeDay.dateStr).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
          </h3>
          
          {scheduleData && (
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              scheduleData.is_locked 
                ? "bg-brand-success/10 text-brand-success border border-brand-success/20" 
                : "bg-brand-warning/10 text-brand-warning border border-brand-warning/20"
            }`}>
              {scheduleData.is_locked ? "Locked" : "Draft"}
            </span>
          )}
        </div>

        {loadingSchedule ? (
          <div className="flex-1 flex justify-center items-center py-20 text-xs text-brand-muted gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-brand-accent" />
            Fetching calendar timeline...
          </div>
        ) : scheduleData && scheduleData.blocks && scheduleData.blocks.length > 0 ? (
          <div className="flex flex-col relative border-l border-brand-border ml-2 pl-6 gap-6 my-2">
            {scheduleData.blocks.map((block: ScheduleBlock) => {
              const isCompleted = block.status === "completed";
              const isSkipped = block.status === "skipped";
              const isBreak = block.type === "break";
              
              return (
                <div key={block.id} className="relative">
                  {/* Timeline bullet */}
                  <span className={`w-3.5 h-3.5 rounded-full absolute -left-[31px] top-1 border-2 border-brand-bg z-10 ${
                    isCompleted 
                      ? "bg-brand-success" 
                      : isSkipped 
                        ? "bg-brand-danger" 
                        : isBreak
                          ? "bg-slate-700"
                          : "bg-brand-accent"
                  }`} />

                  <div className="flex justify-between items-center gap-4">
                    <div>
                      <h4 className={`font-bold text-sm text-slate-200 ${isCompleted ? 'line-through opacity-65 text-brand-success' : isSkipped ? 'opacity-70 text-brand-danger' : ''}`}>
                        {block.title}
                      </h4>
                      <span className="text-[10px] text-brand-muted tracking-wide font-semibold mt-0.5 inline-block uppercase">
                        <Clock className="w-3 h-3 inline mr-1 text-brand-muted" />
                        {block.planned_start.slice(0, 5)} - {block.planned_end.slice(0, 5)}
                        {block.reason && <span className="text-brand-danger italic ml-1.5">({block.reason})</span>}
                      </span>
                    </div>

                    <span className={`text-[8px] font-black tracking-wider uppercase px-2 py-0.5 rounded border ${
                      isCompleted 
                        ? "bg-brand-success/10 text-brand-success border-brand-success/20" 
                        : isSkipped 
                          ? "bg-brand-danger/10 text-brand-danger border-brand-danger/20" 
                          : "bg-slate-800 text-slate-400 border-slate-700/50"
                    }`}>
                      {block.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex-1 flex flex-col justify-center items-center py-20 text-brand-muted text-xs gap-1.5">
            <CalendarDays className="w-8 h-8 opacity-20 text-brand-muted" />
            No schedule blocks recorded for this date.
          </div>
        )}
      </div>
    </div>
  );
}
