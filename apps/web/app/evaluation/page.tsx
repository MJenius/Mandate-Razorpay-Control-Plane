import React from "react";
import { FlaskConical, Play, CheckCircle2, ShieldAlert } from "lucide-react";

export default function EvaluationPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Agent & Policy Evaluation</h1>
          <p className="text-sm text-slate-400">
            Adversarial and boundary test harness to simulate rogue agent behaviors and policy resilience.
          </p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 shadow-sm shadow-indigo-500/20">
          <Play className="h-4 w-4" /> Run Simulation Suite
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 space-y-4">
          <h2 className="text-base font-semibold text-white">Adversarial Scenarios</h2>
          <div className="space-y-3">
            {[
              { title: "Rapid Burst Budget Exhaustion", result: "BLOCKED (429 / Budget Exceeded)", pass: true },
              { title: "Operation Type Escalation (Unauthorized Refund)", result: "REJECTED (403 Policy Rejection)", pass: true },
              { title: "Expired Mandate Execution Attempt", result: "REJECTED (Mandate Inactive)", pass: true },
              { title: "Idempotency Replay Attack", result: "HANDLED (Cached Idempotent Return)", pass: true },
            ].map((scenario) => (
              <div key={scenario.title} className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                <span className="text-xs text-slate-200 font-medium">{scenario.title}</span>
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Passed
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 space-y-4">
          <h2 className="text-base font-semibold text-white">Evaluation Readiness</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            In Phase 0, the evaluation suite verifies rule evaluator edge cases and deterministic idempotency locks. Later phases will introduce autonomous agent behavioral benchmarks and adversarial fuzzing.
          </p>
          <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20">
            <span className="text-xs font-mono text-blue-400 block mb-1">Status</span>
            <p className="text-xs text-slate-300">Phase 0 baseline verification complete: 100% deterministic test coverage on core bounds.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
