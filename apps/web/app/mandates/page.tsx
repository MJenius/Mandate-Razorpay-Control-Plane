"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Plus,
  RefreshCcw,
  Ban,
  PlayCircle,
  Trash2,
  Lock,
  Layers,
  Clock,
  DollarSign,
  AlertTriangle,
  GitBranch,
  CheckCircle2,
} from "lucide-react";
import { api, Mandate } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { useToast } from "@/components/common/Toast";
import { SkeletonCard } from "@/components/common/Skeleton";
import EmptyState from "@/components/common/EmptyState";
import ErrorState from "@/components/common/ErrorState";

export default function MandatesPage() {
  const toast = useToast();
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Modals & Dialogs state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [confirmState, setConfirmState] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    action: () => Promise<void>;
    isDestructive: boolean;
    confirmLabel: string;
  }>({
    isOpen: false,
    title: "",
    description: "",
    action: async () => {},
    isDestructive: true,
    confirmLabel: "Confirm",
  });

  // New mandate form state (INR inputs)
  const [newAgentId, setNewAgentId] = useState("agt_shopping_parent_01");
  const [newPerOpInr, setNewPerOpInr] = useState<number>(25000); // in Rupees ₹
  const [newAggregateInr, setNewAggregateInr] = useState<number>(100000); // in Rupees ₹
  const [newCurrency, setNewCurrency] = useState("INR");
  const [newOps, setNewOps] = useState<string[]>([
    "CREATE_ORDER",
    "CREATE_PAYMENT_LINK",
  ]);

  const loadMandates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMandates();
      setMandates(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load financial mandates");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMandates();
  }, []);

  const handleSuspend = (mandate: Mandate) => {
    setConfirmState({
      isOpen: true,
      title: `Suspend Mandate ${mandate.id}?`,
      description: `Suspending mandate for agent '${mandate.agent_id}' will immediately halt all pending operations and cascade suspension to all child sub-mandates.`,
      confirmLabel: "Suspend Mandate",
      isDestructive: true,
      action: async () => {
        setActionLoading(mandate.id);
        try {
          await api.suspendMandate(mandate.id, "Administrative suspension via Web Console");
          toast.success("Mandate Suspended", `Mandate ${mandate.id} and child authority suspended.`);
          await loadMandates();
        } catch (err: unknown) {
          toast.error("Suspension Failed", err instanceof Error ? err.message : String(err));
        } finally {
          setActionLoading(null);
        }
      },
    });
  };

  const handleActivate = (mandate: Mandate) => {
    setConfirmState({
      isOpen: true,
      title: `Activate Mandate ${mandate.id}?`,
      description: `Reactivating mandate will allow agent '${mandate.agent_id}' to resume financial transactions within authorized budget limits.`,
      confirmLabel: "Activate Mandate",
      isDestructive: false,
      action: async () => {
        setActionLoading(mandate.id);
        try {
          await api.activateMandate(mandate.id);
          toast.success("Mandate Activated", `Mandate ${mandate.id} is now ACTIVE.`);
          await loadMandates();
        } catch (err: unknown) {
          toast.error("Activation Failed", err instanceof Error ? err.message : String(err));
        } finally {
          setActionLoading(null);
        }
      },
    });
  };

  const handleRevoke = (mandate: Mandate) => {
    setConfirmState({
      isOpen: true,
      title: `⚠️ Permanently Revoke Mandate ${mandate.id}?`,
      description: `Revocation is PERMANENT and IRREVERSIBLE. All child sub-mandates delegated under this tree will be immediately and permanently revoked, preventing any future financial operations.`,
      confirmLabel: "Permanently Revoke",
      isDestructive: true,
      action: async () => {
        setActionLoading(mandate.id);
        try {
          await api.revokeMandate(mandate.id, "Permanent administrative revocation via Web Console");
          toast.success("Mandate Revoked", `Mandate ${mandate.id} permanently revoked.`);
          await loadMandates();
        } catch (err: unknown) {
          toast.error("Revocation Failed", err instanceof Error ? err.message : String(err));
        } finally {
          setActionLoading(null);
        }
      },
    });
  };

  const handleCreateMandate = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading("create");
    try {
      const perOpPaise = Math.round(newPerOpInr * 100);
      const aggregatePaise = Math.round(newAggregateInr * 100);

      await api.createMandate({
        agent_id: newAgentId,
        granted_by_id: "prn_demo_merchant_01",
        currency: newCurrency.toUpperCase(),
        max_amount_per_op: perOpPaise,
        aggregate_spend_limit: aggregatePaise,
        allowed_operations: newOps,
        valid_until: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      });

      toast.success(
        "Mandate Issued",
        `Issued ₹${newAggregateInr.toLocaleString("en-IN")} authority contract for ${newAgentId}`
      );
      setShowCreateModal(false);
      await loadMandates();
    } catch (err: unknown) {
      toast.error("Issuance Failed", err instanceof Error ? err.message : String(err));
    } finally {
      setActionLoading(null);
    }
  };

  const toggleOp = (op: string) => {
    setNewOps((prev) =>
      prev.includes(op) ? prev.filter((item) => item !== op) : [...prev, op]
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="Financial Mandates & Authority Contracts"
        icon={ShieldCheck}
        architecturePhase="Stage 2: Deterministic Authority Contracts"
        description="Mandates define explicit, cryptographically verifiable financial boundaries for AI agents. Rather than trusting LLM system prompts, Mandate strictly enforces single-transaction caps, aggregate budget pools, allowed operation types, and hierarchical delegation depths."
        lastUpdated={lastUpdated}
        isLoading={loading}
        onRefresh={loadMandates}
        actions={
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-blue-600/25 transition-all"
          >
            <Plus className="h-4 w-4" />
            <span>Issue New Mandate</span>
          </button>
        }
      />

      {error && <ErrorState message={error} onRetry={loadMandates} isRetrying={loading} />}

      {/* Mandates Grid */}
      {loading && mandates.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((n) => (
            <SkeletonCard key={n} />
          ))}
        </div>
      ) : mandates.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No Financial Mandates Active"
          description="There are currently no active authority contracts in the database. Issue a root mandate or run the Demo Reset to seed initial authority."
          actionLabel="Issue Root Mandate"
          onAction={() => setShowCreateModal(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {mandates.map((m) => {
            const spentInr = m.current_aggregate_spend / 100;
            const reservedInr = m.reserved_spend / 100;
            const totalInr = m.aggregate_spend_limit / 100;
            const perOpInr = m.max_amount_per_op / 100;
            const delegatedInr = m.delegated_child_budget_allocated / 100;
            const availableInr = Math.max(0, totalInr - (spentInr + reservedInr + delegatedInr));
            const pct = Math.min(100, Math.round(((spentInr + reservedInr) / (totalInr || 1)) * 100));

            return (
              <div
                key={m.id}
                className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl flex flex-col justify-between hover:border-slate-700 transition-all"
              >
                <div className="space-y-3.5">
                  {/* Top Identifier Row */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-xs font-bold text-white">{m.id}</span>
                      <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                        {m.agent_id}
                      </span>
                    </div>
                    <StatusBadge status={m.status} />
                  </div>

                  {/* Limits Overview */}
                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-[11px]">Per-Op Ceiling:</span>
                      <strong className="text-white font-bold">
                        ₹{perOpInr.toLocaleString("en-IN")}
                      </strong>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-[11px]">Aggregate Budget:</span>
                      <strong className="text-emerald-400 font-bold">
                        ₹{totalInr.toLocaleString("en-IN")}
                      </strong>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1.5 border-t border-slate-800">
                      <span>Available: ₹{availableInr.toLocaleString("en-IN")}</span>
                      <span>Currency: {m.currency}</span>
                    </div>
                  </div>

                  {/* Budget Usage Bar */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-[11px] font-mono text-slate-400">
                      <span>Committed: ₹{spentInr.toLocaleString("en-IN")}</span>
                      <span>{pct}% Used</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          pct > 80 ? "bg-rose-500" : pct > 50 ? "bg-amber-500" : "bg-blue-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] font-mono text-slate-500">
                      <span>Reserved (Pending): ₹{reservedInr.toLocaleString("en-IN")}</span>
                      {delegatedInr > 0 && <span>Child Allocated: ₹{delegatedInr.toLocaleString("en-IN")}</span>}
                    </div>
                  </div>

                  {/* Hierarchy & Whitelist */}
                  <div className="pt-2 border-t border-slate-800/80 space-y-2">
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                      <span>Delegation Depth: {m.delegation_depth}</span>
                      <span>Contract v{m.version}</span>
                    </div>

                    <div className="flex flex-wrap gap-1">
                      {m.allowed_operations.map((op) => (
                        <span
                          key={op}
                          className="px-1.5 py-0.5 bg-slate-900 border border-slate-800 rounded text-[9px] font-mono text-slate-300"
                        >
                          {op}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Mandate Actions Toolbar */}
                <div className="pt-3 border-t border-[#1f293d] flex items-center justify-end gap-2">
                  {m.status === "ACTIVE" ? (
                    <button
                      onClick={() => handleSuspend(m)}
                      disabled={actionLoading === m.id}
                      className="px-2.5 py-1.5 bg-amber-950/40 hover:bg-amber-900/60 border border-amber-800/60 text-amber-300 rounded-xl text-[11px] font-medium transition-colors flex items-center gap-1 disabled:opacity-50"
                    >
                      <Ban className="h-3 w-3" />
                      <span>Suspend</span>
                    </button>
                  ) : m.status === "SUSPENDED" ? (
                    <button
                      onClick={() => handleActivate(m)}
                      disabled={actionLoading === m.id}
                      className="px-2.5 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-800/60 text-emerald-300 rounded-xl text-[11px] font-medium transition-colors flex items-center gap-1 disabled:opacity-50"
                    >
                      <PlayCircle className="h-3 w-3" />
                      <span>Activate</span>
                    </button>
                  ) : null}

                  {m.status !== "REVOKED" && (
                    <button
                      onClick={() => handleRevoke(m)}
                      disabled={actionLoading === m.id}
                      className="px-2.5 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-xl text-[11px] font-medium transition-colors flex items-center gap-1 disabled:opacity-50"
                    >
                      <Trash2 className="h-3 w-3" />
                      <span>Revoke</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmState.isOpen}
        title={confirmState.title}
        description={confirmState.description}
        confirmLabel={confirmState.confirmLabel}
        isDestructive={confirmState.isDestructive}
        isLoading={actionLoading !== null}
        onConfirm={async () => {
          await confirmState.action();
          setConfirmState((prev) => ({ ...prev, isOpen: false }));
        }}
        onCancel={() => setConfirmState((prev) => ({ ...prev, isOpen: false }))}
      />

      {/* Issue Mandate Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <h2 className="text-base font-bold text-white">Issue Root Financial Mandate</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateMandate} className="space-y-4 text-xs font-sans">
              <div>
                <label className="text-slate-300 font-medium block mb-1.5">Target AI Agent ID</label>
                <input
                  type="text"
                  value={newAgentId}
                  onChange={(e) => setNewAgentId(e.target.value)}
                  placeholder="e.g. agt_shopping_parent_01"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label className="text-slate-300 font-medium block mb-1">
                    Per-Operation Limit (₹ INR)
                  </label>
                  <input
                    type="number"
                    value={newPerOpInr}
                    onChange={(e) => setNewPerOpInr(Number(e.target.value))}
                    min={1}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
                    required
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    = {Math.round(newPerOpInr * 100).toLocaleString()} Paise
                  </span>
                </div>

                <div>
                  <label className="text-slate-300 font-medium block mb-1">
                    Aggregate Spend Budget (₹ INR)
                  </label>
                  <input
                    type="number"
                    value={newAggregateInr}
                    onChange={(e) => setNewAggregateInr(Number(e.target.value))}
                    min={1}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white font-mono focus:outline-none focus:border-blue-500"
                    required
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    = {Math.round(newAggregateInr * 100).toLocaleString()} Paise
                  </span>
                </div>
              </div>

              <div>
                <label className="text-slate-300 font-medium block mb-1.5">Authorized Operations Whitelist</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: "CREATE_ORDER", label: "Create Order (Razorpay Order)" },
                    { id: "CREATE_PAYMENT_LINK", label: "Create Payment Link (Invoicing)" },
                    { id: "CAPTURE_PAYMENT", label: "Capture Payment" },
                    { id: "CREATE_REFUND", label: "Create Refund (Returns)" },
                  ].map((op) => (
                    <button
                      type="button"
                      key={op.id}
                      onClick={() => toggleOp(op.id)}
                      className={`p-2.5 rounded-xl border text-left text-[11px] font-mono transition-all ${
                        newOps.includes(op.id)
                          ? "bg-blue-600/15 border-blue-500 text-blue-300 font-bold"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      {newOps.includes(op.id) ? "✓ " : "+ "}
                      {op.id}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-[#1f293d]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading === "create"}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 disabled:opacity-50"
                >
                  {actionLoading === "create" ? "Issuing Contract..." : "Confirm & Issue Contract"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
