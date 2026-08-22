"use client";

import React from "react";
import { CheckCircle2, XCircle, Clock, AlertTriangle, Ban, Lock, Play } from "lucide-react";

interface StatusBadgeProps {
  status: string;
  type?: "mandate" | "operation" | "policy" | "agent" | "generic";
  size?: "sm" | "md";
}

export default function StatusBadge({ status, type = "generic", size = "sm" }: StatusBadgeProps) {
  const normalized = (status || "").toUpperCase();

  let style = "bg-slate-900 text-slate-300 border-slate-800";
  let Icon: React.ComponentType<{ className?: string }> = Clock;

  if (["ACTIVE", "SUCCEEDED", "ALLOW", "CAPTURED", "COMMITTED", "PROCESSED"].includes(normalized)) {
    style = "bg-emerald-950/60 text-emerald-300 border-emerald-800/80";
    Icon = CheckCircle2;
  } else if (
    [
      "REVOKED",
      "FAILED",
      "DENY",
      "POLICY_REJECTED",
      "CANCELLED",
      "DEAD_LETTER",
      "EXHAUSTED",
    ].includes(normalized)
  ) {
    style = "bg-rose-950/60 text-rose-300 border-rose-800/80";
    Icon = XCircle;
  } else if (
    ["SUSPENDED", "REQUIRES_APPROVAL", "REQUIRE_HUMAN_REVIEW", "PENDING_APPROVAL"].includes(
      normalized
    )
  ) {
    style = "bg-amber-950/60 text-amber-300 border-amber-800/80";
    Icon = AlertTriangle;
  } else if (["RESERVED", "EXECUTING", "INITIATED", "PROCESSING", "AUTHORIZED"].includes(normalized)) {
    style = "bg-blue-950/60 text-blue-300 border-blue-800/80";
    Icon = Clock;
  }

  const padding = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";
  const iconSize = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md font-mono font-bold border transition-colors ${padding} ${style}`}
    >
      <Icon className={`${iconSize} shrink-0`} />
      <span>{normalized.replace(/_/g, " ")}</span>
    </span>
  );
}
