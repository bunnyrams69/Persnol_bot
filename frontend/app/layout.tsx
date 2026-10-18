"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useStore } from "@/store/useStore";
import { 
  LayoutDashboard, 
  CalendarDays, 
  Clock, 
  Inbox, 
  TrendingUp, 
  Flame, 
  MessageSquare, 
  Settings as SettingsIcon,
  BookOpen,
  PieChart,
  Sparkles
} from "lucide-react";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const fetchInitialData = useStore((state) => state.fetchInitialData);
  const analytics = useStore((state) => state.analytics);
  const user = useStore((state) => state.user);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  const navItems = [
    { name: "Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Tomorrow Plan", path: "/tomorrow", icon: Clock },
    { name: "Calendar", path: "/calendar", icon: CalendarDays },
    { name: "Inbox", path: "/inbox", icon: Inbox },
    { name: "Deadlines", path: "/deadlines", icon: BookOpen },
    { name: "Goals & Ratios", path: "/goals", icon: PieChart },
    { name: "AI Coach Chat", path: "/coach", icon: MessageSquare },
    { name: "Analytics", path: "/analytics", icon: TrendingUp },
    { name: "Patterns", path: "/patterns", icon: Sparkles },
    { name: "Settings", path: "/settings", icon: SettingsIcon },
  ];

  return (
    <html lang="en">
      <head>
        <title>LIFE OS - AI Chief of Staff</title>
        <meta name="description" content="AI Chief of Staff for Students and Creators" />
      </head>
      <body className={`flex h-screen w-screen bg-brand-bg text-slate-100 overflow-hidden font-sans ${inter.className}`}>
        {/* Sidebar Nav */}
        <aside className="w-72 h-full flex flex-col justify-between p-6 border-r border-brand-border bg-brand-card/30 backdrop-blur-md">
          <div className="flex flex-col gap-8">
            {/* Title / Brand */}
            <div className="flex items-center gap-3 py-2 px-1">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-accent to-indigo-500 flex items-center justify-center font-bold text-white text-base shadow-lg glow-shadow-accent">
                L
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                  LIFE OS
                </h1>
                <span className="text-[10px] text-brand-muted tracking-wider uppercase font-semibold">
                  AI CHIEF OF STAFF
                </span>
              </div>
            </div>

            {/* Quick KPI stats in sidebar */}
            {analytics && (
              <div className="flex flex-col gap-2 p-3.5 rounded-xl border border-brand-border bg-brand-card/50">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-brand-muted">Reality Score</span>
                  <span className={`font-bold ${analytics.reality_score >= 70 ? 'text-brand-success' : 'text-brand-danger'}`}>
                    {analytics.reality_score}%
                  </span>
                </div>
                <div className="w-full bg-brand-border h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-brand-accent h-full rounded-full transition-all duration-500" 
                    style={{ width: `${analytics.reality_score}%` }}
                  />
                </div>
                <div className="flex justify-between items-center text-xs mt-1 text-slate-300">
                  <span className="flex items-center gap-1">
                    <Flame className="w-3.5 h-3.5 text-brand-warning fill-brand-warning/30" />
                    Streak
                  </span>
                  <span className="font-bold text-brand-warning">
                    {analytics.gym_streak} days
                  </span>
                </div>
              </div>
            )}

            {/* Navigation links */}
            <nav className="flex flex-col gap-1.5">
              {navItems.map((item) => {
                const isActive = pathname === item.path;
                const Icon = item.icon;
                return (
                  <Link 
                    key={item.path} 
                    href={item.path}
                    className={`flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                      isActive 
                        ? "bg-brand-accent/15 text-brand-accent border-l-2 border-brand-accent shadow-sm" 
                        : "text-brand-muted hover:text-slate-200 hover:bg-brand-card/30"
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? "text-brand-accent" : "text-brand-muted"}`} />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Footer User Info */}
          <div className="flex items-center gap-3 p-2 rounded-xl border border-brand-border bg-brand-card/30">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center font-semibold text-white">
              {(user?.name || "U")[0].toUpperCase()}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-semibold truncate">{user?.name || "User"}</span>
              <span className="text-[10px] text-brand-success flex items-center gap-1 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-success animate-pulse" />
                Active Coach
              </span>
            </div>
          </div>
        </aside>

        {/* Content Container */}
        <main className="flex-1 h-full overflow-y-auto bg-brand-bg px-10 py-8 relative">
          <div className="max-w-6xl mx-auto flex flex-col min-h-full">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}

