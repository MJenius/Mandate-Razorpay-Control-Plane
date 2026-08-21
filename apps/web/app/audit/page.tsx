"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  Shield,
  User,
  Bot,
  Clock,
  RefreshCcw,
  Search,
  Filter,
  Layers,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { api, AuditEvent } from "../../lib/api";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [actorFilter, setActorFilter] = useState<string>("ALL");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuditLogs(100);
      setEvents(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs from API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const filteredEvents = events.filter((e) => {
    const matchesSearch =
      searchFilter === "" ||
      e.action.toLowerCase().includes(searchFilter.toLowerCase()) ||
      e.actor_id.toLowerCase().includes(searchFilter.toLowerCase()) ||
      e.resource_id.toLowerCase().includes(searchFilter.toLowerCase()) ||
      JSON.stringify(e.payload).toLowerCase().includes(searchFilter.toLowerCase());

    const matchesActor =
      actorFilter === "ALL" ||
      (actorFilter === "AGENT" && e.actor_type === "AGENT") ||
      (actorFilter === "SYSTEM" && e.actor_type === "SYSTEM") ||
      (actorFilter === "PRINCIPAL" && e.actor_type === "PRINCIPAL");

    return matchesSearch && matchesActor;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <FileText className="h-6 w-6 text-indigo-400" />
            Immutable Audit Trail & Ledger Stream
          </h1>
          <p className="text-sm text-slate-400">
            Append-only, cryptographically auditable log stream of all agent operations, mandate updates, and policy evaluations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadAuditLogs}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh Stream
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 bg-[#111827] border border-[#1f293d] p-3.5 rounded-2xl">
        <div className="relative flex-1">
          <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Search by Action, Actor ID, Resource ID, or Payload..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Actor:</span>
          {(["ALL", "AGENT", "PRINCIPAL", "SYSTEM"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setActorFilter(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors ${
                actorFilter === t
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Audit Logs Table / Stream */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-4 shadow-xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3 text-xs text-slate-400">
          <span>Displaying verified cryptographic audit entries</span>
          <span className="font-mono">
            {filteredEvents.length} of {events.length} Events
          </span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono animate-pulse">
            Querying immutable audit ledger...
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono space-y-2">
            <Layers className="h-8 w-8 text-slate-700 mx-auto" />
            <div>No matching audit records found.</div>
          </div>
        ) : (
          <div className="divide-y divide-[#1f293d]">
            {filteredEvents.map((event) => {
              const isExpanded = expandedId === event.id;

              return (
                <div key={event.id} className="py-3.5 space-y-2">
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : event.id)}
                    className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 cursor-pointer hover:bg-slate-900/30 p-2 rounded-xl transition-colors"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2 font-mono">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                            event.action.includes("COMMITTED") || event.action.includes("APPROVED")
                              ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                              : event.action.includes("REJECTED") || event.action.includes("REVOKED")
                              ? "bg-rose-950 text-rose-300 border-rose-800"
                              : "bg-blue-950 text-blue-300 border-blue-800"
                          }`}
                        >
                          {event.action}
                        </span>
                        <span className="text-[11px] text-slate-500">{event.event_id}</span>
                        <span className="text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                          {event.actor_type}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-slate-300 font-mono">
                        <span>
                          Actor: <strong className="text-white">{event.actor_id}</strong>
                        </span>
                        <span>
                          Resource: <strong className="text-indigo-400">{event.resource_id}</strong>
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-right">
                      <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-slate-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-500" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Payload & State Transition Inspector */}
                  {isExpanded && (
                    <div className="mt-2 p-3.5 rounded-xl bg-black/60 border border-slate-800 space-y-2 font-mono text-[11px]">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <span className="text-slate-400 block mb-1 font-bold">Event Payload:</span>
                          <pre className="text-[10px] text-emerald-400 bg-slate-950 p-2.5 rounded-lg overflow-x-auto max-h-48">
                            {JSON.stringify(event.payload, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <span className="text-slate-400 block mb-1 font-bold">State Transition:</span>
                          <pre className="text-[10px] text-indigo-300 bg-slate-950 p-2.5 rounded-lg overflow-x-auto max-h-48">
                            {JSON.stringify(
                              {
                                previous_state: event.previous_state,
                                new_state: event.new_state,
                              },
                              null,
                              2
                            )}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
