import { create } from "zustand";
import { api } from "@/lib/api";

export interface ScheduleBlock {
  id: number;
  schedule_version_id: number;
  title: string;
  type: string;
  source: string;
  priority: number;
  planned_start: string;
  planned_end: string;
  actual_start?: string;
  actual_end?: string;
  status: string;
  reason?: string;
}

export interface DailySchedule {
  id: number;
  date: string;
  user_id: number;
  energy_score?: number;
  is_locked: boolean;
  blocks: ScheduleBlock[];
}

export interface Deadline {
  id: number;
  title: string;
  client_name?: string;
  estimated_minutes: number;
  actual_minutes?: number;
  due_datetime: string;
  status: string;
  priority: number;
}

export interface Goal {
  id: number;
  name: string;
  ratio: number;
  minimum_minutes: number;
  priority: number;
}

export interface InboxItem {
  id: number;
  title: string;
  description?: string;
  source: string;
  priority: string;
  suggested_type: string;
  status: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "coach";
  content: string;
  timestamp: string;
}

export interface UserProfile {
  id: number;
  name: string;
  telegram_id: string;
  timezone: string;
  wake_time: string;
  sleep_time: string;
}

export interface AnalyticsData {
  reality_score: number;
  total_planned_hours: number;
  total_completed_hours: number;
  agency_planned_hours: number;
  agency_completed_hours: number;
  agency_score: number;
  dsa_planned_hours: number;
  dsa_completed_hours: number;
  dsa_score: number;
  gym_streak: number;
  completed_blocks_count: number;
  skipped_blocks_count: number;
  most_productive_day: string;
  least_productive_day: string;
  skip_reasons_breakdown: Record<string, number>;
  daily_focus_hours: Record<string, number>;
}

export interface CreateDeadlineInput {
  title: string;
  client_name?: string;
  estimated_minutes: number;
  due_datetime: string;
  priority: number;
}

export interface CreateInboxItemInput {
  title: string;
  description?: string;
  source?: string;
  priority?: string;
  suggested_type?: string;
}

export interface PatternCell {
  weekday: number;
  weekday_name: string;
  weekday_short: string;
  category: string;
  category_display: string;
  done: number;
  skipped: number;
  total: number;
  skip_rate: number;
  most_common_reason?: string | null;
  is_flagged: boolean;
}

export interface FlaggedPattern {
  weekday: number;
  weekday_name: string;
  weekday_plural: string;
  category: string;
  category_display: string;
  done: number;
  skipped: number;
  total: number;
  skip_rate: number;
  confidence: number;
  most_common_reason?: string | null;
  message: string;
}

export interface PatternsData {
  flagged_patterns: FlaggedPattern[];
  matrix: PatternCell[];
  summary: {
    total_blocks: number;
    total_completed: number;
    total_skipped: number;
    flagged_count: number;
    date_range: {
      start: string;
      end: string;
      days: number;
    };
  };
}

interface LifeOSState {
  user: UserProfile | null;
  todaySchedule: DailySchedule | null;
  tomorrowSchedule: DailySchedule | null;
  deadlines: Deadline[];
  goals: Goal[];
  inbox: InboxItem[];
  analytics: AnalyticsData | null;
  patterns: PatternsData | null;
  chatHistory: ChatMessage[];
  loading: boolean;
  coachLoading: boolean;
  error: string | null;

  // Actions
  fetchInitialData: () => Promise<void>;
  fetchPatterns: (days?: number) => Promise<void>;
  fetchScheduleForDate: (dateStr: string, isTomorrow?: boolean) => Promise<void>;
  updateBlockStatus: (blockId: number, status: string, reason?: string, dateStr?: string) => Promise<void>;
  createDeadline: (deadline: CreateDeadlineInput) => Promise<void>;
  deleteDeadline: (id: number) => Promise<void>;
  updateGoalRatios: (ratios: { id: number; ratio: number }[]) => Promise<void>;
  createInboxItem: (item: CreateInboxItemInput) => Promise<void>;
  updateInboxStatus: (id: number, status: string) => Promise<void>;
  sendCoachMessage: (text: string) => Promise<void>;
  setEnergy: (score: number) => Promise<void>;
  clearError: () => void;
}

export const useStore = create<LifeOSState>((set) => ({
  user: null,
  todaySchedule: null,
  tomorrowSchedule: null,
  deadlines: [],
  goals: [],
  inbox: [],
  analytics: null,
  patterns: null,
  chatHistory: [
    {
      id: "welcome",
      role: "coach",
      content: "LIFE OS active. Ready for review or inbox capture.",
      timestamp: new Date().toLocaleTimeString(),
    },
  ],
  loading: false,
  coachLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  fetchPatterns: async (days = 28) => {
    try {
      const patternsData = await api.getPatterns(days);
      set({ patterns: patternsData });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      console.error("Failed to fetch patterns:", message);
    }
  },

  fetchInitialData: async () => {
    set({ loading: true, error: null });
    try {
      const todayStr = new Date().toISOString().split("T")[0];
      const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split("T")[0];

      const [user, todaySched, tomorrowSched, deadlines, goals, inbox, analytics, patterns] = await Promise.all([
        api.getUser(),
        api.getSchedule(todayStr),
        api.getSchedule(tomorrowStr),
        api.getDeadlines(),
        api.getGoals(),
        api.getInbox(),
        api.getAnalytics(),
        api.getPatterns(28).catch(() => null),
      ]);

      set({
        user,
        todaySchedule: todaySched,
        tomorrowSchedule: tomorrowSched,
        deadlines,
        goals,
        inbox,
        analytics,
        patterns,
        loading: false,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message, loading: false });
    }
  },

  fetchScheduleForDate: async (dateStr: string, isTomorrow = false) => {
    set({ loading: true });
    try {
      const sched = await api.getSchedule(dateStr);
      if (isTomorrow) {
        set({ tomorrowSchedule: sched, loading: false });
      } else {
        set({ todaySchedule: sched, loading: false });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message, loading: false });
    }
  },

  updateBlockStatus: async (blockId: number, status: string, reason?: string, dateStr?: string) => {
    try {
      await api.updateBlockStatus(blockId, status, reason);
      const todayStr = new Date().toISOString().split("T")[0];
      const activeDate = dateStr || todayStr;
      
      // Refresh schedule
      const sched = await api.getSchedule(activeDate);
      if (activeDate === todayStr) {
        set({ todaySchedule: sched });
      } else {
        set({ tomorrowSchedule: sched });
      }
      
      // Refresh analytics in background
      const analytics = await api.getAnalytics();
      set({ analytics });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message });
    }
  },

  setEnergy: async (score: number) => {
    try {
      const todayStr = new Date().toISOString().split("T")[0];
      await api.setEnergy(todayStr, score);
      const todaySched = await api.getSchedule(todayStr);
      set({ todaySchedule: todaySched });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message });
    }
  },

  createDeadline: async (deadlineData: CreateDeadlineInput) => {
    set({ loading: true });
    try {
      await api.createDeadline(deadlineData);
      const [deadlines, analytics] = await Promise.all([api.getDeadlines(), api.getAnalytics()]);
      set({ deadlines, analytics, loading: false });
      
      // Regenerate tomorrow's schedule in background since a new deadline was added!
      const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const tomorrowSched = await api.generateSchedule(tomorrowStr);
      set({ tomorrowSchedule: tomorrowSched });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message, loading: false });
    }
  },

  deleteDeadline: async (id: number) => {
    set({ loading: true });
    try {
      await api.deleteDeadline(id);
      const deadlines = await api.getDeadlines();
      set({ deadlines, loading: false });
      
      // Regenerate tomorrow's schedule
      const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const tomorrowSched = await api.generateSchedule(tomorrowStr);
      set({ tomorrowSchedule: tomorrowSched });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message, loading: false });
    }
  },

  updateGoalRatios: async (ratios: { id: number; ratio: number }[]) => {
    set({ loading: true });
    try {
      const goals = await api.updateGoalRatios(ratios);
      set({ goals, loading: false });
      
      // Regenerate tomorrow's schedule
      const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const tomorrowSched = await api.generateSchedule(tomorrowStr);
      set({ tomorrowSchedule: tomorrowSched });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message, loading: false });
    }
  },

  createInboxItem: async (itemData: CreateInboxItemInput) => {
    set({ loading: true });
    try {
      await api.createInboxItem(itemData);
      const inbox = await api.getInbox();
      set({ inbox, loading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message, loading: false });
    }
  },

  updateInboxStatus: async (id: number, status: string) => {
    try {
      await api.updateInboxStatus(id, status);
      const inbox = await api.getInbox();
      set({ inbox });
      if (status === "scheduled") {
        const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split("T")[0];
        const tomorrowSched = await api.generateSchedule(tomorrowStr);
        set({ tomorrowSchedule: tomorrowSched });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({ error: message });
    }
  },

  sendCoachMessage: async (text: string) => {
    const userMsg: ChatMessage = {
      id: Math.random().toString(),
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString(),
    };
    
    set((state) => ({
      chatHistory: [...state.chatHistory, userMsg],
      coachLoading: true,
    }));

    try {
      const response = await api.sendCoachMessage(text);
      
      const coachMsg: ChatMessage = {
        id: Math.random().toString(),
        role: "coach",
        content: response.coach_message,
        timestamp: new Date().toLocaleTimeString(),
      };
      
      set((state) => ({
        chatHistory: [...state.chatHistory, coachMsg],
        coachLoading: false,
      }));

      // If negotiation caused updates, reload tomorrow's schedule
      if (response.actions_applied > 0 || response.negotiation_complete) {
        const tomorrowStr = new Date(Date.now() + 86400000).toISOString().split("T")[0];
        const tomorrowSched = await api.getSchedule(tomorrowStr);
        set({ tomorrowSchedule: tomorrowSched });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      set({
        error: message,
        coachLoading: false,
      });
    }
  },
}));
