"use client";

import React from "react";
import { AlertTriangle, ShieldAlert, X } from "lucide-react";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  isDestructive = true,
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-150">
        <div className="flex items-start gap-3.5">
          <div
            className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 border ${
              isDestructive
                ? "bg-rose-950/60 border-rose-800/80 text-rose-400"
                : "bg-blue-950/60 border-blue-800/80 text-blue-400"
            }`}
          >
            {isDestructive ? (
              <AlertTriangle className="h-5 w-5" />
            ) : (
              <ShieldAlert className="h-5 w-5" />
            )}
          </div>

          <div className="flex-1 space-y-1">
            <h3 className="text-sm font-bold text-white tracking-tight">{title}</h3>
            <p className="text-xs text-slate-300 leading-relaxed font-sans">{description}</p>
          </div>

          <button
            onClick={onCancel}
            disabled={isLoading}
            className="text-slate-500 hover:text-white p-1 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#1f293d]">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 rounded-xl text-xs font-semibold text-white transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50 ${
              isDestructive
                ? "bg-rose-600 hover:bg-rose-500 shadow-rose-600/20"
                : "bg-blue-600 hover:bg-blue-500 shadow-blue-600/20"
            }`}
          >
            {isLoading && (
              <span className="h-3 w-3 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            )}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
