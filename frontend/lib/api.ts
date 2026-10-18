const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiRequest(path: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${path}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export const api = {
  // User Profile
  getUser: () => apiRequest("/api/user"),
  updateUser: (data: { name?: string; wake_time?: string; sleep_time?: string }) =>
    apiRequest("/api/user", { method: "PUT", body: JSON.stringify(data) }),

  // Schedule
  getSchedule: (dateStr: string) => apiRequest(`/api/schedule/date/${dateStr}`),
  generateSchedule: (dateStr: string) =>
    apiRequest(`/api/schedule/generate?date_str=${dateStr}`, { method: "POST" }),
  updateBlockStatus: (blockId: number, status: string, reason?: string) =>
    apiRequest(`/api/schedule/block/${blockId}/status`, {
      method: "POST",
      body: JSON.stringify({ status, reason }),
    }),
  setEnergy: (dateStr: string, score: number) =>
    apiRequest(`/api/schedule/date/${dateStr}/energy?score=${score}`, { method: "POST" }),


  // Deadlines
  getDeadlines: () => apiRequest("/api/deadlines"),
  createDeadline: (data: {
    title: string;
    client_name?: string;
    estimated_minutes: number;
    due_datetime: string;
    priority: number;
  }) =>
    apiRequest("/api/deadlines", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteDeadline: (id: number) => apiRequest(`/api/deadlines/${id}`, { method: "DELETE" }),

  // Goals
  getGoals: () => apiRequest("/api/goals"),
  updateGoalRatios: (ratios: { id: number; ratio: number }[]) =>
    apiRequest("/api/goals", {
      method: "PUT",
      body: JSON.stringify({ ratios }),
    }),

  // Inbox
  getInbox: () => apiRequest("/api/inbox"),
  createInboxItem: (data: {
    title: string;
    description?: string;
    source?: string;
    priority?: string;
    suggested_type?: string;
  }) =>
    apiRequest("/api/inbox", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateInboxStatus: (id: number, status: string) =>
    apiRequest(`/api/inbox/${id}?status=${status}`, { method: "PUT" }),

  // Analytics & Patterns
  getAnalytics: () => apiRequest("/api/analytics"),
  getPatterns: (days: number = 28) => apiRequest(`/api/patterns?days=${days}`),

  // Coach Chat
  getCoachContext: () => apiRequest("/api/coach/chat"),
  sendCoachMessage: (message: string) =>
    apiRequest("/api/coach/message", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
