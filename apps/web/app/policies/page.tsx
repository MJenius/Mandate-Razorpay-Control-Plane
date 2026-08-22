"use client";

import React, { useState, useEffect } from "react";
import {
  Sliders,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Activity,
  Layers,
  Cpu,
  Lock,
  ArrowRight,
  Info,
  Clock,
} from "lucide-react";
import {
  api,
  PolicyRuleMetadata,
  PolicyEvaluationDetails,
  Mandate,
  Agent,
} from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import { useToast } from "@/components/common/Toast";
import { SkeletonCard, SkeletonTable } from "@/components/common/Skeleton";
import ErrorState from "@/components/common/ErrorState";

export default function PoliciesPage() {
  const toast = useToast();
  const [rules, setRules] = useState<PolicyRuleMetadata[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Test Simulator State
  const [testAgentId, setTestAgentId] = useState("agt_shopping_parent_01");
  const [testMandateId, setTestMandateId] = useState("mnd_parent_root_01");
  const [testOpType, setTestOpType] = useState("CREATE_ORDER");
  const [testAmountInr, setTestAmountInr] = useState<number>(6500); // in Rupees ₹
  const [testCurrency, setTestCurrency] = useState("INR");
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<PolicyEvaluationDetails | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [rulesRes, agentsRes, mandatesRes] = await Promise.all([
        api.getPolicyRules(),
        api.getAgents(),
        api.getMandates(),
      ]);

      setRules(rulesRes.rules);
      setAgents(agentsRes);
      setMandates(mandatesRes);

      if (mandatesRes.length > 0) {
        setTestMandateId(mandatesRes[0].id);
        setTestAgentId(mandatesRes[0].agent_id);
      }

      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load Policy Engine rules");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunPolicyTest = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setEvaluating(true);
    try {
      const amountPaise = Math.round(testAmountInr * 100);
      const result = await api.testEvaluatePolicy({
        agent_id: testAgentId,
        mandate_id: testMandateId,
        operation_type: testOpType,
        amount: amountPaise,
        currency: testCurrency,
        payload: { simulated_test: true },
      });

      setEvalResult(result);
      if (result.decision === "ALLOW") {
        toast.success("Policy ALLOW", "All 8 deterministic rules passed successfully.");
      } else if (result.decision === "DENY") {
        toast.warning("Policy DENIED", result.rejection_reasons?.join("; "));
      } else {
        toast.info("Requires Review", result.review_reasons?.join("; "));
      }
    } catch (err: unknown) {
      toast.error("Evaluation Failed", err instanceof Error ? err.message : String(err));
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="Deterministic Policy Engine & Rule Diagnostics"
        icon={Sliders}
        architecturePhase="Stage 3: Pre-Flight Deterministic Policy Gate"
        description="The Policy Engine evaluates 8 deterministic rules synchronously in memory before any financial action reaches the Razorpay API. It enforces the Zero-Gateway-Dispatch Invariant: if any policy rule fails, zero network calls or credentials touch external gateways."
        lastUpdated={lastUpdated}
        isLoading={loading}
        onRefresh={loadData}
      />

      {error && <ErrorState message={error} onRetry={loadData} isRetrying={loading} />}

      {/* Core Architectural Paradigm Explanation: Mandate vs Policy Engine */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-2xl bg-[#111827] border border-blue-500/30 p-5 space-y-2.5 shadow-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20">
              Authority Contract
            </span>
            <Lock className="h-4 w-4 text-blue-400" />
          </div>
          <h3 className="text-base font-bold text-white">What is a Financial Mandate?</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            A <strong>Mandate</strong> is a passive, immutable authority contract granted by a principal. It specifies the <em>declarative boundary</em>: maximum amount per operation, aggregate budget pool, allowed operation whitelist, and hierarchical delegation constraints.
          </p>
        </div>

        <div className="rounded-2xl bg-[#111827] border border-purple-500/30 p-5 space-y-2.5 shadow-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase text-purple-400 bg-purple-500/10 px-2.5 py-0.5 rounded-full border border-purple-500/20">
              Enforcement Mechanism
            </span>
            <ShieldCheck className="h-4 w-4 text-purple-400" />
          </div>
          <h3 className="text-base font-bold text-white">What is the Policy Engine?</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            The <strong>Policy Engine</strong> is the active, zero-hallucination runtime enforcement gate. It intercepts every proposed action and evaluates the 8 rules against the mandate, guaranteeing sub-15ms decisions and strictly 0 gateway dispatches on non-ALLOW.
          </p>
        </div>
      </div>

      {/* 8 Actual Policy Rules Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Sliders className="h-4 w-4 text-blue-400" />
            <span>The 8 Real Deterministic Policy Engine Rules</span>
          </h2>
          <span className="text-xs text-slate-400 font-mono">Evaluated in strict sequential order</span>
        </div>

        {loading && rules.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
              <SkeletonCard key={n} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {rules.map((rule) => (
              <div
                key={rule.name}
                className="rounded-2xl bg-[#111827] border border-[#1f293d] p-4 space-y-3 shadow-xl flex flex-col justify-between hover:border-slate-700 transition-all"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="h-6 w-6 rounded-lg bg-slate-900 border border-slate-800 text-blue-400 flex items-center justify-center font-bold">
                      #{rule.order}
                    </span>
                    <span className="text-[10px] font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                      ACTIVE
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                      {rule.category}
                    </span>
                    <h3 className="font-bold text-white text-xs font-mono mt-0.5">
                      {rule.name}
                    </h3>
                  </div>

                  <p className="text-[11px] text-slate-300 leading-snug font-sans">
                    {rule.description}
                  </p>
                </div>

                <div className="pt-2.5 border-t border-slate-800 space-y-1 text-[10px] font-mono text-slate-400">
                  <div>
                    <strong className="text-slate-300">Invariant:</strong> {rule.invariant}
                  </div>
                  <div className="text-indigo-400">Enforcement: {rule.enforcement}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Interactive Policy Rule Evaluator Testbed */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 shadow-xl space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[#1f293d] pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Play className="h-4 w-4 text-emerald-400" />
              <span>Live Policy Engine Testbed (Dry-Run Evaluation)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulate candidate financial operations against the actual backend PolicyEngine without mutating database state.
            </p>
          </div>
          <span className="text-[11px] font-mono text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded border border-blue-500/20">
            Backed by /api/v1/policies/test-evaluate
          </span>
        </div>

        {/* Input Parameters Form */}
        <form onSubmit={handleRunPolicyTest} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs font-sans">
          <div className="sm:col-span-2">
            <label className="text-slate-400 block mb-1 font-mono">Authorized Agent & Bound Mandate</label>
            <select
              value={`${testAgentId}::${testMandateId}`}
              onChange={(e) => {
                const [agId, mndId] = e.target.value.split("::");
                setTestAgentId(agId);
                setTestMandateId(mndId);
                const m = mandates.find((item) => item.id === mndId);
                if (m?.allowed_operations?.length) {
                  setTestOpType(m.allowed_operations[0]);
                }
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
            >
              {mandates.map((m) => {
                const a = agents.find((ag) => ag.id === m.agent_id);
                const agentName = a ? a.name : m.agent_id;
                return (
                  <option key={m.id} value={`${m.agent_id}::${m.id}`}>
                    {agentName} ({m.agent_id}) ⇄ {m.id} (Cap: ₹{(m.max_amount_per_op / 100).toLocaleString("en-IN")})
                  </option>
                );
              })}
              {mandates.length === 0 && (
                <option value="agt_shopping_parent_01::mnd_parent_root_01">
                  Primary Shopping Agent ⇄ mnd_parent_root_01
                </option>
              )}
            </select>
          </div>

          <div>
            <label className="text-slate-400 block mb-1 font-mono">Operation Type</label>
            <select
              value={testOpType}
              onChange={(e) => setTestOpType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
            >
              <option value="CREATE_ORDER">CREATE_ORDER</option>
              <option value="CREATE_PAYMENT_LINK">CREATE_PAYMENT_LINK</option>
              <option value="CAPTURE_PAYMENT">CAPTURE_PAYMENT</option>
              <option value="CREATE_REFUND">CREATE_REFUND</option>
            </select>
          </div>

          <div>
            <label className="text-slate-400 block mb-1 font-mono">Amount (₹ INR)</label>
            <input
              type="number"
              value={testAmountInr}
              onChange={(e) => setTestAmountInr(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={evaluating}
              className="w-full h-[38px] rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-all shadow-md shadow-emerald-600/20 disabled:opacity-50"
            >
              <Play className={`h-3.5 w-3.5 ${evaluating ? "animate-spin" : ""}`} />
              <span>{evaluating ? "Evaluating..." : "Evaluate Policy"}</span>
            </button>
          </div>
        </form>

        {/* Live Evaluation Diagnostics Table */}
        {evalResult && (
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-3 font-mono text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-3">
                <span className="text-slate-400">Overall Decision:</span>
                <StatusBadge status={evalResult.decision || "DENY"} size="md" />
              </div>
              <div className="text-slate-400 text-[11px]">
                Total Latency: <strong className="text-white">{evalResult.total_latency_ms}ms</strong> · 8 Rules Evaluated
              </div>
            </div>

            {evalResult.rejection_reasons && evalResult.rejection_reasons.length > 0 && (
              <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-900/60 text-rose-300 text-xs space-y-1">
                <strong className="text-rose-400 block font-bold">Policy Rejection Details:</strong>
                {evalResult.rejection_reasons.map((r, i) => (
                  <div key={i}>• {r}</div>
                ))}
              </div>
            )}

            {/* Individual Rule Diagnostics Breakdown */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/60 text-slate-400 uppercase text-[10px]">
                  <tr>
                    <th className="py-2 px-3">Rule Name</th>
                    <th className="py-2 px-3">Decision</th>
                    <th className="py-2 px-3">Diagnostic Reason</th>
                    <th className="py-2 px-3 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {evalResult.rule_diagnostics?.map((rd) => (
                    <tr key={rd.rule_name} className="hover:bg-slate-900/30">
                      <td className="py-2 px-3 font-bold text-white text-[11px]">{rd.rule_name}</td>
                      <td className="py-2 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] font-bold ${
                            rd.passed
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                              : "bg-rose-950 text-rose-300 border border-rose-800"
                          }`}
                        >
                          {rd.passed ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                          {rd.passed ? "PASS" : "FAIL"}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-[11px] text-slate-400">{rd.reason}</td>
                      <td className="py-2 px-3 text-right text-slate-500 text-[10px]">{rd.latency_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
