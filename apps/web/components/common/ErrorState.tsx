"use client";

import React from "react";
import { AlertCircle, RefreshCcw, WifiOff } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export default function ErrorState({
  title = "Connection or Evaluation Error",
  message = "Failed to synchronize state with the Mandate control plane API.",
  onRetry,
  isRetrying = false,
}: ErrorStateProps) {
  return (
    <div className="rounded-2xl bg-rose-950/20 border border-rose-900/50 p-8 text-center space-y-4 shadow-xl">
      <div className="h-12 w-12 rounded-2xl bg-rose-950/60 border border-rose-800/80 flex items-center justify-center mx-auto text-rose-400">
        <WifiOff className="h-6 w-6" />
      </div>
      <div className="space-y-1 max-w-md mx-auto">
        <h3 className="text-sm font-bold text-white">{title}</h3>
        <p className="text-xs text-rose-300/90 leading-relaxed font-sans">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          disabled={isRetrying}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md shadow-rose-600/20 transition-all disabled:opacity-50"
        >
          <RefreshCcw className={`h-3.5 w-3.5 ${isRetrying ? "animate-spin" : ""}`} />
          <span>{isRetrying ? "Reconnecting..." : "Retry Request"}</span>
        </button>
      )}
    </div>
  );
}
