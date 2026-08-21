import React from "react";
import { Bot, ShieldCheck, ArrowUpRight, Lock, CheckCircle2, History } from "lucide-react";

export default function OverviewPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header section */}
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-white">System Overview</h1>
        <p className="text-sm text-slate-400">
          Real-time metrics, active mandates, and authorization telemetry for delegated AI financial operations.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Active Agents</span>
            <Bot className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">3</span>
            <span className="text-xs text-emerald-400 font-medium">All Healthy</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Autonomous callers with active keys</p>
        </div>

        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Active Mandates</span>
            <ShieldCheck className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">5</span>
            <span className="text-xs text-blue-400 font-medium">100% Policy Bound</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Delegated budgets in effect</p>
        </div>

        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Total Allocated Budget</span>
            <Lock className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">₹ 2,50,000</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Aggregated maximum exposure limit</p>
        </div>

        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">Policy Checks Passed</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-400">99.8%</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Zero unauthenticated attempts</p>
        </div>
      </div>

      {/* Grid Layout for details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Agents Column */}
        <div className="lg:col-span-2 rounded-xl bg-[#111827] border border-[#1f293d] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white">Managed AI Agents</h2>
            <span className="text-xs text-blue-400 font-mono">Phase 0 Stubs</span>
          </div>
          <div className="divide-y divide-[#1f293d]">
            {[
              { id: "ag_procure_01", name: "Procurement Agent", role: "Vendor settlements & invoice payments", cap: "₹ 50,000 / op", status: "ACTIVE" },
              { id: "ag_support_refund", name: "Customer Support Agent", role: "Instant refunds under strict thresholds", cap: "₹ 2,000 / op", status: "ACTIVE" },
              { id: "ag_subscription_bot", name: "Billing Reconciliation Agent", role: "Payment link creation & verification", cap: "₹ 10,000 / op", status: "ACTIVE" },
            ].map((agent) => (
              <div key={agent.id} className="py-3.5 flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{agent.name}</span>
                    <span className="text-[10px] font-mono bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/20">
                      {agent.id}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{agent.role}</p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-slate-300 block">{agent.cap}</span>
                  <span className="text-[10px] text-emerald-400 font-medium">● {agent.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Architecture Status */}
        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <History className="h-4 w-4 text-blue-400" />
            Control Plane Architecture
          </h2>
          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
              <div className="flex justify-between items-center text-slate-300 font-medium">
                <span>FastAPI Control Plane</span>
                <span className="text-emerald-400">Healthy</span>
              </div>
              <p className="text-slate-500 text-[11px]">Enforces idempotency, authentication & audit logging.</p>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
              <div className="flex justify-between items-center text-slate-300 font-medium">
                <span>Policy Evaluation Engine</span>
                <span className="text-emerald-400">Synchronous Gate</span>
              </div>
              <p className="text-slate-500 text-[11px]">Evaluates spend boundaries and operations before gateway execution.</p>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
              <div className="flex justify-between items-center text-slate-300 font-medium">
                <span>Razorpay Gateway Client</span>
                <span className="text-blue-400">Test Mode</span>
              </div>
              <p className="text-slate-500 text-[11px]">Orders, Payments, Refunds, Payment Links & Webhooks abstraction.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
