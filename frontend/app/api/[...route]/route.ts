import { NextRequest, NextResponse } from "next/server";

// In-memory persistent data store for serverless demo
const store = {
  user: {
    id: 1,
    name: "Bunny",
    telegram_id: "bunnyrams69",
    timezone: "Asia/Kolkata",
    wake_time: "07:00",
    sleep_time: "23:00",
  },
  energyScores: {} as Record<string, number>,
  goals: [
    { id: 1, name: "AI Agency", ratio: 0.60, minimum_minutes: 120, priority: 1 },
    { id: 2, name: "DSA & Algorithms", ratio: 0.40, minimum_minutes: 90, priority: 2 },
  ],
  deadlines: [
    {
      id: 1,
      title: "Telegram Bot Deployment & Webhook Setup",
      client_name: "Apex Digital",
      estimated_minutes: 180,
      actual_minutes: 120,
      due_datetime: new Date(Date.now() + 3 * 86400000).toISOString(),
      status: "in_progress",
      priority: 1,
    },
    {
      id: 2,
      title: "AI Coaching Logic & Evaluation Flow",
      client_name: "Life OS Core",
      estimated_minutes: 120,
      actual_minutes: 90,
      due_datetime: new Date(Date.now() + 5 * 86400000).toISOString(),
      status: "pending",
      priority: 2,
    },
    {
      id: 3,
      title: "Stripe Billing & Subscription Webhooks",
      client_name: "FinTech Labs",
      estimated_minutes: 240,
      actual_minutes: undefined,
      due_datetime: new Date(Date.now() + 8 * 86400000).toISOString(),
      status: "pending",
      priority: 1,
    },
  ],
  inbox: [
    {
      id: 1,
      title: "Review Anthropic Prompt Caching latency metrics",
      description: "Benchmark time to first token on 10k token prompts",
      source: "telegram",
      priority: "high",
      suggested_type: "task",
      status: "pending",
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: 2,
      title: "Restock protein isolate and creatine",
      description: "Replenish supplies before weekend session",
      source: "web",
      priority: "medium",
      suggested_type: "errand",
      status: "pending",
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
    {
      id: 3,
      title: "Draft system prompt for deterministic habit agent",
      description: "Include pattern detector confidence threshold at >= 0.60",
      source: "telegram",
      priority: "high",
      suggested_type: "idea",
      status: "processed",
      created_at: new Date(Date.now() - 86400000).toISOString(),
    },
  ],
  blocks: [
    {
      id: 1,
      schedule_version_id: 1,
      title: "Morning Routine & Day Calibration",
      type: "fixed",
      source: "routine",
      priority: 1,
      planned_start: "07:00",
      planned_end: "08:00",
      status: "completed",
      reason: undefined,
    },
    {
      id: 2,
      schedule_version_id: 1,
      title: "DSA & Problem Solving (Trees & Dynamic Programming)",
      type: "goal",
      source: "dsa",
      priority: 1,
      planned_start: "08:30",
      planned_end: "10:30",
      status: "completed",
      reason: undefined,
    },
    {
      id: 3,
      schedule_version_id: 1,
      title: "AI Agency - Client Bot Architecture",
      type: "goal",
      source: "agency",
      priority: 1,
      planned_start: "11:00",
      planned_end: "14:00",
      status: "completed",
      reason: undefined,
    },
    {
      id: 4,
      schedule_version_id: 1,
      title: "Telegram Bot Webhook & Cloud Deployment",
      type: "deadline",
      source: "client",
      priority: 2,
      planned_start: "15:00",
      planned_end: "17:00",
      status: "pending",
      reason: undefined,
    },
    {
      id: 5,
      schedule_version_id: 1,
      title: "Gym - Strength & Conditioning Workout",
      type: "fixed",
      source: "gym",
      priority: 1,
      planned_start: "18:00",
      planned_end: "19:30",
      status: "pending",
      reason: undefined,
    },
    {
      id: 6,
      schedule_version_id: 1,
      title: "Nightly AI Review & Tomorrow Negotiation",
      type: "routine",
      source: "system",
      priority: 2,
      planned_start: "21:30",
      planned_end: "22:00",
      status: "pending",
      reason: undefined,
    },
  ],
};

function getScheduleForDate(dateStr: string) {
  const energy = store.energyScores[dateStr] || 4;
  return {
    id: 101,
    date: dateStr,
    user_id: 1,
    energy_score: energy,
    is_locked: true,
    blocks: store.blocks,
  };
}

function getPatternsData() {
  const weekdays = [
    { num: 0, name: "Monday", short: "Mon", plural: "Mondays" },
    { num: 1, name: "Tuesday", short: "Tue", plural: "Tuesdays" },
    { num: 2, name: "Wednesday", short: "Wed", plural: "Wednesdays" },
    { num: 3, name: "Thursday", short: "Thu", plural: "Thursdays" },
    { num: 4, name: "Friday", short: "Fri", plural: "Fridays" },
    { num: 5, name: "Saturday", short: "Sat", plural: "Saturdays" },
    { num: 6, name: "Sunday", short: "Sun", plural: "Sundays" },
  ];

  const categories = [
    { key: "gym", display: "Gym & Fitness" },
    { key: "agency", display: "AI Agency" },
    { key: "dsa", display: "DSA Practice" },
    { key: "deadline", display: "Client Deadlines" },
  ];

  const matrix = [];
  for (const day of weekdays) {
    for (const cat of categories) {
      let done = 3;
      let skipped = 1;
      let reason: string | null = null;
      let isFlagged = false;

      if (day.num === 2 && cat.key === "dsa") {
        // Wednesday DSA skip pattern
        done = 1;
        skipped = 3;
        reason = "Too tired after college";
        isFlagged = true;
      } else if (day.num === 6 && cat.key === "agency") {
        // Sunday Agency burnout
        done = 1;
        skipped = 3;
        reason = "Weekend burnout";
        isFlagged = true;
      } else if (cat.key === "gym") {
        done = 4;
        skipped = 0;
      }

      const total = done + skipped;
      const skipRate = total > 0 ? skipped / total : 0;

      matrix.push({
        weekday: day.num,
        weekday_name: day.name,
        weekday_short: day.short,
        category: cat.key,
        category_display: cat.display,
        done,
        skipped,
        total,
        skip_rate: Math.round(skipRate * 100) / 100,
        most_common_reason: reason,
        is_flagged: isFlagged,
      });
    }
  }

  return {
    flagged_patterns: [
      {
        weekday: 2,
        weekday_name: "Wednesday",
        weekday_plural: "Wednesdays",
        category: "dsa",
        category_display: "DSA Practice",
        done: 1,
        skipped: 3,
        total: 4,
        skip_rate: 0.75,
        confidence: 0.88,
        most_common_reason: "Too tired after college",
        message: "You skipped 75% of DSA sessions on Wednesdays. Common reason: 'Too tired after college'.",
      },
      {
        weekday: 6,
        weekday_name: "Sunday",
        weekday_plural: "Sundays",
        category: "agency",
        category_display: "AI Agency",
        done: 1,
        skipped: 3,
        total: 4,
        skip_rate: 0.75,
        confidence: 0.82,
        most_common_reason: "Weekend burnout",
        message: "You skipped 75% of AI Agency sessions on Sundays. Common reason: 'Weekend burnout'.",
      },
    ],
    matrix,
    summary: {
      total_blocks: 112,
      total_completed: 92,
      total_skipped: 20,
      flagged_count: 2,
      date_range: {
        start: new Date(Date.now() - 28 * 86400000).toISOString().split("T")[0],
        end: new Date().toISOString().split("T")[0],
        days: 28,
      },
    },
  };
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ route: string[] }> }
) {
  const { route } = await context.params;
  const path = "/" + (route || []).join("/");
  const url = new URL(req.url);

  // User Profile
  if (path === "/user") {
    return NextResponse.json(store.user);
  }

  // Schedule by Date
  if (path.startsWith("/schedule/date/")) {
    const parts = path.split("/");
    const dateStr = parts[parts.length - 1] || new Date().toISOString().split("T")[0];
    return NextResponse.json(getScheduleForDate(dateStr));
  }

  // Deadlines
  if (path === "/deadlines") {
    return NextResponse.json(store.deadlines);
  }

  // Goals
  if (path === "/goals") {
    return NextResponse.json(store.goals);
  }

  // Inbox
  if (path === "/inbox") {
    return NextResponse.json(store.inbox);
  }

  // Analytics
  if (path === "/analytics") {
    return NextResponse.json({
      reality_score: 82,
      total_planned_hours: 112,
      total_completed_hours: 92,
      agency_planned_hours: 58,
      agency_completed_hours: 49,
      agency_score: 84,
      dsa_planned_hours: 38,
      dsa_completed_hours: 31,
      dsa_score: 81,
      gym_streak: 9,
      completed_blocks_count: 52,
      skipped_blocks_count: 8,
      most_productive_day: "Tuesday",
      least_productive_day: "Wednesday",
      skip_reasons_breakdown: {
        "Too tired": 4,
        "Unexpected work": 2,
        "Bad planning": 1,
        "Distraction": 1,
      },
      daily_focus_hours: {
        Mon: 6.5,
        Tue: 7.2,
        Wed: 4.1,
        Thu: 6.8,
        Fri: 5.9,
        Sat: 5.0,
        Sun: 3.8,
      },
    });
  }

  // Patterns
  if (path === "/patterns") {
    return NextResponse.json(getPatternsData());
  }

  // Coach Chat Context
  if (path === "/coach/chat") {
    return NextResponse.json({
      user: store.user,
      today: getScheduleForDate(new Date().toISOString().split("T")[0]),
      patterns: getPatternsData().flagged_patterns,
      system_status: "Active - Ready for evening review & negotiation",
    });
  }

  return NextResponse.json({ error: `Not Found: ${path}` }, { status: 404 });
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ route: string[] }> }
) {
  const { route } = await context.params;
  const path = "/" + (route || []).join("/");
  const url = new URL(req.url);

  // Schedule Generate
  if (path === "/schedule/generate") {
    const dateStr = url.searchParams.get("date_str") || new Date().toISOString().split("T")[0];
    return NextResponse.json(getScheduleForDate(dateStr));
  }

  // Energy Score
  if (path.includes("/energy")) {
    const score = parseInt(url.searchParams.get("score") || "4", 10);
    const dateStr = path.split("/")[3] || new Date().toISOString().split("T")[0];
    store.energyScores[dateStr] = score;
    return NextResponse.json({ success: true, date: dateStr, score });
  }

  // Block Status Update
  if (path.includes("/status")) {
    const body = await req.json().catch(() => ({}));
    const blockId = parseInt(path.split("/")[3] || "1", 10);
    const block = store.blocks.find((b) => b.id === blockId);
    if (block) {
      block.status = body.status || "completed";
      if (body.reason) block.reason = body.reason;
    }
    return NextResponse.json({ success: true, blockId, status: body.status });
  }

  // Create Deadline
  if (path === "/deadlines") {
    const body = await req.json().catch(() => ({}));
    const newDeadline = {
      id: Date.now(),
      title: body.title || "New Deadline",
      client_name: body.client_name || "Self",
      estimated_minutes: Number(body.estimated_minutes) || 60,
      actual_minutes: undefined,
      due_datetime: body.due_datetime || new Date(Date.now() + 86400000).toISOString(),
      status: "pending",
      priority: Number(body.priority) || 1,
    };
    store.deadlines.push(newDeadline);
    return NextResponse.json(newDeadline);
  }

  // Create Inbox Item
  if (path === "/inbox") {
    const body = await req.json().catch(() => ({}));
    const newItem = {
      id: Date.now(),
      title: body.title || "Untitled Task",
      description: body.description || "",
      source: body.source || "web",
      priority: body.priority || "medium",
      suggested_type: body.suggested_type || "task",
      status: "pending",
      created_at: new Date().toISOString(),
    };
    store.inbox.unshift(newItem);
    return NextResponse.json(newItem);
  }

  // AI Coach Message
  if (path === "/coach/message") {
    const body = await req.json().catch(() => ({}));
    const userMsg = (body.message || "").toLowerCase();

    let coachReply =
      "I've analyzed your schedule and active commitments. Your Agency work is on track at 84%, but watch out for Wednesday DSA fatigue. What specific adjustments should we lock in for tomorrow?";

    if (userMsg.includes("tired") || userMsg.includes("skip")) {
      coachReply =
        "Pattern alert: You've flagged tiredness on Wednesdays before. Rather than skipping entirely, let's negotiate a 30-minute low-intensity LeetCode review instead of a heavy 2-hour block. Deal?";
    } else if (userMsg.includes("schedule") || userMsg.includes("tomorrow")) {
      coachReply =
        "Tomorrow's plan has 6 hours allocated: 3.5h for Agency bot deployment, 1.5h for DSA trees, and 1h for workout. All high-priority deadlines are protected with buffer.";
    } else if (userMsg.includes("goal") || userMsg.includes("agency")) {
      coachReply =
        "Your current ratio is Agency 60% / DSA 40%. You've logged 49 hours towards Agency this month. High velocity—keep pushing!";
    }

    return NextResponse.json({
      response: coachReply,
      status: "ok",
      timestamp: new Date().toLocaleTimeString(),
    });
  }

  return NextResponse.json({ error: `Not Found: ${path}` }, { status: 404 });
}

export async function PUT(
  req: NextRequest,
  context: { params: Promise<{ route: string[] }> }
) {
  const { route } = await context.params;
  const path = "/" + (route || []).join("/");
  const url = new URL(req.url);

  // Update User
  if (path === "/user") {
    const body = await req.json().catch(() => ({}));
    store.user = { ...store.user, ...body };
    return NextResponse.json(store.user);
  }

  // Update Goals
  if (path === "/goals") {
    const body = await req.json().catch(() => ({}));
    if (Array.isArray(body.ratios)) {
      for (const r of body.ratios) {
        const goal = store.goals.find((g) => g.id === r.id);
        if (goal) goal.ratio = r.ratio;
      }
    }
    return NextResponse.json({ success: true, goals: store.goals });
  }

  // Update Inbox Status
  if (path.startsWith("/inbox/")) {
    const id = parseInt(path.split("/")[2] || "0", 10);
    const status = url.searchParams.get("status") || "processed";
    const item = store.inbox.find((i) => i.id === id);
    if (item) item.status = status;
    return NextResponse.json({ success: true, id, status });
  }

  return NextResponse.json({ error: `Not Found: ${path}` }, { status: 404 });
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ route: string[] }> }
) {
  const { route } = await context.params;
  const path = "/" + (route || []).join("/");

  if (path.startsWith("/deadlines/")) {
    const id = parseInt(path.split("/")[2] || "0", 10);
    store.deadlines = store.deadlines.filter((d) => d.id !== id);
    return NextResponse.json({ success: true, id });
  }

  return NextResponse.json({ error: `Not Found: ${path}` }, { status: 404 });
}
