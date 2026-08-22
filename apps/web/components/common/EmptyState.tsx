"use client";

import React from "react";
import { Layers, ShieldCheck, Plus, RefreshCcw } from "lucide-react";

interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
}

export default function EmptyState({
  icon: Icon = Layers,
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
}: EmptyStateProps) {
  return (
    <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-12 text-center space-y-4 shadow-xl">
      <div className="h-12 w-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500 shadow-inner">
        <Icon className="h-6 w-6 text-slate-400" />
      </div>
      <div className="space-y-1 max-w-md mx-auto">
        <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
        <p className="text-xs text-slate-400 leading-relaxed font-sans">{description}</p>
      </div>

      {(onAction || onSecondaryAction) && (
        <div className="flex items-center justify-center gap-2.5 pt-2">
          {onSecondaryAction && secondaryActionLabel && (
            <button
              onClick={onSecondaryAction}
              className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition-colors"
            >
              {secondaryActionLabel}
            </button>
          )}
          {onAction && actionLabel && (
            <button
              onClick={onAction}
              className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 px-4 py-2 text-xs font-semibold text-white transition-all shadow-md shadow-blue-600/20"
            >
              {actionLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
