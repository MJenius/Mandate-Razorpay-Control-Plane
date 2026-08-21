import React from "react";
import { Sliders, ShieldCheck, Check, Plus } from "lucide-react";

export default function PoliciesPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Policy Engine Rules</h1>
          <p className="text-sm text-slate-400">
            Pre-flight verification rules evaluated synchronously before any financial gateway dispatch.
          </p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20">
          <Plus className="h-4 w-4" /> Add Custom Rule
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          {
            name: "Mandate Validity Rule",
            code: "MANDATE_VALIDITY_CHECK",
            desc: "Ensures caller holds an ACTIVE mandate that has not reached expiry.",
            active: true,
          },
          {
            name: "Amount Bound Rule",
            code: "AMOUNT_BOUND_CHECK",
            desc: "Enforces single-operation caps and total aggregate remaining budget.",
            active: true,
          },
          {
            name: "Operation Authorization Rule",
            code: "ALLOWED_OPERATION_TYPE_CHECK",
            desc: "Restricts operation types (e.g. Refunds, Orders) to explicit allowlists.",
            active: true,
          },
        ].map((rule) => (
          <div key={rule.code} className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                {rule.code}
              </span>
              <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                <Check className="h-3.5 w-3.5" /> Enforced
              </span>
            </div>
            <h3 className="font-semibold text-white text-base">{rule.name}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">{rule.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
