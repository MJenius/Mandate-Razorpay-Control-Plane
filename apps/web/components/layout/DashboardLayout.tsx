"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  ShieldCheck,
  CreditCard,
  FileText,
  Sliders,
  FlaskConical,
  Activity,
  Menu,
  X,
  ExternalLink,
  ShoppingBag,
  GitBranch,
  Play,
  Wifi,
  WifiOff,
  AlertTriangle,
  RefreshCcw,
} from "lucide-react";
import { API_BASE_URL, api } from "@/lib/api";

const NAV_ITEMS = [
  { name: "Overview", href: "/", icon: LayoutDashboard, tag: "Summary" },
  { name: "AI Agents", href: "/agents", icon: Bot, tag: "Playground" },
  { name: "Mandates", href: "/mandates", icon: ShieldCheck, tag: "Contracts" },
  { name: "Policy Engine", href: "/policies", icon: Sliders, tag: "8 Rules" },
  { name: "Delegation Graph", href: "/delegation", icon: GitBranch, tag: "Hierarchy" },
  { name: "Commerce (MCP)", href: "/commerce", icon: ShoppingBag, tag: "Gateway" },
  { name: "Reliability & DLQ", href: "/operations", icon: Activity, tag: "Telemetry" },
  { name: "Transactions", href: "/transactions", icon: CreditCard, tag: "Ledger" },
  { name: "Audit Trail", href: "/audit", icon: FileText, tag: "Immutable" },
  { name: "Evaluation Lab", href: "/eval", icon: FlaskConical, tag: "Benchmark" },
  { name: "Competition Demo", href: "/demo", icon: Play, tag: "Showcase" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [backendHealth, setBackendHealth] = useState<"healthy" | "degraded" | "offline" | "checking">("checking");
  const [healthDetail, setHealthDetail] = useState<string>("");

  const checkHealth = async () => {
    try {
      const res = await api.getReadiness();
      if (res && res.status === "ready") {
        setBackendHealth("healthy");
        setHealthDetail("PostgreSQL + Redis Operational");
      } else if (res && res.status === "degraded") {
        setBackendHealth("degraded");
        setHealthDetail("Core DB Active (Redis Cache Degraded)");
      } else {
        setBackendHealth("offline");
        setHealthDetail("PostgreSQL Unreachable / Uninitialized");
      }
    } catch {
      setBackendHealth("offline");
      setHealthDetail(`Control Plane Unreachable (${API_BASE_URL})`);
    }
  };


  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-[#090d16] text-slate-100 font-sans">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-[#0c1220] border-r border-[#1e293b] p-4 flex flex-col justify-between transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="space-y-6">
          {/* Brand Header */}
          <div className="flex items-center justify-between px-2 py-2">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/25 group-hover:scale-105 transition-transform">
                <ShieldCheck className="h-5 w-5 text-white" />
              </div>
              <div>
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent block leading-none">
                  MANDATE
                </span>
                <span className="block text-[9px] uppercase font-mono tracking-widest text-blue-400 mt-1">
                  Razorpay Control Plane
                </span>
              </div>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-slate-400 hover:text-white p-1"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1 overflow-y-auto max-h-[calc(100vh-230px)] pr-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? "bg-blue-600/15 text-blue-300 border border-blue-500/30 shadow-sm shadow-blue-500/10 font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-blue-400" : "text-slate-400"}`} />
                    <span>{item.name}</span>
                  </div>
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.2 rounded ${
                      isActive
                        ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        : "bg-slate-900 text-slate-500"
                    }`}
                  >
                    {item.tag}
                  </span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom Sandbox Status Card */}
        <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/80 space-y-1.5 font-sans">
          <div className="flex items-center justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-slate-300 font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Razorpay Sandbox
            </span>
            <span className="text-[10px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
              Test Mode
            </span>
          </div>
          <p className="text-[10px] text-slate-500 leading-snug">
            Hermetic safety active. 0 live money moved.
          </p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top App Bar */}
        <header className="flex h-16 items-center justify-between border-b border-[#1e293b] bg-[#0c1220]/90 px-6 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-slate-400 hover:text-white lg:hidden p-1"
            >
              <Menu className="h-6 w-6" />
            </button>

            {/* Real Health Indicator */}
            <div className="flex items-center gap-2 text-xs">
              {backendHealth === "healthy" ? (
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium bg-emerald-950/50 border border-emerald-800/60 px-2.5 py-1 rounded-full text-[11px] font-mono">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Control Plane: Active & Healthy</span>
                </div>
              ) : backendHealth === "degraded" ? (
                <div className="flex items-center gap-1.5 text-amber-400 font-medium bg-amber-950/50 border border-amber-800/60 px-2.5 py-1 rounded-full text-[11px] font-mono">
                  <AlertTriangle className="h-3 w-3" />
                  <span>Control Plane: Degraded</span>
                </div>
              ) : backendHealth === "offline" ? (
                <div className="flex items-center gap-2 text-rose-400 font-medium bg-rose-950/60 border border-rose-800 px-3 py-1 rounded-full text-[11px] font-mono">
                  <WifiOff className="h-3.5 w-3.5 animate-pulse" />
                  <span>Backend Offline ({API_BASE_URL})</span>
                  <button
                    onClick={checkHealth}
                    className="underline text-white ml-1 hover:text-rose-200"
                    title="Retry connection"
                  >
                    Retry
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-mono">
                  <RefreshCcw className="h-3 w-3 animate-spin" />
                  <span>Checking Backend...</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-blue-400 transition-colors bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-lg px-3 py-1.5 font-mono shadow-sm"
            >
              <span>Swagger REST Specs</span>
              <ExternalLink className="h-3 w-3 text-slate-500" />
            </a>

            <div className="h-8 px-2.5 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-xs font-mono font-bold text-blue-300">
              PRN_ADMIN
            </div>
          </div>
        </header>

        {/* Dynamic Page Content Stream */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#090d16]">
          {children}
        </main>
      </div>
    </div>
  );
}
