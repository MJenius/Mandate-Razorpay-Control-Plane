"use client";

import React from "react";
import { RefreshCcw, ShieldCheck, Activity, Cpu, Sparkles } from "lucide-react";

interface PageHeaderProps {
  title: string;
  icon?: React.ComponentType<{ className?: string }>;
  description: string;
  architecturePhase?: string;
  isTestMode?: boolean;
  gatewayName?: string;
  policyStatus?: string;
  lastUpdated?: string | null;
  isLoading?: boolean;
  onRefresh?: () => void;
  actions?: React.ReactNode;
}

export default function PageHeader({
  title,
  icon: Icon = ShieldCheck,
  description,
  architecturePhase,
  isTestMode = true,
  gatewayName = "Razorpay Test Mode",
  policyStatus = "Deterministic Policy Engine Active",
  lastUpdated,
  isLoading = false,
  onRefresh,
  actions,
}: PageHeaderProps) {
  return (
    <div className="rounded-2xl bg-gradient-to-r from-[#111827] via-[#0f172a] to-[#111827] border border-[#1f293d] p-6 shadow-xl space-y-4">
      {/* Top Banner Row: Context Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1f293d] pb-3 text-[11px] font-mono">
        <div className="flex flex-wrap items-center gap-2">
          {/* Architecture Phase Badge */}
          {architecturePhase && (
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 font-sans font-semibold">
              <Cpu className="h-3 w-3 text-blue-400" />
              {architecturePhase}
            </span>
          )}

          {/* Test Mode / Gateway Badge */}
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/80">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {isTestMode ? "SANDBOX / TEST MODE" : "PRODUCTION"} · {gatewayName}
          </span>

          {/* Policy Engine Badge */}
          <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-950/60 text-indigo-300 border border-indigo-800/60">
            <ShieldCheck className="h-3 w-3 text-indigo-400" />
            {policyStatus}
          </span>
        </div>

        {/* Refresh & Last Updated */}
        <div className="flex items-center gap-2.5 text-slate-400 text-[10px]">
          {lastUpdated && <span>Refreshed: {lastUpdated}</span>}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors disabled:opacity-50"
              title="Refresh live data"
            >
              <RefreshCcw className={`h-3 w-3 ${isLoading ? "animate-spin text-blue-400" : ""}`} />
              <span>{isLoading ? "Syncing..." : "Refresh"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Title & Action Row */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="space-y-1.5 max-w-3xl">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-xl bg-blue-600/15 border border-blue-500/30 flex items-center justify-center text-blue-400 shadow-inner">
              <Icon className="h-5 w-5 text-blue-400" />
            </div>
            <span>{title}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans">{description}</p>
        </div>

        {/* Context Actions Slot */}
        {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
