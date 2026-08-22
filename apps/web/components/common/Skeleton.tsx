"use client";

import React from "react";

export function SkeletonCard() {
  return (
    <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-3 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-4 w-24 bg-slate-800 rounded"></div>
        <div className="h-4 w-6 bg-slate-800 rounded-full"></div>
      </div>
      <div className="h-8 w-32 bg-slate-800 rounded"></div>
      <div className="h-3 w-48 bg-slate-800 rounded"></div>
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 animate-pulse">
      <div className="h-6 w-48 bg-slate-800 rounded"></div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-3 py-2 border-b border-slate-800/60">
            {Array.from({ length: cols }).map((_, j) => (
              <div key={j} className="h-4 bg-slate-800 rounded flex-1"></div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
