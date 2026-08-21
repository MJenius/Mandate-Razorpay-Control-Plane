"use client";

import React, { useState } from "react";
import { GitBranch, ShieldCheck, AlertOctagon, User, Bot, ArrowRight, CornerDownRight, Zap, RefreshCw, XCircle } from "lucide-react";

export default function DelegationGraphPage() {
  const [treeData, setTreeData] = useState<any>({
    root_principal: { name: "Commerce Enterprise Admin", role: "ADMIN" },
    parent_mandate: {
      id: "mnd_root_99a",
      agent_name: "Primary Shopping Agent",
      agent_type: "SHOPPING",
      status: "ACTIVE",
      currency: "INR",
      max_amount_per_op: "₹25,000",
      aggregate_spend_limit: "₹1,00,000",
      current_spend: "₹19,500",
      delegated_child_budget: "₹15,000",
      remaining_available: "₹65,500",
      depth: 0,
    },
    child_mandates: [
      {
        id: "mnd_child_01",
        agent_name: "Procurement Sub-Agent (Electronics)",
        agent_type: "PROCUREMENT",
        status: "ACTIVE",
        currency: "INR",
        max_amount_per_op: "₹10,000",
        aggregate_spend_limit: "₹15,000",
        current_spend: "₹6,500",
        depth: 1,
        allowed_ops: ["CREATE_ORDER"],
      },
    ],
  });

  const [revoked, setRevoked] = useState(false);
  const [escalationAttempt, setEscalationAttempt] = useState<string | null>(null);

  const handleRevokeParent = () => {
    setRevoked(true);
    setTreeData((prev: any) => ({
      ...prev,
      parent_mandate: { ...prev.parent_mandate, status: "REVOKED" },
      child_mandates: prev.child_mandates.map((c: any) => ({ ...c, status: "REVOKED" })),
    }));
  };

  const handleSimulateEscalation = () => {
    setEscalationAttempt(
      "Escalation Blocked: Child agent requested ₹50,000 per-op limit (Parent ceiling is ₹25,000) → Deterministically Rejected by Mandate."
    );
    setTimeout(() => setEscalationAttempt(null), 6000);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Hierarchical Mandate Delegation Tree</h1>
          <p className="text-sm text-slate-400">
            Multi-agent financial authority delegation with mathematical non-escalation invariants and cascading revocation.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSimulateEscalation}
            className="flex items-center gap-1.5 rounded-lg bg-slate-800 border border-slate-700 px-3.5 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700 transition-colors shadow-sm"
          >
            <Zap className="h-3.5 w-3.5 text-amber-400" />
            Simulate Child Escalation Attempt
          </button>
          <button
            onClick={handleRevokeParent}
            disabled={revoked}
            className="flex items-center gap-1.5 rounded-lg bg-rose-600 px-3.5 py-2 text-xs font-medium text-white hover:bg-rose-500 transition-colors disabled:opacity-50 shadow-sm"
          >
            <AlertOctagon className="h-3.5 w-3.5" />
            {revoked ? "Parent & Children Revoked" : "Revoke Root Mandate (Cascade)"}
          </button>
        </div>
      </div>

      {/* Escalation Notification */}
      {escalationAttempt && (
        <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs flex items-center gap-2">
          <XCircle className="h-4 w-4 shrink-0 text-amber-400" />
          <span>{escalationAttempt}</span>
        </div>
      )}

      {/* Delegation DAG / Tree Visualization */}
      <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-6 space-y-6">
        <div className="flex items-center gap-2 border-b border-[#1f293d] pb-3">
          <GitBranch className="h-4 w-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Authority Delegation Chain (Depth: 0 → 1)</h2>
        </div>

        {/* Level 0: Root Principal */}
        <div className="flex items-start gap-4">
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center shrink-0">
            <User className="h-5 w-5 text-purple-400" />
          </div>
          <div className="flex-1 p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-white text-xs">{treeData.root_principal.name}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                ROOT PRINCIPAL
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Granted initial financial contract to Shopping Agent</p>
          </div>
        </div>

        {/* Level 1: Parent Mandate (Primary Shopping Agent) */}
        <div className="ml-6 pl-6 border-l-2 border-dashed border-blue-500/30 space-y-4">
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
              <Bot className="h-5 w-5 text-blue-400" />
            </div>
            <div className="flex-1 p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-white text-sm">{treeData.parent_mandate.agent_name}</span>
                  <span className="text-[11px] text-slate-400 block font-mono">Mandate #{treeData.parent_mandate.id} (Depth: 0)</span>
                </div>
                <span
                  className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                    treeData.parent_mandate.status === "ACTIVE"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  }`}
                >
                  {treeData.parent_mandate.status}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block font-sans">Per-Op Limit</span>
                  <span className="text-white font-semibold">{treeData.parent_mandate.max_amount_per_op}</span>
                </div>
                <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block font-sans">Total Aggregate Budget</span>
                  <span className="text-white font-semibold">{treeData.parent_mandate.aggregate_spend_limit}</span>
                </div>
                <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block font-sans">Delegated to Children</span>
                  <span className="text-indigo-400 font-semibold">{treeData.parent_mandate.delegated_child_budget}</span>
                </div>
                <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                  <span className="text-slate-400 text-[10px] block font-sans">Available Pool</span>
                  <span className="text-emerald-400 font-semibold">{treeData.parent_mandate.remaining_available}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Level 2: Child Mandate (Procurement Sub-Agent) */}
          <div className="ml-6 pl-6 border-l-2 border-dashed border-indigo-500/30 space-y-3">
            {treeData.child_mandates.map((child: any) => (
              <div key={child.id} className="flex items-start gap-4">
                <div className="h-9 w-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
                  <CornerDownRight className="h-4 w-4 text-indigo-400" />
                </div>
                <div className="flex-1 p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-white text-xs">{child.agent_name}</span>
                      <span className="text-[10px] text-slate-400 block font-mono">Delegated Mandate #{child.id} (Depth: 1)</span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        child.status === "ACTIVE"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}
                    >
                      {child.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-[11px] font-mono">
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800">
                      <span className="text-slate-400 text-[10px] block font-sans">Per-Op Bound</span>
                      <span className="text-white">{child.max_amount_per_op}</span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800">
                      <span className="text-slate-400 text-[10px] block font-sans">Sub-Budget Limit</span>
                      <span className="text-white">{child.aggregate_spend_limit}</span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800">
                      <span className="text-slate-400 text-[10px] block font-sans">Spent / Reserved</span>
                      <span className="text-amber-400">{child.current_spend}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Non-Escalation Verified: Strictly bounded by parent mandate authority</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
