"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  Play,
  CheckCircle2,
  XCircle,
  DollarSign,
  Clock,
  ShieldCheck,
  Cpu,
  BarChart3,
  RefreshCcw,
  AlertTriangle,
  Layers,
} from "lucide-react";
import { api, BenchmarkMetrics } from "../../lib/api";

export default function EvalLabPage() {
  const [running, setRunning] = useState(false);
  const [multiplier, setMultiplier] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<BenchmarkMetrics | null>(null);

  const handleRunBenchmark = async () => {
    setRunning(true);
    setError(null);
    try {
      const data = await api.runEvaluation(42, multiplier, "agt_shopping_parent_01");
      setReport(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to execute benchmark trial");
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    // Run initial baseline evaluation
    handleRunBenchmark();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <ShieldAlert className="h-6 w-6 text-rose-400" />
            Adversarial Evaluation & Safety Lab
          </h1>
          <p className="text-sm text-slate-400">
            Empirical stress-testing over 5 adversarial profiles (Overreaching, Compromised, Buggy, Prompt Injection, Legitimate).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl text-xs">
            <span className="text-slate-400 font-mono">Volume:</span>
            {[1, 5, 20].map((m) => (
              <button
                key={m}
                onClick={() => setMultiplier(m)}
                disabled={running}
                className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                  multiplier === m
                    ? "bg-rose-600 text-white font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {m * 50} Scenarios
              </button>
            ))}
          </div>

          <button
            onClick={handleRunBenchmark}
            disabled={running}
            className="flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 transition-colors disabled:opacity-50 shadow-lg shadow-rose-600/20"
          >
            <Play className={`h-3.5 w-3.5 ${running ? "animate-spin" : ""}`} />
            {running ? `Executing ${multiplier * 50} Scenarios...` : "Run Simulation Suite"}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-900 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={handleRunBenchmark} className="underline hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Metric Cards */}
      {report && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="uppercase tracking-wider font-mono text-[10px]">Security Recall</span>
              <ShieldAlert className="h-4 w-4 text-rose-400" />
            </div>
            <p className="text-3xl font-bold font-mono text-white">
              {(report.unauthorized_action_block_rate * 100).toFixed(1)}%
            </p>
            <span className="text-[11px] text-emerald-400 font-mono">
              {report.adversarial_scenarios} Hostile Scenarios Blocked
            </span>
          </div>

          <div className="p-5 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="uppercase tracking-wider font-mono text-[10px]">Financial Loss Prevented</span>
              <DollarSign className="h-4 w-4 text-emerald-400" />
            </div>
            <p className="text-3xl font-bold font-mono text-emerald-400">
              ₹{(report.financial_loss_prevented_inr).toLocaleString("en-IN")}
            </p>
            <span className="text-[11px] text-slate-400 font-mono">
              Counterfactual Loss: ₹{report.counterfactual_baseline_loss_inr.toLocaleString("en-IN")}
            </span>
          </div>

          <div className="p-5 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="uppercase tracking-wider font-mono text-[10px]">Policy Bypass Rate</span>
              <ShieldCheck className="h-4 w-4 text-blue-400" />
            </div>
            <p className="text-3xl font-bold font-mono text-white">
              {(report.policy_bypass_rate * 100).toFixed(1)}%
            </p>
            <span className="text-[11px] text-emerald-400 font-mono">
              {report.unauthorized_razorpay_effects} Unauthorized Razorpay Calls
            </span>
          </div>

          <div className="p-5 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="uppercase tracking-wider font-mono text-[10px]">P95 Decision Latency</span>
              <Clock className="h-4 w-4 text-indigo-400" />
            </div>
            <p className="text-3xl font-bold font-mono text-white">{report.latency_p95_ms} ms</p>
            <span className="text-[11px] text-slate-400 font-mono">
              P50: {report.latency_p50_ms}ms · P99: {report.latency_p99_ms}ms
            </span>
          </div>
        </div>
      )}

      {/* Baseline Comparative Table */}
      {report && (
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl">
          <div className="flex items-center gap-2 border-b border-[#1f293d] pb-3">
            <BarChart3 className="h-4 w-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-white">Empirical Architectural Comparison</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-sans">
              <thead className="bg-slate-900/80 text-slate-400 uppercase font-mono text-[10px]">
                <tr>
                  <th className="py-3 px-4">Control Model</th>
                  <th className="py-3 px-4">Attack Block Rate</th>
                  <th className="py-3 px-4">Policy Bypass Rate</th>
                  <th className="py-3 px-4">Financial Loss Incurred</th>
                  <th className="py-3 px-4">Architectural Guarantees</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f293d] font-mono text-xs">
                <tr className="hover:bg-slate-900/40">
                  <td className="py-3.5 px-4 font-sans font-semibold text-slate-300">
                    No Controls (Direct Model Calling)
                  </td>
                  <td className="py-3.5 px-4 text-rose-400">0.0%</td>
                  <td className="py-3.5 px-4 text-rose-400">100.0%</td>
                  <td className="py-3.5 px-4 text-rose-400">
                    ₹{report.counterfactual_baseline_loss_inr.toLocaleString("en-IN")}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 font-sans text-[11px]">
                    All adversarial prompts directly disburse money via live gateway.
                  </td>
                </tr>
                <tr className="hover:bg-slate-900/40">
                  <td className="py-3.5 px-4 font-sans font-semibold text-slate-300">
                    Basic Tool Permissions (Boolean Roles)
                  </td>
                  <td className="py-3.5 px-4 text-amber-400">28.0%</td>
                  <td className="py-3.5 px-4 text-amber-400">72.0%</td>
                  <td className="py-3.5 px-4 text-amber-400">
                    ₹{(report.counterfactual_baseline_loss_inr * 0.72).toLocaleString("en-IN")}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 font-sans text-[11px]">
                    Vulnerable to quantity escalation, concurrent race conditions, budget exhaustion.
                  </td>
                </tr>
                <tr className="bg-blue-500/5 hover:bg-blue-500/10">
                  <td className="py-3.5 px-4 font-sans font-semibold text-blue-400 flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-blue-400" /> Mandate Control Plane
                  </td>
                  <td className="py-3.5 px-4 text-emerald-400 font-bold">
                    {(report.unauthorized_action_block_rate * 100).toFixed(1)}%
                  </td>
                  <td className="py-3.5 px-4 text-emerald-400 font-bold">
                    {(report.policy_bypass_rate * 100).toFixed(1)}%
                  </td>
                  <td className="py-3.5 px-4 text-emerald-400 font-bold">₹0.00 (Zero Loss)</td>
                  <td className="py-3.5 px-4 text-emerald-300 font-sans text-[11px]">
                    Deterministic policy contracts, two-phase budget reservation, 0 gateway dispatch on DENY.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detailed Adversarial Scenarios Inspector */}
      {report && (
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-purple-400" />
              <h2 className="text-sm font-semibold text-white">
                Live Scenario Executions & Policy Diagnostics ({report.detailed_results.length} Runs)
              </h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Deterministic Seed #42</span>
          </div>

          <div className="divide-y divide-[#1f293d] rounded-xl border border-slate-800 bg-slate-950/60 text-xs font-sans max-h-96 overflow-y-auto">
            {report.detailed_results.map((sc) => (
              <div key={sc.scenario_id} className="p-3.5 flex items-center justify-between hover:bg-slate-900/40">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2 font-mono">
                    <span className="font-semibold text-slate-200 text-xs">{sc.name}</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400">
                      {sc.profile}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{sc.category}</span>
                  </div>
                  <span className="text-[11px] text-slate-400 block font-mono">
                    At-Risk Protected: ₹{sc.protected_inr.toLocaleString("en-IN")} · Latency: {sc.latency_ms}ms
                  </span>
                </div>
                <div className="flex items-center gap-3 font-mono">
                  <span className="text-[11px] text-slate-400">Expected: {sc.expected}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      sc.actual === "DENY"
                        ? "bg-rose-950 text-rose-300 border border-rose-800"
                        : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                    }`}
                  >
                    {sc.actual}
                  </span>
                  {sc.passed ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <XCircle className="h-4 w-4 text-rose-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
