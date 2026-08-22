"use client";

import React from "react";
import { CreditCard, Terminal, Radio, ShieldCheck, Box } from "lucide-react";

interface IntegrationBadgeProps {
  type: "razorpay_rest" | "razorpay_mcp" | "hmac_webhook" | "policy_engine" | "sandbox";
}

export default function IntegrationBadge({ type }: IntegrationBadgeProps) {
  if (type === "razorpay_rest") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-300 text-[11px] font-mono">
        <CreditCard className="h-3.5 w-3.5 text-blue-400" />
        <span>Razorpay REST API (v1/orders, v1/payments)</span>
      </span>
    );
  }

  if (type === "razorpay_mcp") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-[11px] font-mono">
        <Terminal className="h-3.5 w-3.5 text-indigo-400" />
        <span>Razorpay MCP JSON-RPC 2.0 Gateway</span>
      </span>
    );
  }

  if (type === "hmac_webhook") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[11px] font-mono">
        <Radio className="h-3.5 w-3.5 text-emerald-400" />
        <span>HMAC-SHA256 Webhook Ingestion</span>
      </span>
    );
  }

  if (type === "policy_engine") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-300 text-[11px] font-mono">
        <ShieldCheck className="h-3.5 w-3.5 text-purple-400" />
        <span>Deterministic Policy Engine (8 Rules)</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-mono">
      <Box className="h-3.5 w-3.5 text-amber-400" />
      <span>Razorpay Test Mode / Sandbox</span>
    </span>
  );
}
