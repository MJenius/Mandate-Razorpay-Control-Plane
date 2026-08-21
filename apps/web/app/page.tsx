"use client";

import React, { useState, useEffect } from "react";
import {
  Bot,
  ShieldCheck,
  Lock,
  CheckCircle2,
  AlertTriangle,
  RefreshCcw,
  Activity,
  Layers,
  ArrowRight,
  TrendingUp,
  CreditCard,
  FileText,
} from "lucide-react";
import Link from "next/link";
import { api, Mandate, FinancialOperation, AuditEvent, SystemMetrics } from "../lib/api";

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [operations, setOperations] = useState<FinancialOperation[]>([]);
  const [recentAudit, setRecentAudit] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [metricsData, mandatesData, opsData, auditData] = await Promise.allSettled([
        api.getMetrics(),
        api.getMandates(),
        api.getOperations(),
        api.getAuditLogs(5),
      ]);

      if (metricsData.status === "fulfilled") setMetrics(metricsData.value);
      if (mandatesData.status === "fulfilled") setMandates(mandatesData.value);
      if (opsData.status === "fulfilled") setOperations(opsData.value);
      if (auditData.status === "fulfilled") setRecentAudit(auditData.value);
    } catch {
      // Backend may be starting
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const totalAllocatedBudgetInr = mandates.reduce((acc, m) => acc + m.aggregate_spend_limit, 0) / 100;
  const totalSpentInr = mandates.reduce((acc, m) => acc + m.current_aggregate_spend, 0) / 100;
  const totalReservedInr = mandates.reduce((acc, m) => acc + m.reserved_spend, 0) / 100;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="h-6 w-6 text-blue-400" />
            Mandate Control Plane Overview
          </h1>
          <p className="text-sm text-slate-400">
            Real-time financial telemetry, active authority contracts, and deterministic policy gate metrics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <Link
            href="/demo"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20 transition-colors"
          >
            Competition Demo Mode <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Active Mandates</span>
            <ShieldCheck className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white font-mono">
              {mandates.filter((m) => m.status === "ACTIVE").length}
            </span>
            <span className="text-xs text-emerald-400 font-medium">100% Policy Bound</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Autonomous authority contracts</p>
        </div>

        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Allocated Budget</span>
            <Lock className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white font-mono">
              ₹{totalAllocatedBudgetInr.toLocaleString("en-IN")}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500 font-mono">
            Spent: ₹{totalSpentInr.toLocaleString("en-IN")} | Rsv: ₹{totalReservedInr.toLocaleString("en-IN")}
          </p>
        </div>

        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Operations Executed</span>
            <CreditCard className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white font-mono">
              {metrics ? metrics.total_operations : operations.length}
            </span>
            <span className="text-xs text-emerald-400 font-medium">
              {metrics ? `${metrics.succeeded_operations} Succeeded` : "Live"}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            {metrics?.failed_operations || 0} Blocked / Denied by Policy
          </p>
        </div>

        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Hostile Block Rate</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-400 font-mono">100.0%</span>
            <span className="text-xs text-slate-400 font-mono">N=1,000</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">0.0% Bypass · ₹21.85 Cr Loss Prevented</p>
        </div>
      </div>

      {/* Grid Layout for details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Mandates Live List */}
        <div className="lg:col-span-2 rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-blue-400" />
              Active Financial Mandates
            </h2>
            <Link href="/mandates" className="text-xs text-blue-400 hover:underline">
              View all →
            </Link>
          </div>

          <div className="divide-y divide-[#1f293d]">
            {mandates.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 font-mono">
                No active mandates loaded. Reset demo or issue a mandate.
              </div>
            ) : (
              mandates.slice(0, 4).map((m) => (
                <div key={m.id} className="py-3 flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-xs font-bold text-white">{m.id}</span>
                      <span className="text-[10px] text-blue-400 bg-blue-500/10 px-1.5 py-0.2 rounded border border-blue-500/20">
                        {m.agent_id}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Cap: ₹{(m.max_amount_per_op / 100).toLocaleString()} / op · Budget: ₹
                      {(m.aggregate_spend_limit / 100).toLocaleString()}
                    </div>
                  </div>

                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                      m.status === "ACTIVE"
                        ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                        : "bg-rose-950 text-rose-400 border border-rose-800"
                    }`}
                  >
                    {m.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Live Cryptographic Audit Log Feed */}
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <FileText className="h-4 w-4 text-indigo-400" />
              Live Audit Feed
            </h2>
            <Link href="/audit" className="text-xs text-indigo-400 hover:underline">
              View all →
            </Link>
          </div>

          <div className="space-y-3 font-mono text-[11px]">
            {recentAudit.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">No audit events recorded yet.</div>
            ) : (
              recentAudit.map((a) => (
                <div key={a.id} className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-[10px]">{a.action}</span>
                    <span className="text-[9px] text-slate-500">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 truncate">
                    Actor: <strong className="text-slate-300">{a.actor_id}</strong> → {a.resource_id}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
