"use client";

import React, { useState } from "react";
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
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Agents", href: "/agents", icon: Bot },
  { name: "Mandates", href: "/mandates", icon: ShieldCheck },
  { name: "Transactions", href: "/transactions", icon: CreditCard },
  { name: "Audit Log", href: "/audit", icon: FileText },
  { name: "Policies", href: "/policies", icon: Sliders },
  { name: "Evaluation", href: "/evaluation", icon: FlaskConical },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-[#090d16] text-slate-100">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-[#0d1322] border-r border-[#1e293b] p-4 transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-2 py-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                MANDATE
              </span>
              <span className="block text-[10px] uppercase font-mono tracking-widest text-blue-400">
                Razorpay Control Plane
              </span>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-slate-400 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation links */}
        <nav className="space-y-1.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-blue-400" : "text-slate-400"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Bottom environment badge */}
        <div className="absolute bottom-4 left-4 right-4 p-3 rounded-xl bg-slate-900/80 border border-slate-800">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-slate-400">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Test Mode
            </span>
            <span className="text-[10px] font-mono bg-slate-800 px-2 py-0.5 rounded text-slate-300">
              v0.1.0-alpha
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500 truncate">
            Gateway: Razorpay Sandbox
          </p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-16 items-center justify-between border-b border-[#1e293b] bg-[#0d1322]/80 px-6 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-slate-400 hover:text-white lg:hidden"
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <Activity className="h-3.5 w-3.5 text-emerald-400" />
              <span>Control Plane Status:</span>
              <span className="text-emerald-400 font-semibold">Active & Healthy</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-blue-400 transition-colors border border-slate-700/60 rounded-md px-2.5 py-1"
            >
              <span>API Specs (Swagger)</span>
              <ExternalLink className="h-3 w-3" />
            </a>
            <div className="h-8 w-8 rounded-full bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-xs font-bold text-blue-400">
              AD
            </div>
          </div>
        </header>

        {/* View container */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#090d16]">
          {children}
        </main>
      </div>
    </div>
  );
}
