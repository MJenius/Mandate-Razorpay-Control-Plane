"use client";

import React, { useState } from "react";
import {
  Bot,
  ShieldCheck,
  Sliders,
  Terminal,
  CreditCard,
  Radio,
  FileText,
  ArrowRight,
  Lock,
  CheckCircle2,
  Cpu,
} from "lucide-react";

interface StepDetail {
  id: string;
  name: string;
  subhead: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  tag: string;
  description: string;
  securityGuarantee: string;
}

const ARCHITECTURE_STEPS: StepDetail[] = [
  {
    id: "agent",
    name: "1. Autonomous AI Agent",
    subhead: "Natural Language Dialogue",
    icon: Bot,
    color: "from-blue-600 to-indigo-600",
    tag: "ROLE CONTEXT",
    description:
      "Specialized AI agents (Shopping, Procurement Sub-Agent, Customer Support) formulate tool calls via OpenAI/Anthropic/Gemini adapters.",
    securityGuarantee: "Credentials and raw keys are strictly isolated from agent prompts.",
  },
  {
    id: "mandate",
    name: "2. Financial Mandate",
    subhead: "Authority Contract",
    icon: ShieldCheck,
    color: "from-indigo-600 to-purple-600",
    tag: "AUTHORITY BOUND",
    description:
      "Declares what the agent is authorized to spend: per-operation ceiling (e.g. ₹25k), aggregate budget limit, currency, allowed operations allowlist, and valid timeframe.",
    securityGuarantee: "Sub-agents operate under delegated sub-mandates with strict non-escalation invariants.",
  },
  {
    id: "policy",
    name: "3. Deterministic Policy Engine",
    subhead: "Pre-Flight Enforcement",
    icon: Sliders,
    color: "from-purple-600 to-pink-600",
    tag: "8 DETERMINISTIC RULES",
    description:
      "Evaluates 8 in-memory rules synchronously in <15ms. Emits strict ALLOW, DENY, or REQUIRE_HUMAN_REVIEW decision.",
    securityGuarantee: "Zero-Gateway-Dispatch Invariant: On DENY, strictly 0 Razorpay calls are dispatched.",
  },
  {
    id: "mcp",
    name: "4. Razorpay MCP Gateway",
    subhead: "JSON-RPC 2.0 Security Proxy",
    icon: Terminal,
    color: "from-pink-600 to-rose-600",
    tag: "DYNAMIC FILTERING",
    description:
      "Implements initialize, tools/list, and tools/call. Slashes the 25+ tool surface down to 2-3 whitelisted tools, rejecting unexpected parameter injections.",
    securityGuarantee: "88% to 92% attack surface reduction across all standard agent roles.",
  },
  {
    id: "gateway",
    name: "5. Razorpay REST Client",
    subhead: "Orders, Payments, Links, Refunds",
    icon: CreditCard,
    color: "from-amber-600 to-emerald-600",
    tag: "SANDBOX GATEWAY",
    description:
      "Executes authorized operations against Razorpay API (Orders, Payment Links, Captured Payments, Refunds) using merchant credentials held securely by Mandate.",
    securityGuarantee: "Two-Phase Budget Reservation commits funds atomically only upon successful gateway dispatch.",
  },
  {
    id: "webhooks",
    name: "6. HMAC-SHA256 Webhooks",
    subhead: "Event Reliability & DLQ",
    icon: Radio,
    color: "from-emerald-600 to-teal-600",
    tag: "AUTO-CONVERGENCE",
    description:
      "Durable ingestion of order.paid, payment.captured, payment.failed, and refund.processed with cryptographic HMAC verification and idempotency locks.",
    securityGuarantee: "Out-of-order auto-convergence and Dead-Letter Queue (DLQ) guarantee zero double-spend.",
  },
  {
    id: "audit",
    name: "7. Audit Trail & Ledger",
    subhead: "Immutable Forensic Log",
    icon: FileText,
    color: "from-teal-600 to-cyan-600",
    tag: "CRYPTOGRAPHIC PROOF",
    description:
      "Append-only cryptographic event store capturing actor, resource diffs, rule diagnostics, latency, and full trace IDs for enterprise auditing.",
    securityGuarantee: "Every financial operation is 100% reproducible and verifiable end-to-end.",
  },
];

export default function ArchitectureDiagram() {
  const [activeStep, setActiveStep] = useState<string>("policy");

  const selectedDetail = ARCHITECTURE_STEPS.find((s) => s.id === activeStep) || ARCHITECTURE_STEPS[2];

  return (
    <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[#1f293d] pb-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Cpu className="h-5 w-5 text-blue-400" />
            Mandate End-to-End Control Plane Architecture
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            How autonomous AI agents are safely bound to Razorpay financial primitives through deterministic authority contracts.
          </p>
        </div>
        <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-3 py-1 rounded-full border border-emerald-800">
          ● Closed-Loop Verification Pipeline
        </span>
      </div>

      {/* Step Flow Pipeline */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
        {ARCHITECTURE_STEPS.map((step, idx) => {
          const StepIcon = step.icon;
          const isSelected = activeStep === step.id;

          return (
            <button
              key={step.id}
              onClick={() => setActiveStep(step.id)}
              className={`p-3 rounded-xl border text-left transition-all relative flex flex-col justify-between space-y-2 ${
                isSelected
                  ? "bg-blue-600/15 border-blue-500 shadow-lg shadow-blue-500/10 scale-[1.02]"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900"
              }`}
            >
              <div className="flex items-center justify-between">
                <div
                  className={`h-7 w-7 rounded-lg flex items-center justify-center bg-gradient-to-tr ${step.color} text-white shadow-sm`}
                >
                  <StepIcon className="h-3.5 w-3.5" />
                </div>
                <span className="text-[9px] font-mono text-slate-500">#{idx + 1}</span>
              </div>

              <div className="space-y-0.5">
                <p className="text-[11px] font-bold text-white tracking-tight leading-tight">{step.name.split(". ")[1]}</p>
                <p className="text-[9px] text-slate-400 font-mono truncate">{step.subhead}</p>
              </div>

              <span
                className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  isSelected
                    ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                    : "bg-slate-800 text-slate-400"
                }`}
              >
                {step.tag}
              </span>
            </button>
          );
        })}
      </div>

      {/* Selected Step Deep Dive */}
      <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-3 font-sans text-xs">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-sm">{selectedDetail.name}</span>
            <span className="text-slate-400 font-mono">({selectedDetail.subhead})</span>
          </div>
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-950/80 text-blue-300 border border-blue-800">
            {selectedDetail.tag}
          </span>
        </div>

        <p className="text-slate-300 leading-relaxed text-xs">{selectedDetail.description}</p>

        <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-emerald-300 flex items-start gap-2 text-xs">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-white">Security Guarantee: </strong>
            <span className="text-emerald-200">{selectedDetail.securityGuarantee}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
