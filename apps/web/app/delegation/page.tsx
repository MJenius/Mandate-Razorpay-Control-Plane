"use client";

import React, { useState, useEffect } from "react";
import {
  GitBranch,
  ShieldCheck,
  User,
  Bot,
  CornerDownRight,
  AlertOctagon,
  Plus,
  Zap,
  RefreshCcw,
  CheckCircle2,
  XCircle,
  Lock,
  Layers,
  ArrowRight,
} from "lucide-react";
import { api, DelegationNode, Mandate, Agent } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { useToast } from "@/components/common/Toast";
import { SkeletonCard } from "@/components/common/Skeleton";
import EmptyState from "@/components/common/EmptyState";
import ErrorState from "@/components/common/ErrorState";

export default function DelegationGraphPage() {
  const toast = useToast();
  const [treeNodes, setTreeNodes] = useState<DelegationNode[]>([]);
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Delegation Modal state
  const [showDelegateModal, setShowDelegateModal] = useState(false);
  const [selectedParentId, setSelectedParentId] = useState<string>("");
  const [targetChildAgentId, setTargetChildAgentId] = useState<string>("agt_procurement_child_01");
  const [delegatePerOpInr, setDelegatePerOpInr] = useState<number>(10000);
  const [delegateAggregateInr, setDelegateAggregateInr] = useState<number>(15000);
  const [delegateOps, setDelegateOps] = useState<string[]>(["CREATE_ORDER"]);

  // Confirm Dialog State
  const [confirmState, setConfirmState] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    action: () => Promise<void>;
  }>({
    isOpen: false,
    title: "",
    description: "",
    action: async () => {},
  });

  const loadTreeData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [treeData, mandatesData, agentsData] = await Promise.all([
        api.getDelegationTree(),
        api.getMandates(),
        api.getAgents(),
      ]);

      setTreeNodes(treeData);
      setMandates(mandatesData);
      setAgents(agentsData);

      const activeParent = mandatesData.find((m) => !m.parent_mandate_id && m.status === "ACTIVE");
      if (activeParent) setSelectedParentId(activeParent.id);

      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load delegation graph from API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTreeData();
  }, []);

  const handleCascadeRevoke = (mandateId: string) => {
    setConfirmState({
      isOpen: true,
      title: `Cascade Revoke Mandate Tree (${mandateId})?`,
      description: `Revoking this parent mandate will immediately cascade permanent revocation down the entire hierarchy. All delegated child sub-mandates will be permanently deactivated.`,
      action: async () => {
        setActionLoading(mandateId);
        try {
          await api.revokeMandate(mandateId, "Administrative cascade revocation via Delegation Graph");
          toast.success("Mandate Tree Revoked", `Parent ${mandateId} and all child authority revoked.`);
          await loadTreeData();
        } catch (err: unknown) {
          toast.error("Revocation Failed", err instanceof Error ? err.message : String(err));
        } finally {
          setActionLoading(null);
        }
      },
    });
  };

  const handleSimulateEscalationAttack = async () => {
    setActionLoading("escalate_test");
    try {
      const parent = mandates.find((m) => m.id === selectedParentId) || mandates[0];
      if (!parent) {
        toast.error("No Parent Mandate", "Please seed the demo dataset first.");
        return;
      }

      // Deliberately request per-op ceiling exceeding parent limit
      const illegalPerOpPaise = parent.max_amount_per_op * 2;
      const illegalAggregatePaise = parent.aggregate_spend_limit * 2;

      await api.delegateChildMandate(parent.id, {
        target_agent_id: "agt_procurement_child_01",
        currency: "INR",
        max_amount_per_op: illegalPerOpPaise,
        aggregate_spend_limit: illegalAggregatePaise,
        allowed_operations: ["CREATE_ORDER", "CREATE_REFUND"],
        valid_until: new Date(Date.now() + 60 * 24 * 60 * 60 * 1000).toISOString(),
      });

      toast.error("Security Failure", "Escalation request was not blocked!");
    } catch (err: unknown) {
      toast.success(
        "Escalation Blocked by Invariant",
        err instanceof Error ? err.message : "Privilege escalation deterministically rejected by Mandate API."
      );
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelegateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedParentId) return;

    setActionLoading("delegate");
    try {
      await api.delegateChildMandate(selectedParentId, {
        target_agent_id: targetChildAgentId,
        currency: "INR",
        max_amount_per_op: Math.round(delegatePerOpInr * 100),
        aggregate_spend_limit: Math.round(delegateAggregateInr * 100),
        allowed_operations: delegateOps,
        valid_until: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
      });

      toast.success(
        "Sub-Mandate Delegated",
        `Delegated ₹${delegateAggregateInr.toLocaleString("en-IN")} authority to ${targetChildAgentId}`
      );
      setShowDelegateModal(false);
      await loadTreeData();
    } catch (err: unknown) {
      toast.error("Delegation Failed", err instanceof Error ? err.message : String(err));
    } finally {
      setActionLoading(null);
    }
  };

  // Group root vs child nodes
  const rootNodes = treeNodes.filter((n) => n.parent_id === null || n.depth === 0);
  const childNodes = treeNodes.filter((n) => n.parent_id !== null && n.depth > 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="Hierarchical Mandate Delegation Graph"
        icon={GitBranch}
        architecturePhase="Stage 2: Multi-Agent Authority Hierarchy"
        description="Autonomous multi-agent architectures require hierarchical authority delegation (e.g. Primary Shopping Agent delegating a sub-budget to a Procurement Sub-Agent). Mandate enforces strict mathematical non-escalation invariants and cascading revocation across the entire DAG."
        lastUpdated={lastUpdated}
        isLoading={loading}
        onRefresh={loadTreeData}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleSimulateEscalationAttack}
              disabled={actionLoading !== null}
              className="inline-flex items-center gap-1.5 rounded-xl bg-amber-950/40 hover:bg-amber-900/60 border border-amber-800/60 text-amber-300 px-3.5 py-2 text-xs font-semibold transition-all disabled:opacity-50"
            >
              <Zap className="h-3.5 w-3.5 text-amber-400" />
              <span>Test Non-Escalation Invariant</span>
            </button>
            <button
              onClick={() => setShowDelegateModal(true)}
              disabled={rootNodes.length === 0}
              className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-blue-600/25 transition-all disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              <span>Delegate Sub-Mandate</span>
            </button>
          </div>
        }
      />

      {error && <ErrorState message={error} onRetry={loadTreeData} isRetrying={loading} />}

      {/* Non-Escalation Invariants Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-white">
            <ShieldCheck className="h-4 w-4 text-blue-400" />
            <span>Budget Containment</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
            A child mandate&apos;s aggregate limit cannot exceed the parent&apos;s unallocated available pool. Funds are reserved atomically from parent upon delegation.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-white">
            <Lock className="h-4 w-4 text-indigo-400" />
            <span>Per-Op Ceiling Invariant</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
            Child single-operation limits must be ≤ parent per-op limits. Operation whitelists must be strict subsets of parent permissions.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-white">
            <AlertOctagon className="h-4 w-4 text-rose-400" />
            <span>Cascading Revocation</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
            Suspending or revoking any ancestor parent mandate instantly cascades down the DAG, permanently disabling all child transaction authority.
          </p>
        </div>
      </div>

      {/* Hierarchical DAG Authority Tree */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-6 shadow-xl">
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-blue-400" />
            <h2 className="text-sm font-bold text-white">Live Authority Graph (DAG)</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {treeNodes.length} Nodes in Database
          </span>
        </div>

        {loading && treeNodes.length === 0 ? (
          <SkeletonCard />
        ) : treeNodes.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title="Delegation Graph Empty"
            description="No authority tree found. Run Demo Reset or issue a root mandate to view the hierarchy."
            actionLabel="Reset Demo Dataset"
            onAction={async () => {
              await api.resetDemo();
              await loadTreeData();
            }}
          />
        ) : (
          <div className="space-y-6">
            {/* Root Principal Node */}
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0 shadow-inner">
                <User className="h-5 w-5" />
              </div>
              <div className="flex-1 p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-xs font-bold text-white">Alpha Commerce Enterprise</span>
                    <span className="text-[10px] text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20 font-bold">
                      ROOT PRINCIPAL OWNER
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Principal ID: prn_alpha_corp_01 · Issues root financial authority contracts
                  </p>
                </div>
              </div>
            </div>

            {/* Depth 0: Root Parent Mandates */}
            <div className="ml-5 pl-6 border-l-2 border-dashed border-blue-500/30 space-y-6">
              {rootNodes.map((parent) => {
                const parentChildren = childNodes.filter((c) => c.parent_id === parent.id);
                const spentInr = parent.current_spend / 100;
                const reservedInr = parent.reserved_spend / 100;
                const limitInr = parent.aggregate_spend_limit / 100;
                const delegatedInr = parent.delegated_budget / 100;
                const availableInr = Math.max(0, limitInr - (spentInr + reservedInr + delegatedInr));

                return (
                  <div key={parent.id} className="space-y-4">
                    <div className="flex items-start gap-4">
                      <div className="h-10 w-10 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 shadow-inner">
                        <Bot className="h-5 w-5" />
                      </div>

                      <div className="flex-1 p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 shadow-sm">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2 font-mono">
                              <span className="font-bold text-white text-sm">{parent.agent_name}</span>
                              <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                                Mandate #{parent.id} (Depth: {parent.depth})
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-400 font-mono">
                              Agent ID: {parent.agent_id} · Currency: {parent.currency}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <StatusBadge status={parent.status} />
                            {parent.status === "ACTIVE" && (
                              <button
                                onClick={() => handleCascadeRevoke(parent.id)}
                                disabled={actionLoading === parent.id}
                                className="px-2.5 py-1 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 text-[10px] font-mono transition-colors"
                              >
                                Cascade Revoke
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Limits Grid */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-0.5">
                            <span className="text-[10px] text-slate-400 block font-sans">Per-Op Cap</span>
                            <strong className="text-white font-bold">₹{(parent.max_amount_per_op / 100).toLocaleString("en-IN")}</strong>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-0.5">
                            <span className="text-[10px] text-slate-400 block font-sans">Aggregate Budget</span>
                            <strong className="text-white font-bold">₹{limitInr.toLocaleString("en-IN")}</strong>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-0.5">
                            <span className="text-[10px] text-slate-400 block font-sans">Delegated to Children</span>
                            <strong className="text-indigo-400 font-bold">₹{delegatedInr.toLocaleString("en-IN")}</strong>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-0.5">
                            <span className="text-[10px] text-slate-400 block font-sans">Available Pool</span>
                            <strong className="text-emerald-400 font-bold">₹{availableInr.toLocaleString("en-IN")}</strong>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Depth 1: Delegated Child Sub-Mandates */}
                    <div className="ml-5 pl-6 border-l-2 border-dashed border-indigo-500/30 space-y-3">
                      {parentChildren.length === 0 ? (
                        <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/60 text-slate-500 text-xs font-mono flex items-center justify-between">
                          <span>No child sub-mandates delegated yet under this parent.</span>
                          <button
                            onClick={() => {
                              setSelectedParentId(parent.id);
                              setShowDelegateModal(true);
                            }}
                            className="text-blue-400 hover:underline"
                          >
                            + Delegate Sub-Mandate
                          </button>
                        </div>
                      ) : (
                        parentChildren.map((child) => {
                          const childSpent = child.current_spend / 100;
                          const childLimit = child.aggregate_spend_limit / 100;
                          const childPerOp = child.max_amount_per_op / 100;

                          return (
                            <div key={child.id} className="flex items-start gap-4">
                              <div className="h-9 w-9 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 shadow-inner">
                                <CornerDownRight className="h-4 w-4" />
                              </div>

                              <div className="flex-1 p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
                                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                                  <div>
                                    <div className="flex items-center gap-2 font-mono">
                                      <span className="font-bold text-white text-xs">{child.agent_name}</span>
                                      <span className="text-[10px] text-indigo-300 bg-indigo-500/10 px-2 py-0.2 rounded border border-indigo-500/20">
                                        Sub-Mandate #{child.id} (Depth: {child.depth})
                                      </span>
                                    </div>
                                    <span className="text-[10px] text-slate-400 font-mono">
                                      Agent ID: {child.agent_id} · Bound by Parent #{parent.id}
                                    </span>
                                  </div>
                                  <StatusBadge status={child.status} />
                                </div>

                                <div className="grid grid-cols-3 gap-2 text-[11px] font-mono">
                                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                                    <span className="text-[10px] text-slate-400 block font-sans">Per-Op Bound</span>
                                    <span className="text-white font-bold">₹{childPerOp.toLocaleString("en-IN")}</span>
                                  </div>
                                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                                    <span className="text-[10px] text-slate-400 block font-sans">Sub-Budget Limit</span>
                                    <span className="text-emerald-400 font-bold">₹{childLimit.toLocaleString("en-IN")}</span>
                                  </div>
                                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                                    <span className="text-[10px] text-slate-400 block font-sans">Committed Spend</span>
                                    <span className="text-amber-400 font-bold">₹{childSpent.toLocaleString("en-IN")}</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmState.isOpen}
        title={confirmState.title}
        description={confirmState.description}
        confirmLabel="Cascade Revoke"
        isDestructive={true}
        isLoading={actionLoading !== null}
        onConfirm={async () => {
          await confirmState.action();
          setConfirmState((prev) => ({ ...prev, isOpen: false }));
        }}
        onCancel={() => setConfirmState((prev) => ({ ...prev, isOpen: false }))}
      />

      {/* Delegate Sub-Mandate Modal */}
      {showDelegateModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <h2 className="text-base font-bold text-white">Delegate Bounded Sub-Mandate</h2>
              <button
                onClick={() => setShowDelegateModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleDelegateSubmit} className="space-y-4 text-xs font-sans">
              <div>
                <label className="text-slate-300 font-medium block mb-1">Parent Mandate Authority</label>
                <select
                  value={selectedParentId}
                  onChange={(e) => {
                    const nextParentId = e.target.value;
                    setSelectedParentId(nextParentId);
                    const p = mandates.find((m) => m.id === nextParentId);
                    if (p) {
                      const maxOp = p.max_amount_per_op / 100;
                      const avail = Math.max(0, (p.aggregate_spend_limit - p.current_aggregate_spend - p.delegated_child_budget_allocated) / 100);
                      setDelegatePerOpInr(Math.min(delegatePerOpInr, maxOp));
                      setDelegateAggregateInr(Math.min(delegateAggregateInr, avail > 0 ? avail : maxOp));
                      if (p.allowed_operations?.length) {
                        setDelegateOps([p.allowed_operations[0]]);
                      }
                    }
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white font-mono"
                  required
                >
                  {rootNodes.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.id} — {p.agent_name} (Cap: ₹{(p.max_amount_per_op / 100).toLocaleString("en-IN")})
                    </option>
                  ))}
                </select>
                {(() => {
                  const parent = mandates.find((m) => m.id === selectedParentId);
                  if (!parent) return null;
                  const maxOp = parent.max_amount_per_op / 100;
                  const avail = Math.max(0, (parent.aggregate_spend_limit - parent.current_aggregate_spend - parent.delegated_child_budget_allocated) / 100);
                  return (
                    <div className="mt-1.5 p-2 rounded-lg bg-slate-900/80 border border-slate-800 text-[10px] text-slate-400 font-mono flex items-center justify-between">
                      <span>Parent Per-Op Cap: <strong className="text-white">₹{maxOp.toLocaleString("en-IN")}</strong></span>
                      <span>Available Sub-Pool: <strong className="text-emerald-400">₹{avail.toLocaleString("en-IN")}</strong></span>
                    </div>
                  );
                })()}
              </div>

              <div>
                <label className="text-slate-300 font-medium block mb-1">Target Child Sub-Agent</label>
                <select
                  value={targetChildAgentId}
                  onChange={(e) => setTargetChildAgentId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white font-mono"
                  required
                >
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  {(() => {
                    const parent = mandates.find((m) => m.id === selectedParentId);
                    const parentMax = parent ? parent.max_amount_per_op / 100 : 25000;
                    const isExceeded = delegatePerOpInr > parentMax;
                    return (
                      <>
                        <label className="text-slate-300 font-medium block mb-1">
                          Per-Op Ceiling (₹ INR)
                        </label>
                        <input
                          type="number"
                          value={delegatePerOpInr}
                          onChange={(e) => setDelegatePerOpInr(Number(e.target.value))}
                          max={parentMax}
                          min={1}
                          className={`w-full bg-slate-950 border rounded-xl px-3.5 py-2.5 text-white font-mono ${
                            isExceeded ? "border-rose-500 text-rose-300" : "border-slate-800"
                          }`}
                          required
                        />
                        <span className={`text-[10px] mt-1 block font-mono ${isExceeded ? "text-rose-400 font-bold" : "text-slate-500"}`}>
                          {isExceeded
                            ? `⚠️ Exceeds parent cap (₹${parentMax.toLocaleString()})`
                            : `Must be ≤ parent cap (₹${parentMax.toLocaleString()})`}
                        </span>
                      </>
                    );
                  })()}
                </div>

                <div>
                  {(() => {
                    const parent = mandates.find((m) => m.id === selectedParentId);
                    const parentPool = parent
                      ? Math.max(0, (parent.aggregate_spend_limit - parent.current_aggregate_spend - parent.delegated_child_budget_allocated) / 100)
                      : 100000;
                    const isExceeded = delegateAggregateInr > (parentPool > 0 ? parentPool : 100000);
                    return (
                      <>
                        <label className="text-slate-300 font-medium block mb-1">
                          Sub-Budget Limit (₹ INR)
                        </label>
                        <input
                          type="number"
                          value={delegateAggregateInr}
                          onChange={(e) => setDelegateAggregateInr(Number(e.target.value))}
                          max={parentPool > 0 ? parentPool : undefined}
                          min={1}
                          className={`w-full bg-slate-950 border rounded-xl px-3.5 py-2.5 text-white font-mono ${
                            isExceeded ? "border-rose-500 text-rose-300" : "border-slate-800"
                          }`}
                          required
                        />
                        <span className={`text-[10px] mt-1 block font-mono ${isExceeded ? "text-rose-400 font-bold" : "text-slate-500"}`}>
                          {isExceeded
                            ? `⚠️ Exceeds available pool (₹${parentPool.toLocaleString()})`
                            : `Must be ≤ pool (₹${parentPool.toLocaleString()})`}
                        </span>
                      </>
                    );
                  })()}
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-medium block mb-1.5">Authorized Operations Whitelist</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    "CREATE_ORDER",
                    "CREATE_PAYMENT_LINK",
                    "CREATE_REFUND",
                  ].map((op) => {
                    const parent = mandates.find((m) => m.id === selectedParentId);
                    const isAllowedByParent = !parent || !parent.allowed_operations || parent.allowed_operations.includes(op);
                    const isSelected = delegateOps.includes(op);

                    return (
                      <button
                        type="button"
                        key={op}
                        disabled={!isAllowedByParent}
                        onClick={() => {
                          if (isSelected) {
                            setDelegateOps(delegateOps.filter((o) => o !== op));
                          } else {
                            setDelegateOps([...delegateOps, op]);
                          }
                        }}
                        className={`p-2.5 rounded-xl border text-left text-[11px] font-mono transition-all ${
                          !isAllowedByParent
                            ? "opacity-40 bg-slate-950 border-slate-900 text-slate-600 cursor-not-allowed"
                            : isSelected
                            ? "bg-blue-600/15 border-blue-500 text-blue-300 font-bold"
                            : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        {isSelected ? "✓ " : "+ "}
                        {op}
                        {!isAllowedByParent && " (Not in parent)"}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-[#1f293d]">
                <button
                  type="button"
                  onClick={() => setShowDelegateModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={
                    actionLoading === "delegate" ||
                    Boolean(
                      (() => {
                        const parent = mandates.find((m) => m.id === selectedParentId);
                        if (!parent) return false;
                        const maxOp = parent.max_amount_per_op / 100;
                        const pool = (parent.aggregate_spend_limit - parent.current_aggregate_spend - parent.delegated_child_budget_allocated) / 100;
                        return delegatePerOpInr > maxOp || (pool > 0 && delegateAggregateInr > pool);
                      })()
                    )
                  }
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 disabled:opacity-50"
                >
                  {actionLoading === "delegate" ? "Delegating..." : "Confirm Sub-Delegation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
