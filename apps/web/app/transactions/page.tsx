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
  ChevronRight,
  Filter,
  ShieldCheck,
  Radio,
  UserCheck,
  AlertTriangle,
  FileText,
  Lock,
} from "lucide-react";
import { api, FinancialOperation } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import IntegrationBadge from "@/components/common/IntegrationBadge";
import { useToast } from "@/components/common/Toast";
import { SkeletonTable } from "@/components/common/Skeleton";
import EmptyState from "@/components/common/EmptyState";
import ErrorState from "@/components/common/ErrorState";

export default function TransactionsPage() {
  const toast = useToast();
  const [operations, setOperations] = useState<FinancialOperation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedOp, setSelectedOp] = useState<FinancialOperation | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const loadOperations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getOperations();
      setOperations(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load financial operations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOperations();
  }, []);

  const handleApprove = async (opId: string, approved: boolean) => {
    setActionLoading(opId);
    try {
      await api.approveOperation(opId, "prn_demo_merchant_01", approved, "Human approval review");
      toast.success(
        approved ? "Operation Approved" : "Operation Rejected",
        `Operation ${opId} updated.`
      );
      setSelectedOp(null);
      await loadOperations();
    } catch (err: unknown) {
      toast.error("Approval Failed", err instanceof Error ? err.message : String(err));
    } finally {
      setActionLoading(null);
    }
  };

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
      (statusFilter === "FAILED" &&
        (op.status === "FAILED" || op.status === "POLICY_REJECTED")) ||
      (statusFilter === "REQUIRES_APPROVAL" && op.status === "REQUIRES_APPROVAL") ||
      (statusFilter === "PENDING" &&
        (op.status === "RESERVED" ||
          op.status === "EXECUTING" ||
          op.status === "INITIATED"));

    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.ceil(filteredOps.length / pageSize) || 1;
  const paginatedOps = filteredOps.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="Financial Operations & Gateway Ledger"
        icon={CreditCard}
        architecturePhase="Stage 5: Gateway Dispatch & State Machine Ledger"
        description="Comprehensive ledger of financial operations executed by AI agents. Tracks full forensic lifecycles from initial agent request through deterministic policy evaluation, two-phase budget reservation, Razorpay Test Mode execution, and HMAC webhook settlement."
        lastUpdated={lastUpdated}
        isLoading={loading}
        onRefresh={loadOperations}
      />

      {error && <ErrorState message={error} onRetry={loadOperations} isRetrying={loading} />}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-3 bg-[#111827] border border-[#1f293d] p-4 rounded-2xl shadow-xl">
        <div className="relative flex-1">
          <Search className="h-4 w-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search by Operation ID, Agent ID, Mandate ID, Action..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Status:</span>
          {(["ALL", "SUCCEEDED", "PENDING", "REQUIRES_APPROVAL", "FAILED"] as const).map(
            (s) => (
              <button
                key={s}
                onClick={() => {
                  setStatusFilter(s);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  statusFilter === s
                    ? "bg-blue-600 text-white font-bold shadow-sm"
                    : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
                }`}
              >
                {s.replace("_", " ")}
              </button>
            )
          )}
        </div>
      </div>

      {/* Operations Ledger Table */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] border-b border-[#1f293d]">
              <tr>
                <th className="px-5 py-3.5">Operation ID</th>
                <th className="px-5 py-3.5">Agent / Mandate</th>
                <th className="px-5 py-3.5">Operation Type</th>
                <th className="px-5 py-3.5">Amount (INR)</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Timestamp</th>
                <th className="px-5 py-3.5 text-right">Lifecycle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f293d] text-slate-300 font-mono">
              {loading && operations.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-500 text-xs">
                    Querying live PostgreSQL operations table...
                  </td>
                </tr>
              ) : paginatedOps.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-500 text-xs">
                    No matching financial operations found in the ledger.
                  </td>
                </tr>
              ) : (
                paginatedOps.map((op) => {
                  const amountInr = (op.amount / 100).toLocaleString("en-IN", {
                    style: "currency",
                    currency: op.currency || "INR",
                  });

                  return (
                    <tr key={op.id} className="hover:bg-slate-900/50 transition-colors">
                      <td className="px-5 py-3.5 font-bold text-white text-xs">{op.operation_id}</td>
                      <td className="px-5 py-3.5 text-slate-400">
                        <div>{op.agent_id}</div>
                        <div className="text-[10px] text-slate-500">{op.mandate_id}</div>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300">
                          {op.operation_type}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-bold text-slate-100">{amountInr}</td>
                      <td className="px-5 py-3.5">
                        <StatusBadge status={op.status} />
                      </td>
                      <td className="px-5 py-3.5 text-slate-500 text-[11px]">
                        {new Date(op.created_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => setSelectedOp(op)}
                          className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium transition-colors"
                        >
                          Inspect Lifecycle →
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {filteredOps.length > pageSize && (
          <div className="p-4 border-t border-[#1f293d] bg-slate-900/60 flex items-center justify-between text-xs font-mono text-slate-400">
            <span>
              Showing {(currentPage - 1) * pageSize + 1}–
              {Math.min(currentPage * pageSize, filteredOps.length)} of {filteredOps.length} Operations
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50"
              >
                Previous
              </button>
              <span>Page {currentPage} of {totalPages}</span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Forensic Lifecycle Inspector Drawer / Modal */}
      {selectedOp && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl animate-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <div>
                <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                  <span>Operation Forensic Inspector</span>
                  <StatusBadge status={selectedOp.status} />
                </h2>
                <span className="text-[11px] text-slate-400 font-mono">
                  Operation ID: {selectedOp.operation_id}
                </span>
              </div>
              <button
                onClick={() => setSelectedOp(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* 6-Stage Forensic Lifecycle Stepper */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-xs">
              <span className="text-slate-400 font-bold uppercase text-[10px] block">
                Forensic Operation Lifecycle:
              </span>

              <div className="space-y-2.5">
                {/* 1. Request Initiated */}
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 text-[11px] shrink-0 font-bold">
                    1
                  </div>
                  <div className="space-y-0.5 flex-1">
                    <span className="font-bold text-white">Request Initiated by AI Agent</span>
                    <p className="text-[11px] text-slate-400">
                      Agent: <strong className="text-slate-200">{selectedOp.agent_id}</strong> · Amount: ₹{(selectedOp.amount / 100).toLocaleString("en-IN")} · Type: {selectedOp.operation_type}
                    </p>
                    <div className="text-[10px] text-slate-500">Idempotency Key: {selectedOp.idempotency_key}</div>
                  </div>
                </div>

                {/* 2. Policy Engine Evaluation */}
                <div className="flex items-start gap-3">
                  <div
                    className={`h-6 w-6 rounded-full flex items-center justify-center text-[11px] shrink-0 font-bold border ${
                      selectedOp.policy_evaluation_details?.decision === "ALLOW"
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                        : "bg-rose-500/10 border-rose-500/30 text-rose-400"
                    }`}
                  >
                    2
                  </div>
                  <div className="space-y-0.5 flex-1">
                    <span className="font-bold text-white">Deterministic Policy Engine Gate</span>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={selectedOp.policy_evaluation_details?.decision || "DENY"} />
                      {selectedOp.policy_evaluation_details?.total_latency_ms && (
                        <span className="text-[10px] text-slate-400">
                          Latency: {selectedOp.policy_evaluation_details.total_latency_ms}ms
                        </span>
                      )}
                    </div>
                    {selectedOp.error_message && (
                      <p className="text-[11px] text-rose-400 bg-rose-950/40 p-2 rounded border border-rose-900 mt-1">
                        {selectedOp.error_message}
                      </p>
                    )}
                  </div>
                </div>

                {/* 3. Budget Reservation & Gateway Dispatch */}
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-[11px] shrink-0 font-bold">
                    3
                  </div>
                  <div className="space-y-0.5 flex-1">
                    <span className="font-bold text-white">Two-Phase Budget Reservation & Gateway</span>
                    <p className="text-[11px] text-slate-400">
                      {selectedOp.status === "POLICY_REJECTED"
                        ? "Zero Gateway Dispatch: 0 network calls sent to Razorpay."
                        : `Budget reserved atomically under Mandate ${selectedOp.mandate_id}. Dispatched to Razorpay Test Mode.`}
                    </p>
                  </div>
                </div>

                {/* 4. Final State */}
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-[11px] shrink-0 font-bold">
                    4
                  </div>
                  <div className="space-y-0.5 flex-1">
                    <span className="font-bold text-white">Settlement & Audit Trail</span>
                    <p className="text-[11px] text-slate-400">
                      Final Status: <strong className="text-white">{selectedOp.status}</strong> · Trace ID: {selectedOp.trace_id || "None"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Human-in-the-Loop Sign-Off Controls */}
            {selectedOp.status === "REQUIRES_APPROVAL" && (
              <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/60 space-y-3 font-sans text-xs">
                <div className="flex items-center gap-2 text-amber-300 font-bold">
                  <UserCheck className="h-4 w-4" />
                  <span>Human Principal Sign-Off Required</span>
                </div>
                <p className="text-slate-300 text-xs leading-relaxed">
                  This high-value transaction exceeds the autonomous mandate review threshold. As an administrator, you must explicitly approve or deny gateway execution.
                </p>
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={() => handleApprove(selectedOp.operation_id, false)}
                    disabled={actionLoading !== null}
                    className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold"
                  >
                    Reject Operation
                  </button>
                  <button
                    onClick={() => handleApprove(selectedOp.operation_id, true)}
                    disabled={actionLoading !== null}
                    className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-md"
                  >
                    Approve & Dispatch Gateway
                  </button>
                </div>
              </div>
            )}

            {/* Raw JSON Payload Inspector */}
            <div className="space-y-2 font-mono text-xs">
              <span className="text-slate-400 block font-bold">Raw Payload Data:</span>
              <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[10px] text-emerald-400 overflow-x-auto max-h-48">
                {JSON.stringify(selectedOp.payload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
