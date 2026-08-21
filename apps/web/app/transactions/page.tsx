"use client";

import React, { useState, useEffect } from "react";
import {
  CreditCard,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCcw,
  Search,
  ArrowUpRight,
  ExternalLink,
  Layers,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { api, FinancialOperation } from "../../lib/api";

export default function TransactionsPage() {
  const [operations, setOperations] = useState<FinancialOperation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedOp, setSelectedOp] = useState<FinancialOperation | null>(null);

  const loadOperations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getOperations();
      setOperations(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load financial operations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOperations();
  }, []);

  const filteredOps = operations.filter((op) => {
    const matchesSearch =
      searchQuery === "" ||
      op.operation_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      op.agent_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      op.mandate_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      op.operation_type.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === "ALL" ||
      (statusFilter === "SUCCEEDED" && op.status === "SUCCEEDED") ||
      (statusFilter === "FAILED" && (op.status === "FAILED" || op.status === "POLICY_REJECTED")) ||
      (statusFilter === "PENDING" && (op.status === "RESERVED" || op.status === "EXECUTING" || op.status === "REQUIRES_APPROVAL"));

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <CreditCard className="h-6 w-6 text-emerald-400" />
            Financial Operations & Razorpay Gateway Ledger
          </h1>
          <p className="text-sm text-slate-400">
            Real-time ledger of authorized agent financial requests, two-phase budget reservations, and gateway orders.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadOperations}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 bg-[#111827] border border-[#1f293d] p-3.5 rounded-2xl">
        <div className="relative flex-1">
          <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by Operation ID, Agent ID, Mandate ID..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Status:</span>
          {(["ALL", "SUCCEEDED", "PENDING", "FAILED"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors ${
                statusFilter === s
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Operations Table */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs font-sans">
          <thead className="bg-slate-900/80 text-slate-400 uppercase font-mono text-[10px] border-b border-[#1f293d]">
            <tr>
              <th className="px-5 py-3.5">Operation ID</th>
              <th className="px-5 py-3.5">Agent / Mandate</th>
              <th className="px-5 py-3.5">Action</th>
              <th className="px-5 py-3.5">Amount (INR)</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5">Timestamp</th>
              <th className="px-5 py-3.5 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1f293d] text-slate-300 font-mono">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-slate-500 text-xs animate-pulse">
                  Querying live PostgreSQL ledger...
                </td>
              </tr>
            ) : filteredOps.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-slate-500 text-xs">
                  No matching financial operations found.
                </td>
              </tr>
            ) : (
              filteredOps.map((op) => {
                const amountInr = (op.amount / 100).toLocaleString("en-IN", {
                  style: "currency",
                  currency: op.currency || "INR",
                });

                return (
                  <tr key={op.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-5 py-3.5 font-bold text-white text-[11px]">{op.operation_id}</td>
                    <td className="px-5 py-3.5 text-slate-400">
                      <div>{op.agent_id}</div>
                      <div className="text-[10px] text-slate-500">{op.mandate_id}</div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
                        {op.operation_type}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-bold text-slate-200">{amountInr}</td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          op.status === "SUCCEEDED"
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : op.status === "FAILED" || op.status === "POLICY_REJECTED"
                            ? "bg-rose-950 text-rose-400 border border-rose-800"
                            : "bg-blue-950 text-blue-400 border border-blue-800"
                        }`}
                      >
                        {op.status === "SUCCEEDED" ? (
                          <CheckCircle2 className="h-3 w-3" />
                        ) : op.status === "FAILED" || op.status === "POLICY_REJECTED" ? (
                          <XCircle className="h-3 w-3" />
                        ) : (
                          <Clock className="h-3 w-3" />
                        )}
                        {op.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-[10px]">
                      {new Date(op.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => setSelectedOp(op)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px] transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Inspect Modal */}
      {selectedOp && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <h2 className="text-sm font-semibold text-white font-mono">
                Operation Details ({selectedOp.operation_id})
              </h2>
              <button onClick={() => setSelectedOp(null)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="space-y-3 font-mono text-xs text-slate-300 max-h-96 overflow-y-auto">
              <div className="grid grid-cols-2 gap-2 bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div>Status: <strong className="text-white">{selectedOp.status}</strong></div>
                <div>Amount: <strong className="text-emerald-400">₹{(selectedOp.amount / 100).toLocaleString()}</strong></div>
                <div>Agent: <span className="text-slate-400">{selectedOp.agent_id}</span></div>
                <div>Mandate: <span className="text-slate-400">{selectedOp.mandate_id}</span></div>
                {selectedOp.trace_id && <div className="col-span-2">Trace ID: <span className="text-blue-400">{selectedOp.trace_id}</span></div>}
              </div>

              {selectedOp.error_message && (
                <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-900 text-rose-300 text-[11px]">
                  <strong>Error:</strong> {selectedOp.error_message}
                </div>
              )}

              <div>
                <span className="text-slate-400 font-bold block mb-1">Payload:</span>
                <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[10px] text-emerald-400 overflow-x-auto">
                  {JSON.stringify(selectedOp.payload, null, 2)}
                </pre>
              </div>

              {selectedOp.policy_evaluation_details && (
                <div>
                  <span className="text-slate-400 font-bold block mb-1">Policy Diagnostic:</span>
                  <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[10px] text-indigo-300 overflow-x-auto">
                    {JSON.stringify(selectedOp.policy_evaluation_details, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-3 border-t border-[#1f293d]">
              <button
                onClick={() => setSelectedOp(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
