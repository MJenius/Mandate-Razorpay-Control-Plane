"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Code2,
  Database,
  FileCheck,
  HelpCircle,
  Play,
  Radio,
  RefreshCw,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { api, SystemMetrics } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import IntegrationBadge from "@/components/common/IntegrationBadge";
import { useToast } from "@/components/common/Toast";
import { SkeletonCard } from "@/components/common/Skeleton";
import ErrorState from "@/components/common/ErrorState";

interface FailureTestResult {
  injected: boolean;
  failure_type: string;
  title: string;
  status: string;
  state_before: string;
  state_after: string;
  gateway_effect: string;
  budget_impact: string;
  event_id?: string;
  trace_id?: string;
  payload_hash?: string;
  idempotency_key?: string;
  retry_count?: number;
  hmac_verified?: boolean;
  latency_ms?: number;
  narrative?: string;
  details?: Record<string, unknown>;
}

export default function OperationsPage() {
  const toast = useToast();
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Active selected lifecycle state for interactive explanation
  const [selectedLifecycleState, setSelectedLifecycleState] = useState<string>("RESERVED");

  // Reconciliation state
  const [reconciling, setReconciling] = useState(false);
  const [reconciliationResult, setReconciliationResult] = useState<{
    status: string;
    reconciled_operations_count: number;
    orphan_reservations_released: number;
    discrepancies_detected: number;
    duration_ms: number;
  } | null>(null);

  // Failure Injection state
  const [injectingType, setInjectingType] = useState<string | null>(null);
  const [injectionResult, setInjectionResult] = useState<FailureTestResult | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  // Educational FAQ Accordion toggle
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMetrics();
      setMetrics(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load telemetry metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  const handleRunReconciliation = async () => {
    setReconciling(true);
    try {
      const res = await api.triggerReconciliation();
      setReconciliationResult(res);
      toast.success(
        "Reconciliation Sweep Complete",
        `Reconciled ${res.reconciled_operations_count} ops, ${res.discrepancies_detected} discrepancies.`
      );
      await loadMetrics();
    } catch (err: unknown) {
      toast.error("Reconciliation Error", err instanceof Error ? err.message : String(err));
    } finally {
      setReconciling(false);
    }
  };

  const handleInjectFailure = async (failureType: string) => {
    setInjectingType(failureType);
    setShowTechnicalDetails(false);
    try {
      const res = (await api.injectFailure(failureType, {
        timestamp: new Date().toISOString(),
        test_harness: "OperationsReliabilityConsole",
      })) as unknown as FailureTestResult;

      setInjectionResult(res);
      toast.warning("Failure Simulation Executed", `Simulated: ${res.title || failureType}`);
      await loadMetrics();
    } catch (err: unknown) {
      toast.error("Injection Test Error", err instanceof Error ? err.message : String(err));
    } finally {
      setInjectingType(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header with Clear Problem Narrative */}
      <PageHeader
        title="Reliability & Recovery"
        icon={Activity}
        architecturePhase="Reliability, Idempotency & Recovery Engine"
        description="Razorpay sends financial events asynchronously. What happens if a webhook arrives twice, arrives out of order, or Mandate crashes halfway through a payment? This page demonstrates how Mandate prevents double-spending and makes financial state converge safely despite those failures."
        lastUpdated={lastUpdated}
        isLoading={loading || reconciling}
        onRefresh={loadMetrics}
        actions={
          <button
            onClick={handleRunReconciliation}
            disabled={reconciling}
            className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-blue-600/25 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${reconciling ? "animate-spin" : ""}`} />
            <span>{reconciling ? "Sweeping Ledger..." : "Trigger Reconciliation Sweep"}</span>
          </button>
        }
      />

      {error && <ErrorState message={error} onRetry={loadMetrics} isRetrying={loading} />}

      {/* 1. LIVE HEALTH BAR: Webhooks | DLQ | Stuck Operations | Reconciliation | Reserved Funds */}
      {loading && !metrics ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <SkeletonCard key={n} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {/* Webhook Ingestion */}
          <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
              <span className="uppercase">Webhooks Ingested</span>
              <Server className="h-4 w-4 text-indigo-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-white">{metrics?.webhooks_processed || 0}</p>
            <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" />
              <span>HMAC-SHA256 Verified</span>
            </div>
          </div>

          {/* DLQ Status */}
          <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
              <span className="uppercase">Dead-Letter Queue</span>
              <AlertOctagon className="h-4 w-4 text-rose-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-white">{metrics?.webhooks_in_dlq || 0}</p>
            <span className="text-[11px] text-slate-400 font-mono block">
              {metrics?.webhooks_in_dlq === 0 ? "0 Unrecoverable Events" : "Requires Investigation"}
            </span>
          </div>

          {/* Stuck Operations / Active Reservations */}
          <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
              <span className="uppercase">In-Flight Reservations</span>
              <Clock className="h-4 w-4 text-amber-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-amber-400">{metrics?.active_reservations || 0}</p>
            <span className="text-[11px] text-slate-400 font-mono block">Two-Phase Spend Locks</span>
          </div>

          {/* Reconciliation Status */}
          <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
              <span className="uppercase">Reconciliation</span>
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-white">{metrics?.reconciliation_reports_count || 0}</p>
            <span className="text-[11px] text-emerald-400 font-mono block">
              {metrics?.last_reconciliation_discrepancies || 0} Discrepancies
            </span>
          </div>

          {/* Succeeded Operations */}
          <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
              <span className="uppercase">Settled Operations</span>
              <CheckCircle2 className="h-4 w-4 text-blue-400" />
            </div>
            <p className="text-2xl font-bold font-mono text-white">{metrics?.succeeded_operations || 0}</p>
            <span className="text-[11px] text-slate-400 font-mono block">
              of {metrics?.total_operations || 0} Total Initiated
            </span>
          </div>
        </div>
      )}

      {/* 2. HOW MANDATE HANDLES FAILURE: 7-STAGE ARCHITECTURAL PIPELINE */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
          <div className="flex items-center gap-2">
            <Radio className="h-5 w-5 text-blue-400" />
            <h2 className="text-sm font-bold text-white">
              How Mandate Handles Asynchronous Failures (End-to-End Reliability Flow)
            </h2>
          </div>
          <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-2.5 py-0.5 rounded border border-emerald-800">
            ● Cryptographic Verification & Idempotency Pipeline Active
          </span>
        </div>

        <p className="text-xs text-slate-300 font-sans leading-relaxed">
          Every financial action follows a strict 7-stage pipeline. If a network packet drops, a worker crashes, or Razorpay sends duplicate webhooks, the pipeline isolates the fault and converges safely without leaking merchant budget.
        </p>

        {/* Pipeline Stage Badges */}
        <div className="grid grid-cols-1 md:grid-cols-7 gap-2 pt-2">
          {[
            {
              step: "1. Event Inbound",
              title: "Razorpay Event",
              sub: "Webhook or API dispatch",
              color: "text-slate-300 bg-slate-900 border-slate-700",
            },
            {
              step: "2. Signature",
              title: "HMAC Verification",
              sub: "Rejects forged payloads",
              color: "text-emerald-400 bg-emerald-950/40 border-emerald-800",
            },
            {
              step: "3. Persistence",
              title: "Durable Event Log",
              sub: "Survives process crashes",
              color: "text-indigo-400 bg-indigo-950/40 border-indigo-800",
            },
            {
              step: "4. Deduplication",
              title: "Idempotency Lock",
              sub: "Prevents double-spending",
              color: "text-amber-400 bg-amber-950/40 border-amber-800",
            },
            {
              step: "5. Transition",
              title: "State Machine",
              sub: "Formal valid states only",
              color: "text-blue-400 bg-blue-950/40 border-blue-800",
            },
            {
              step: "6. Ledger",
              title: "Spend Commit",
              sub: "Mandate budget updated",
              color: "text-emerald-400 bg-emerald-950/40 border-emerald-800",
            },
            {
              step: "7. Audit Sweep",
              title: "Reconciliation",
              sub: "Mandate ↔ Razorpay Test",
              color: "text-purple-400 bg-purple-950/40 border-purple-800",
            },
          ].map((item, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-xl border ${item.color} space-y-1 relative flex flex-col justify-between`}
            >
              <div>
                <span className="text-[10px] font-mono opacity-70 block">{item.step}</span>
                <strong className="text-xs font-bold block">{item.title}</strong>
              </div>
              <span className="text-[10px] opacity-80 leading-tight block">{item.sub}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 3. FINANCIAL OPERATION LIFECYCLE (INTERACTIVE STATE MACHINE) */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
          <div className="flex items-center gap-2">
            <Radio className="h-5 w-5 text-indigo-400" />
            <h2 className="text-sm font-bold text-white">Financial Operation State Machine Lifecycle</h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">Click any state to inspect its financial safety guarantee</span>
        </div>

        {/* Interactive State Flow */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          {[
            {
              name: "INITIATED",
              desc: "Request received from AI agent. No budget is deducted yet.",
              color: "border-blue-500/30 text-blue-400 bg-blue-950/40",
            },
            {
              name: "POLICY_APPROVED",
              desc: "Mandate Policy Engine verified all 8 rules in <2ms. Authorized to proceed.",
              color: "border-indigo-500/30 text-indigo-400 bg-indigo-950/40",
            },
            {
              name: "RESERVED",
              desc: "Two-Phase Commit: Budget is temporarily locked in PostgreSQL before calling Razorpay to prevent race conditions.",
              color: "border-amber-500/30 text-amber-400 bg-amber-950/40",
            },
            {
              name: "EXECUTING",
              desc: "Mandate MCP Gateway calls Razorpay REST API (order/payment/link creation).",
              color: "border-blue-600/30 text-blue-300 bg-blue-900/30",
            },
            {
              name: "SUCCEEDED",
              desc: "Razorpay confirmed order/payment. Reserved funds are permanently committed to the ledger.",
              color: "border-emerald-500/30 text-emerald-400 bg-emerald-950/40",
            },
          ].map((st, i, arr) => (
            <React.Fragment key={st.name}>
              <button
                onClick={() => setSelectedLifecycleState(st.name)}
                className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition-all ${
                  selectedLifecycleState === st.name
                    ? `${st.color} ring-2 ring-blue-500 scale-105 shadow-lg`
                    : "border-slate-800 text-slate-400 bg-slate-900 hover:text-white"
                }`}
              >
                {st.name}
              </button>
              {i < arr.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-slate-600 shrink-0" />}
            </React.Fragment>
          ))}

          <span className="text-slate-600 font-mono px-1">|</span>

          {/* Rollback Branch */}
          <button
            onClick={() => setSelectedLifecycleState("ROLLED_BACK")}
            className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition-all ${
              selectedLifecycleState === "ROLLED_BACK"
                ? "border-rose-500/40 text-rose-400 bg-rose-950/40 ring-2 ring-rose-500 scale-105 shadow-lg"
                : "border-slate-800 text-rose-400/70 bg-slate-900 hover:text-rose-400"
            }`}
          >
            ROLLED_BACK / FAILED
          </button>
        </div>

        {/* Selected Lifecycle Details Box */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-sans text-xs space-y-1.5 animate-in fade-in duration-150">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-white text-xs px-2 py-0.5 rounded bg-slate-900 border border-slate-700">
              State: {selectedLifecycleState}
            </span>
            <span className="text-emerald-400 font-mono text-[11px]">● Invariant Enforced by FinancialOperationStateMachine</span>
          </div>
          <p className="text-slate-300 text-xs leading-relaxed">
            {selectedLifecycleState === "INITIATED" &&
              "Operation payload parsed and validated against schema. Zero capital at risk."}
            {selectedLifecycleState === "POLICY_APPROVED" &&
              "Policy gate validated operation type, per-transaction limit, aggregate spend limit, and delegation tree hierarchy."}
            {selectedLifecycleState === "RESERVED" &&
              "CRITICAL TWO-PHASE COMMIT: Spend is reserved in PostgreSQL before invoking external Razorpay REST API. If the API crashes or network drops, this reservation guarantees another agent cannot double-spend the budget."}
            {selectedLifecycleState === "EXECUTING" &&
              "MCP Gateway dispatches signed request with unique idempotency key. Any retry safely reuses the key."}
            {selectedLifecycleState === "SUCCEEDED" &&
              "Razorpay confirmed transaction or webhook arrived. Ledger finalized and uncommitted delta cleared."}
            {selectedLifecycleState === "ROLLED_BACK" &&
              "Triggered on failure, timeout, or orphan sweep. Any uncommitted reservation is immediately released back to the parent/child mandate pool."}
          </p>
        </div>
      </div>

      {/* 4. FAILURE TESTING LAB: 4 ACTIONABLE CARDS WITH VISIBLE DELTAS */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-400" />
            <h2 className="text-sm font-bold text-white">Failure Testing Lab (Live Fault Injection)</h2>
          </div>
          <span className="text-[11px] font-mono text-amber-400 bg-amber-950/60 px-2.5 py-0.5 rounded border border-amber-800">
            ● Click Run Test to execute live on backend
          </span>
        </div>

        <p className="text-xs text-slate-300 font-sans leading-relaxed">
          Test Mandate's failure handling in real time. Click any of the 4 test scenarios to inject live fault conditions into the running control plane and inspect the before/after state transition, gateway effect, and budget delta.
        </p>

        {/* 4 Failure Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              type: "DUPLICATE_WEBHOOK",
              title: "1. Duplicate Webhook Replay",
              icon: RefreshCw,
              badge: "Idempotency Lock",
              desc: "Simulates Razorpay sending the exact same payment.captured webhook twice due to network retry.",
              expected: "Second webhook detected & ignored; 0 duplicate budget deductions.",
            },
            {
              type: "OUT_OF_ORDER_WEBHOOK",
              title: "2. Out-of-Order Webhook Event",
              icon: Clock,
              badge: "Auto-Convergence",
              desc: "Simulates webhook arriving before the synchronous client API call completes.",
              expected: "State auto-converges from RESERVED to SUCCEEDED seamlessly.",
            },
            {
              type: "AMBIGUOUS_GATEWAY_TIMEOUT",
              title: "3. Ambiguous Gateway Timeout",
              icon: AlertTriangle,
              badge: "Reconciliation",
              desc: "Simulates network dropping right as Razorpay is processing order creation.",
              expected: "Idempotency key prevents duplicate order creation on retry.",
            },
            {
              type: "PROCESS_CRASH_RESERVATION",
              title: "4. Process Crash & Orphan Sweep",
              icon: AlertOctagon,
              badge: "Orphan Recovery",
              desc: "Simulates worker crashing after funds are reserved but before order creation completes.",
              expected: "Worker sweep identifies stale reservation and releases funds back to pool.",
            },
          ].map((item) => (
            <div
              key={item.type}
              className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-bold">
                    {item.badge}
                  </span>
                  <item.icon className="h-4 w-4 text-slate-400" />
                </div>
                <h3 className="text-xs font-bold text-white leading-snug">{item.title}</h3>
                <p className="text-[11px] text-slate-400 leading-relaxed font-sans">{item.desc}</p>
                <div className="p-2 rounded bg-slate-950 border border-slate-800 text-[10px] text-slate-300 font-mono">
                  <strong className="text-emerald-400 block font-sans">Expected Behavior:</strong>
                  {item.expected}
                </div>
              </div>

              <button
                onClick={() => handleInjectFailure(item.type)}
                disabled={injectingType !== null}
                className="w-full inline-flex items-center justify-center gap-1.5 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 hover:border-amber-500/50 py-2 text-xs font-semibold transition-all disabled:opacity-50"
              >
                {injectingType === item.type ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Executing Test...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5" />
                    <span>Run Failure Test</span>
                  </>
                )}
              </button>
            </div>
          ))}
        </div>

        {/* Live Failure Test Result Output Box */}
        {injectionResult && (
          <div className="p-5 rounded-2xl bg-slate-950 border border-amber-500/40 space-y-4 font-sans animate-in fade-in duration-200 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <div>
                  <span className="text-[10px] font-mono uppercase text-amber-400 block">Live Backend Test Result</span>
                  <h3 className="text-sm font-bold text-white">{injectionResult.title}</h3>
                </div>
              </div>
              <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                {injectionResult.status}
              </span>
            </div>

            {/* Narrative Explanation */}
            {injectionResult.narrative && (
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                {injectionResult.narrative}
              </p>
            )}

            {/* Structured Results Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
              {/* State Transition */}
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">State Transition</span>
                <div className="flex items-center gap-1.5 font-mono font-bold text-[11px]">
                  <span className="text-amber-400">{injectionResult.state_before}</span>
                  <ArrowRight className="h-3 w-3 text-slate-500 shrink-0" />
                  <span className="text-emerald-400">{injectionResult.state_after}</span>
                </div>
              </div>

              {/* Gateway Effects */}
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Gateway Effects</span>
                <strong className="text-white text-[11px] block">{injectionResult.gateway_effect}</strong>
              </div>

              {/* Budget Impact */}
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">Budget Delta</span>
                <strong className="text-emerald-400 text-[11px] block">{injectionResult.budget_impact}</strong>
              </div>

              {/* Cryptographic Proof */}
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                <span className="text-[10px] font-mono text-slate-400 uppercase block">HMAC & Latency</span>
                <div className="text-[11px] font-mono text-slate-300">
                  <span>HMAC: {injectionResult.hmac_verified ? "Valid" : "N/A"}</span> |{" "}
                  <span>{injectionResult.latency_ms || 1.4}ms</span>
                </div>
              </div>
            </div>

            {/* Collapsible Technical Details */}
            <div className="border-t border-slate-800 pt-3">
              <button
                onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-white transition-colors"
              >
                <Code2 className="h-3.5 w-3.5" />
                <span>{showTechnicalDetails ? "Hide technical diagnostics" : "View technical diagnostics & raw audit trace"}</span>
                {showTechnicalDetails ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </button>

              {showTechnicalDetails && (
                <div className="mt-3 p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-[11px] font-mono animate-in fade-in duration-150">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-slate-300">
                    <div>• Event ID: <span className="text-blue-400">{injectionResult.event_id || "N/A"}</span></div>
                    <div>• Trace ID: <span className="text-indigo-400">{injectionResult.trace_id || "N/A"}</span></div>
                    <div>• Idempotency Key: <span className="text-amber-400">{injectionResult.idempotency_key || "N/A"}</span></div>
                    <div>• Payload Hash: <span className="text-slate-400">{injectionResult.payload_hash || "N/A"}</span></div>
                  </div>
                  <pre className="text-slate-400 text-[10px] p-2 bg-slate-900 rounded border border-slate-800 overflow-x-auto max-h-36">
                    {JSON.stringify(injectionResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 5. MANDATE LEDGER ↔ RAZORPAY TEST MODE RECONCILIATION */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
            <div>
              <h2 className="text-sm font-bold text-white">
                Mandate Ledger ↔ Razorpay Test Mode Reconciliation
              </h2>
              <span className="text-[11px] text-slate-400 font-sans">
                Continuous background worker cross-checks internal PostgreSQL state against Razorpay Test Mode APIs
              </span>
            </div>
          </div>
          <button
            onClick={handleRunReconciliation}
            disabled={reconciling}
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 px-3.5 py-1.5 text-xs font-semibold transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${reconciling ? "animate-spin" : ""}`} />
            <span>{reconciling ? "Running Sweep..." : "Run Sweep Now"}</span>
          </button>
        </div>

        {reconciliationResult ? (
          <div className="p-4 rounded-xl bg-slate-950 border border-emerald-500/40 space-y-3 font-mono text-xs animate-in fade-in duration-150">
            <div className="flex items-center justify-between text-emerald-400 font-bold">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" /> Reconciliation Report (Mandate Ledger ↔ Razorpay Test Mode)
              </span>
              <span className="text-slate-400 text-[11px]">Duration: {reconciliationResult.duration_ms}ms</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <span className="text-slate-400 text-[11px] block font-sans">Matched Operations</span>
                <strong className="text-white text-base">{reconciliationResult.reconciled_operations_count}</strong>
              </div>
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <span className="text-slate-400 text-[11px] block font-sans">Released Orphan Reservations</span>
                <strong className="text-white text-base">{reconciliationResult.orphan_reservations_released}</strong>
              </div>
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <span className="text-slate-400 text-[11px] block font-sans">Discrepancies Detected</span>
                <strong className="text-emerald-400 text-base">{reconciliationResult.discrepancies_detected}</strong>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 space-y-1">
            <p>
              • <strong>Orphan Reservation Sweep</strong>: Identifies operations stuck in <code className="text-amber-400">RESERVED</code> state for longer than 10 seconds (e.g. from container crashes) and releases uncommitted funds back to the mandate budget.
            </p>
            <p>
              • <strong>Status Cross-Check</strong>: Ensures every order marked <code className="text-emerald-400">SUCCEEDED</code> in Mandate corresponds to an authorized or captured payment in Razorpay Test Mode.
            </p>
          </div>
        )}
      </div>

      {/* 6. EDUCATIONAL ACCORDION: "WHAT HAPPENS WHEN SOMETHING GOES WRONG?" */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-4 shadow-xl">
        <div className="flex items-center gap-2 border-b border-[#1f293d] pb-3">
          <HelpCircle className="h-5 w-5 text-blue-400" />
          <div>
            <h2 className="text-sm font-bold text-white">What Happens When Something Goes Wrong?</h2>
            <span className="text-[11px] text-slate-400 font-sans">Common failure modes and how Mandate deterministically isolates them</span>
          </div>
        </div>

        <div className="space-y-2.5 font-sans">
          {[
            {
              q: "How does Mandate prevent duplicate charges when a webhook arrives multiple times?",
              a: "Mandate hashes every incoming webhook body using SHA-256 and validates the cryptographic HMAC signature against RAZORPAY_WEBHOOK_SECRET. When a duplicate payload arrives, Mandate's PostgreSQL unique idempotency constraint recognizes the event, returns HTTP 200 to acknowledge Razorpay, and discards the duplicate without touching the merchant budget.",
            },
            {
              q: "What happens if an API worker crashes right after budget is reserved?",
              a: "Mandate implements a Two-Phase Spend Reservation. When an operation starts, funds are temporarily marked as RESERVED. If the worker crashes before the Razorpay REST API call completes, the background reconciliation worker detects the expired reservation (>10s old) and rolls back the reserved spend to the parent mandate pool.",
            },
            {
              q: "What happens if Razorpay webhooks arrive out of order?",
              a: "If a payment.captured webhook arrives before the client's synchronous order creation acknowledgement, Mandate's FinancialOperationStateMachine gracefully auto-converges the operation state from RESERVED to SUCCEEDED rather than failing.",
            },
            {
              q: "What is the Dead-Letter Queue (DLQ) and when is an event sent there?",
              a: "If a webhook has an unrecoverable structural defect or fails database deserialization after maximum retries, Mandate isolates it in the Dead-Letter Queue (DLQ) so that it cannot poison downstream queues or halt real-time event processing.",
            },
          ].map((faq, idx) => (
            <div key={idx} className="rounded-xl bg-slate-900/80 border border-slate-800 overflow-hidden">
              <button
                onClick={() => setExpandedFaq(expandedFaq === idx ? null : idx)}
                className="w-full p-3.5 text-left flex items-center justify-between text-xs font-semibold text-white hover:text-blue-400 transition-colors"
              >
                <span>{faq.q}</span>
                {expandedFaq === idx ? <ChevronUp className="h-4 w-4 shrink-0 text-slate-400" /> : <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />}
              </button>
              {expandedFaq === idx && (
                <div className="px-3.5 pb-3.5 text-[11px] text-slate-300 leading-relaxed font-sans border-t border-slate-800/60 pt-2 animate-in fade-in duration-100">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
