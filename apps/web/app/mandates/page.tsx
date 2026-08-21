import React from "react";
import { ShieldCheck, Plus, AlertCircle } from "lucide-react";

export default function MandatesPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Financial Mandates</h1>
          <p className="text-sm text-slate-400">
            Authorization contracts defining spending limits, allowed operations, and validity periods.
          </p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20">
          <Plus className="h-4 w-4" /> Issue Mandate
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[
          {
            id: "mnd_procure_q3",
            agent: "Procurement Agent",
            perOp: "₹ 50,000",
            spent: "₹ 15,000",
            total: "₹ 1,00,000",
            pct: 15,
            ops: ["CREATE_ORDER", "CAPTURE_PAYMENT"],
            validUntil: "2026-12-31",
          },
          {
            id: "mnd_support_refunds",
            agent: "Customer Support Agent",
            perOp: "₹ 2,000",
            spent: "₹ 8,400",
            total: "₹ 50,000",
            pct: 16.8,
            ops: ["CREATE_REFUND"],
            validUntil: "2026-09-30",
          },
          {
            id: "mnd_billing_links",
            agent: "Billing Reconciliation",
            perOp: "₹ 10,000",
            spent: "₹ 42,000",
            total: "₹ 1,00,000",
            pct: 42,
            ops: ["CREATE_PAYMENT_LINK", "CANCEL_PAYMENT_LINK"],
            validUntil: "2026-11-15",
          },
        ].map((mandate) => (
          <div key={mandate.id} className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                {mandate.id}
              </span>
              <span className="text-xs text-emerald-400 font-medium">ACTIVE</span>
            </div>

            <div>
              <h3 className="font-semibold text-white text-base">{mandate.agent}</h3>
              <p className="text-xs text-slate-400 mt-0.5">Expires {mandate.validUntil}</p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Budget Consumed</span>
                <span className="text-slate-200 font-mono">{mandate.spent} / {mandate.total}</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full"
                  style={{ width: `${mandate.pct}%` }}
                />
              </div>
            </div>

            <div className="pt-2 border-t border-[#1f293d] flex items-center justify-between text-xs text-slate-400">
              <span>Max / Op: <strong className="text-white font-mono">{mandate.perOp}</strong></span>
              <div className="flex gap-1">
                {mandate.ops.map((op) => (
                  <span key={op} className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
                    {op.replace("CREATE_", "")}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
