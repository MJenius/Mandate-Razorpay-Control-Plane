"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Plus,
  AlertCircle,
  RefreshCcw,
  Ban,
  PlayCircle,
  Trash2,
  Lock,
  Layers,
  ArrowUpRight,
  Clock,
  DollarSign,
  AlertTriangle,
} from "lucide-react";
import { api, Mandate } from "../../lib/api";

export default function MandatesPage() {
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New mandate form state
  const [newAgentId, setNewAgentId] = useState("agt_shopping_master_01");
  const [newPerOp, setNewPerOp] = useState(1000000); // ₹10,000 in paise
  const [newAggregate, setNewAggregate] = useState(5000000); // ₹50,000 in paise
  const [newCurrency, setNewCurrency] = useState("INR");
  const [newOps, setNewOps] = useState<string[]>(["CREATE_ORDER", "CAPTURE_PAYMENT"]);

  const loadMandates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMandates();
      setMandates(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load mandates from API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMandates();
  }, []);

  const handleSuspend = async (mandateId: string) => {
    if (!confirm(`Are you sure you want to suspend mandate ${mandateId}? All descendant child authority will also be suspended.`)) return;
    setActionLoading(mandateId);
    try {
      await api.suspendMandate(mandateId, "Manual suspension via Web Console");
      await loadMandates();
    } catch (err: unknown) {
      alert(`Suspension failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleActivate = async (mandateId: string) => {
    setActionLoading(mandateId);
    try {
      await api.activateMandate(mandateId);
      await loadMandates();
    } catch (err: unknown) {
      alert(`Activation failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevoke = async (mandateId: string) => {
    if (!confirm(`⚠️ PERMANENT REVOCATION: Revoking mandate ${mandateId} will immediately and permanently revoke ALL delegated child mandates in this tree. Proceed?`)) return;
    setActionLoading(mandateId);
    try {
      await api.revokeMandate(mandateId, "Permanent administrative revocation via Web Console");
      await loadMandates();
    } catch (err: unknown) {
      alert(`Revocation failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateMandate = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading("create");
    try {
      await api.createMandate({
        agent_id: newAgentId,
        granted_by_id: "prn_demo_merchant_01",
        currency: newCurrency,
        max_amount_per_op: Number(newPerOp),
        aggregate_spend_limit: Number(newAggregate),
        allowed_operations: newOps,
        valid_until: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      });
      setShowCreateModal(false);
      await loadMandates();
    } catch (err: unknown) {
      alert(`Failed to issue mandate: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <ShieldCheck className="h-6 w-6 text-blue-400" />
            Financial Mandates & Authority Contracts
          </h1>
          <p className="text-sm text-slate-400">
            Cryptographic budget bounds and per-operation constraints governing autonomous agent capabilities.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadMandates}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20 transition-colors"
          >
            <Plus className="h-4 w-4" /> Issue Mandate
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-900/50 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={loadMandates} className="underline hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Mandates Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((n) => (
            <div key={n} className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 h-64 animate-pulse"></div>
          ))}
        </div>
      ) : mandates.length === 0 ? (
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-12 text-center space-y-3">
          <ShieldCheck className="h-10 w-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No Mandates Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            No financial mandates are active in the database. Use &quot;Issue Mandate&quot; or run the Demo Reset to seed initial authority.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-medium text-white"
          >
            <Plus className="h-3.5 w-3.5" /> Issue First Mandate
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {mandates.map((m) => {
            const spentInr = m.current_aggregate_spend / 100;
            const reservedInr = m.reserved_spend / 100;
            const totalInr = m.aggregate_spend_limit / 100;
            const perOpInr = m.max_amount_per_op / 100;
            const delegatedInr = m.delegated_child_budget_allocated / 100;
            const pct = Math.min(100, Math.round(((spentInr + reservedInr) / (totalInr || 1)) * 100));

            return (
              <div
                key={m.id}
                className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                      {m.id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        m.status === "ACTIVE"
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : m.status === "SUSPENDED"
                          ? "bg-amber-950 text-amber-400 border border-amber-800"
                          : "bg-rose-950 text-rose-400 border border-rose-800"
                      }`}
                    >
                      {m.status}
                    </span>
                  </div>

                  <div>
                    <div className="text-xs font-mono text-slate-400">Agent: {m.agent_id}</div>
                    <div className="text-sm font-bold text-white mt-0.5">
                      Per-Op Cap: ₹{perOpInr.toLocaleString("en-IN")}
                    </div>
                  </div>

                  {/* Budget Usage Bar */}
                  <div className="space-y-1.5 pt-1">
                    <div className="flex justify-between text-[11px] font-mono text-slate-400">
                      <span>Spent: ₹{spentInr.toLocaleString("en-IN")}</span>
                      <span>Cap: ₹{totalInr.toLocaleString("en-IN")}</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          pct > 80 ? "bg-rose-500" : pct > 50 ? "bg-amber-500" : "bg-blue-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-[9px] font-mono text-slate-500">
                      <span>Reserved: ₹{reservedInr.toLocaleString("en-IN")}</span>
                      {delegatedInr > 0 && <span>Child Allocated: ₹{delegatedInr.toLocaleString("en-IN")}</span>}
                    </div>
                  </div>

                  {/* Allowed Ops & Depth */}
                  <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                    <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between">
                      <span>Delegation Depth: {m.delegation_depth}</span>
                      <span>Version: v{m.version}</span>
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

                {/* Mandate Actions */}
                <div className="pt-3 border-t border-[#1f293d] flex items-center justify-end gap-2">
                  {m.status === "ACTIVE" ? (
                    <button
                      onClick={() => handleSuspend(m.id)}
                      disabled={actionLoading === m.id}
                      className="px-2.5 py-1.5 bg-amber-950/40 hover:bg-amber-900/60 border border-amber-800/60 text-amber-300 rounded-lg text-[11px] font-medium transition-colors flex items-center gap-1"
                    >
                      <Ban className="h-3 w-3" /> Suspend
                    </button>
                  ) : m.status === "SUSPENDED" ? (
                    <button
                      onClick={() => handleActivate(m.id)}
                      disabled={actionLoading === m.id}
                      className="px-2.5 py-1.5 bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-800/60 text-emerald-300 rounded-lg text-[11px] font-medium transition-colors flex items-center gap-1"
                    >
                      <PlayCircle className="h-3 w-3" /> Activate
                    </button>
                  ) : null}

                  {m.status !== "REVOKED" && (
                    <button
                      onClick={() => handleRevoke(m.id)}
                      disabled={actionLoading === m.id}
                      className="px-2.5 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-lg text-[11px] font-medium transition-colors flex items-center gap-1"
                    >
                      <Trash2 className="h-3 w-3" /> Revoke
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Mandate Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <h2 className="text-base font-semibold text-white">Issue Root Financial Mandate</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateMandate} className="space-y-3.5 text-xs font-sans">
              <div>
                <label className="text-slate-400 block mb-1">Target Agent ID</label>
                <input
                  type="text"
                  value={newAgentId}
                  onChange={(e) => setNewAgentId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Per-Op Limit (Paise)</label>
                  <input
                    type="number"
                    value={newPerOp}
                    onChange={(e) => setNewPerOp(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                    required
                  />
                  <span className="text-[10px] text-slate-500">₹{(newPerOp / 100).toLocaleString()}</span>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Aggregate Spend (Paise)</label>
                  <input
                    type="number"
                    value={newAggregate}
                    onChange={(e) => setNewAggregate(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                    required
                  />
                  <span className="text-[10px] text-slate-500">₹{(newAggregate / 100).toLocaleString()}</span>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Currency</label>
                <input
                  type="text"
                  value={newCurrency}
                  onChange={(e) => setNewCurrency(e.target.value.toUpperCase())}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#1f293d]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading === "create"}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md disabled:opacity-50"
                >
                  {actionLoading === "create" ? "Issuing..." : "Confirm & Issue"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
