"use client";

import React, { useState } from "react";
import { ShoppingBag, ShieldCheck, Terminal, ArrowRight, Zap, CheckCircle2, XCircle, Bot, DollarSign, Store, Send, Layers } from "lucide-react";

export default function CommercePage() {
  const [buyerPrompt, setBuyerPrompt] = useState("");
  const [commerceSteps, setCommerceSteps] = useState<any[]>([
    {
      step: 1,
      title: "Natural Language Product Request",
      desc: "User: 'Find me the best mechanical keyboard under ₹10,000 and buy it.'",
      status: "COMPLETED",
      meta: "User Prompt Received",
    },
    {
      step: 2,
      title: "Agent Catalog Discovery & Selection",
      desc: "Shopping Agent matched SKU: 'prod_kb_01' (Keychron K2, ₹6,500).",
      status: "COMPLETED",
      meta: "Within ₹10,000 Constraint",
    },
    {
      step: 3,
      title: "Mandate MCP Security Gateway Interception",
      desc: "MCP Tool 'payments_create_order' dynamically exposed & validated against Mandate #mnd_q3.",
      status: "COMPLETED",
      meta: "Policy: ALLOW (Latency: 1.4ms)",
    },
    {
      step: 4,
      title: "Razorpay Test Mode Order Creation",
      desc: "Created Razorpay Order 'order_mock_77a91b' (Amount: ₹6,500, Receipt: rcpt_mcp_01).",
      status: "COMPLETED",
      meta: "0 Unchecked API Keys",
    },
    {
      step: 5,
      title: "Payment Signature & Webhook Confirmation",
      desc: "Webhook 'payment.captured' ingested with HMAC-SHA256 verification. Budget committed.",
      status: "COMPLETED",
      meta: "Immutable Audit Log #aud_49fa",
    },
  ]);

  const [activeTab, setActiveTab] = useState<"buyer" | "merchant" | "comparison">("comparison");

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Razorpay-Native Agentic Commerce & MCP Gateway</h1>
          <p className="text-sm text-slate-400">
            End-to-end AI agent commerce governed by Model Context Protocol (MCP) tool gateway filtering and bounded authority.
          </p>
        </div>
        <div className="flex rounded-lg bg-slate-900 border border-slate-800 p-1">
          <button
            onClick={() => setActiveTab("comparison")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === "comparison" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Direct MCP vs Mandate
          </button>
          <button
            onClick={() => setActiveTab("buyer")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === "buyer" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Buyer Commerce Flow
          </button>
          <button
            onClick={() => setActiveTab("merchant")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === "merchant" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Merchant Invoicing Flow
          </button>
        </div>
      </div>

      {/* Comparison View */}
      {activeTab === "comparison" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Direct MCP (Unrestricted) */}
          <div className="rounded-xl bg-[#111827] border border-rose-500/20 p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-rose-500/20 pb-3">
              <div className="flex items-center gap-2">
                <Terminal className="h-5 w-5 text-rose-400" />
                <h2 className="text-base font-semibold text-white">Direct Razorpay MCP Access</h2>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/10 text-rose-400 border border-rose-500/20">
                CAPABILITY WITHOUT AUTHORITY
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Agent receives raw Razorpay credentials and an unconstrained tool surface (35+ tools including payouts, settlements, and unlimited refunds).
            </p>
            <div className="space-y-2 text-xs font-mono">
              <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-900/40 text-rose-300 flex items-start gap-2">
                <XCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                <div>
                  <span className="font-bold block">35+ Exposed Tools:</span>
                  <span className="text-[11px] text-rose-400">Shopping bot can execute payouts, settlements, or unauthorized bulk refunds.</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-900/40 text-rose-300 flex items-start gap-2">
                <XCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                <div>
                  <span className="font-bold block">No Per-Op / Aggregate Ceilings:</span>
                  <span className="text-[11px] text-rose-400">Model hallucination or prompt injection can charge unlimited amounts.</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-900/40 text-rose-300 flex items-start gap-2">
                <XCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                <div>
                  <span className="font-bold block">No Hierarchical Delegation:</span>
                  <span className="text-[11px] text-rose-400">Child agents inherit full raw API keys without non-escalation limits.</span>
                </div>
              </div>
            </div>
          </div>

          {/* Mandate-Protected MCP */}
          <div className="rounded-xl bg-[#111827] border border-blue-500/30 p-6 space-y-4 shadow-lg shadow-blue-500/5">
            <div className="flex items-center justify-between border-b border-blue-500/20 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-blue-400" />
                <h2 className="text-base font-semibold text-white">Mandate-Protected MCP Gateway</h2>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                BOUNDED AGENTIC COMMERCE
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Agent connects to Mandate's JSON-RPC 2.0 MCP Gateway. Mandate holds credentials, filters tools dynamically, and verifies every operation deterministically.
            </p>
            <div className="space-y-2 text-xs font-mono">
              <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-emerald-300 flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
                <div>
                  <span className="font-bold block">Dynamic Tool Surface Filtering:</span>
                  <span className="text-[11px] text-emerald-400">Exposes only 2-3 whitelisted tools (slashes 92% of exposed attack surface).</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-emerald-300 flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
                <div>
                  <span className="font-bold block">Two-Phase Budget Accounting:</span>
                  <span className="text-[11px] text-emerald-400">Atomic CAS reservations prevent concurrent sibling over-delegation.</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-emerald-300 flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
                <div>
                  <span className="font-bold block">Strict Schema Validation & Non-Escalation:</span>
                  <span className="text-[11px] text-emerald-400">Unexpected injected parameters are strictly rejected with JSON-RPC error.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Buyer Flow Timeline View */}
      {(activeTab === "buyer" || activeTab === "comparison") && (
        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-[#1f293d] pb-3">
            <ShoppingBag className="h-4 w-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-white">Autonomous Agentic Commerce Execution Trace</h2>
          </div>

          <div className="space-y-3">
            {commerceSteps.map((s) => (
              <div key={s.step} className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 flex items-start justify-between text-xs">
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center font-mono font-bold text-blue-400 text-[11px]">
                    {s.step}
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-semibold text-slate-200 block">{s.title}</span>
                    <span className="text-slate-400 text-[11px]">{s.desc}</span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-emerald-400 shrink-0">
                  {s.meta}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Merchant Invoicing Tab */}
      {activeTab === "merchant" && (
        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-[#1f293d] pb-3">
            <Store className="h-4 w-4 text-purple-400" />
            <h2 className="text-sm font-semibold text-white">Merchant Autonomous Payment Link & Invoicing Agent</h2>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2 text-xs">
            <span className="font-semibold text-slate-200">Merchant MCP Tool: <code className="text-purple-400 font-mono">payments_create_payment_link</code></span>
            <p className="text-slate-400 leading-relaxed text-[11px]">
              Allows autonomous invoicing agents to generate shareable customer checkout links while strictly bounding invoice amount, recipient email format, and merchant aggregate receivables.
            </p>
            <div className="mt-3 p-3 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300">
              Generated Short URL: <a href="#" className="text-blue-400 underline">https://rzp.io/i/mnd_inv_8829</a> | Amount: ₹4,500.00
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
