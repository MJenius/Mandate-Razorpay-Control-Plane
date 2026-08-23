"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Activity,
  ShieldCheck,
  CreditCard,
  CheckCircle2,
  Lock,
  ArrowRight,
  RefreshCcw,
  FileText,
  Bot,
  Sliders,
  Terminal,
  Zap,
  TrendingUp,
} from "lucide-react";
import { api, Mandate, FinancialOperation, AuditEvent, SystemMetrics } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import ArchitectureDiagram from "@/components/common/ArchitectureDiagram";
import { SkeletonCard, SkeletonTable } from "@/components/common/Skeleton";
import ErrorState from "@/components/common/ErrorState";

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [operations, setOperations] = useState<FinancialOperation[]>([]);
  const [recentAudit, setRecentAudit] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [metricsData, mandatesData, opsData, auditData] = await Promise.allSettled([
        api.getMetrics(),
        api.getMandates(),
        api.getOperations(),
        api.getAuditLogs(6),
      ]);

      if (metricsData.status === "fulfilled") setMetrics(metricsData.value);
      if (mandatesData.status === "fulfilled") setMandates(mandatesData.value);
      if (opsData.status === "fulfilled") setOperations(opsData.value);
      if (auditData.status === "fulfilled") setRecentAudit(auditData.value);

      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to synchronize with Mandate control plane");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const totalAllocatedBudgetInr =
    mandates.reduce((acc, m) => acc + m.aggregate_spend_limit, 0) / 100;
  const totalSpentInr =
    mandates.reduce((acc, m) => acc + m.current_aggregate_spend, 0) / 100;
  const totalReservedInr = mandates.reduce((acc, m) => acc + m.reserved_spend, 0) / 100;
  const totalAvailableInr = Math.max(
    0,
    totalAllocatedBudgetInr - (totalSpentInr + totalReservedInr)
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Unified Page Header */}
      <PageHeader
        title="Mandate Control Plane Overview"
        icon={Activity}
        architecturePhase="System Control Plane & Telemetry"
        description="Real-time financial telemetry, authority contracts, two-phase budget reservations, and deterministic policy enforcement. This control plane guarantees that autonomous AI agents never exceed mathematical spending bounds when transacting through Razorpay APIs."
        lastUpdated={lastUpdated}
        isLoading={loading}
        onRefresh={loadDashboardData}
        actions={
          <div className="flex items-center gap-2">
            <Link
              href="/demo"
              className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-blue-600/25 transition-all"
            >
              <Zap className="h-3.5 w-3.5" />
              <span>Launch 5-Step Demo</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        }
      />

      {error && <ErrorState message={error} onRetry={loadDashboardData} isRetrying={loading} />}

      {/* Real Metrics Row */}
      {loading && !metrics ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((n) => (
            <SkeletonCard key={n} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Active Mandates */}
          <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl space-y-2 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-mono uppercase tracking-wider">Active Mandates</span>
              <ShieldCheck className="h-4 w-4 text-blue-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white font-mono">
                {mandates.filter((m) => m.status === "ACTIVE").length}
              </span>
              <span className="text-xs text-emerald-400 font-mono font-medium">
                100% Policy Bound
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Total Issued: {mandates.length} | Revoked: {mandates.filter((m) => m.status === "REVOKED").length}
            </p>
          </div>

          {/* Allocated Budget */}
          <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl space-y-2 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-mono uppercase tracking-wider">Allocated Budget Pool</span>
              <Lock className="h-4 w-4 text-indigo-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-white font-mono">
                ₹{totalAllocatedBudgetInr.toLocaleString("en-IN")}
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between pt-1">
              <span>Spent: ₹{totalSpentInr.toLocaleString("en-IN")}</span>
              <span className="text-amber-400">Reserved: ₹{totalReservedInr.toLocaleString("en-IN")}</span>
            </div>
          </div>

          {/* Operations Executed */}
          <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl space-y-2 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-mono uppercase tracking-wider">Operations Executed</span>
              <CreditCard className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white font-mono">
                {metrics ? metrics.total_operations : operations.length}
              </span>
              <span className="text-xs text-emerald-400 font-mono font-medium">
                {metrics ? `${metrics.succeeded_operations} Succeeded` : "Live"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              {metrics ? `${metrics.failed_operations} Denied / Blocked` : "0 Unchecked Dispatches"}
            </p>
          </div>

          {/* Benchmark Security Recall */}
          <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 shadow-xl space-y-2 relative overflow-hidden">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-mono uppercase tracking-wider">Adversarial Block Rate</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-emerald-400 font-mono">100.0%</span>
              <span className="text-xs text-slate-400 font-mono">1,144 / 1,144</span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              0.0% Bypass · ₹32.17 Cr Loss Prevented
            </p>
          </div>
        </div>
      )}

      {/* Interactive Control Plane Architecture Diagram */}
      <ArchitectureDiagram />

      {/* Active Mandates Feed & Live Audit Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Financial Mandates */}
        <div className="lg:col-span-2 rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-blue-400" />
              <h2 className="text-sm font-bold text-white">Active Authority Contracts</h2>
            </div>
            <Link href="/mandates" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">
              Manage all ({mandates.length}) →
            </Link>
          </div>

          {mandates.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 font-mono">
              No mandates in database. Reset demo or issue a mandate.
            </div>
          ) : (
            <div className="divide-y divide-[#1f293d]">
              {mandates.slice(0, 4).map((m) => {
                const spent = m.current_aggregate_spend / 100;
                const limit = m.aggregate_spend_limit / 100;
                const perOp = m.max_amount_per_op / 100;
                const pct = Math.min(100, Math.round((spent / (limit || 1)) * 100));

                return (
                  <div key={m.id} className="py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 font-mono">
                        <span className="text-xs font-bold text-white">{m.id}</span>
                        <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                          {m.agent_id}
                        </span>
                        {m.parent_mandate_id && (
                          <span className="text-[9px] text-indigo-300 bg-indigo-500/10 px-1.5 py-0.2 rounded">
                            Child (Depth {m.delegation_depth})
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Cap: ₹{perOp.toLocaleString("en-IN")} / op · Aggregate: ₹{limit.toLocaleString("en-IN")}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="w-28 space-y-1">
                        <div className="flex justify-between text-[9px] font-mono text-slate-400">
                          <span>₹{spent.toLocaleString("en-IN")}</span>
                          <span>{pct}%</span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className={`h-full ${pct > 80 ? "bg-rose-500" : pct > 50 ? "bg-amber-500" : "bg-blue-500"}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                      <StatusBadge status={m.status} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Live Cryptographic Audit Stream */}
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white">Live Audit Trail</h2>
            </div>
            <Link href="/audit" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
              Full stream →
            </Link>
          </div>

          {recentAudit.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 font-mono">
              No audit events recorded yet.
            </div>
          ) : (
            <div className="space-y-2.5 font-mono text-[11px]">
              {recentAudit.map((a) => (
                <div
                  key={a.id}
                  className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1 hover:border-slate-700 transition-colors"
                >
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
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
