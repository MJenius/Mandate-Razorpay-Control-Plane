"use client";

import React, { useState, useEffect } from "react";
import {
  FileText,
  ShieldCheck,
  Search,
  RefreshCcw,
  Layers,
  ArrowRight,
  Filter,
  CheckCircle2,
  Lock,
  Clock,
  Terminal,
} from "lucide-react";
import { api, AuditEvent } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import { SkeletonTable } from "@/components/common/Skeleton";
import EmptyState from "@/components/common/EmptyState";
import ErrorState from "@/components/common/ErrorState";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [actorFilter, setActorFilter] = useState<string>("ALL");
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuditLogs(100);
      setEvents(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const filteredEvents = events.filter((e) => {
    const matchesSearch =
      searchQuery === "" ||
      e.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.actor_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.resource_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.event_id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesActor =
      actorFilter === "ALL" || e.actor_type.toUpperCase() === actorFilter;

    return matchesSearch && matchesActor;
  });

  const totalPages = Math.ceil(filteredEvents.length / pageSize) || 1;
  const paginatedEvents = filteredEvents.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="Immutable Cryptographic Audit Trail"
        icon={FileText}
        architecturePhase="Stage 7: Forensic Audit Trail & Ledger Proofs"
        description="Append-only cryptographic event stream tracking all mutations to financial mandates, AI agent execution decisions, two-phase budget locks, and asynchronous Razorpay webhook settlements for compliance and forensic analysis."
        lastUpdated={lastUpdated}
        isLoading={loading}
        onRefresh={loadAuditLogs}
      />

      {error && <ErrorState message={error} onRetry={loadAuditLogs} isRetrying={loading} />}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-3 bg-[#111827] border border-[#1f293d] p-4 rounded-2xl shadow-xl">
        <div className="relative flex-1">
          <Search className="h-4 w-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search by Action, Actor ID, Resource ID, Event ID..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Actor:</span>
          {(["ALL", "AGENT", "PRINCIPAL", "SYSTEM"] as const).map((a) => (
            <button
              key={a}
              onClick={() => {
                setActorFilter(a);
                setCurrentPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                actorFilter === a
                  ? "bg-blue-600 text-white font-bold shadow-sm"
                  : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {/* Audit Stream Table */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] border-b border-[#1f293d]">
              <tr>
                <th className="px-5 py-3.5">Action Event</th>
                <th className="px-5 py-3.5">Actor</th>
                <th className="px-5 py-3.5">Resource Target</th>
                <th className="px-5 py-3.5">Timestamp</th>
                <th className="px-5 py-3.5 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f293d] text-slate-300 font-mono">
              {loading && events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-slate-500 text-xs">
                    Streaming cryptographic audit events from PostgreSQL...
                  </td>
                </tr>
              ) : paginatedEvents.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-slate-500 text-xs">
                    No matching audit events found.
                  </td>
                </tr>
              ) : (
                paginatedEvents.map((evt) => (
                  <tr key={evt.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-5 py-3.5 font-bold text-white text-xs flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
                      <span>{evt.action}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-blue-300 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 text-[10px]">
                        {evt.actor_type}: {evt.actor_id}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">
                      <div>{evt.resource_id}</div>
                      <div className="text-[10px] text-slate-500">{evt.resource_type}</div>
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-[11px]">
                      {new Date(evt.timestamp).toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => setSelectedEvent(evt)}
                        className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium transition-colors"
                      >
                        Inspect Diff →
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {filteredEvents.length > pageSize && (
          <div className="p-4 border-t border-[#1f293d] bg-slate-900/60 flex items-center justify-between text-xs font-mono text-slate-400">
            <span>
              Showing {(currentPage - 1) * pageSize + 1}–
              {Math.min(currentPage * pageSize, filteredEvents.length)} of {filteredEvents.length} Events
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50"
              >
                Previous
              </button>
              <span>Page {currentPage} of {totalPages}</span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Audit State Diff Inspector Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <div>
                <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                  <span>Audit Event Inspector</span>
                </h2>
                <span className="text-[11px] text-slate-400 font-mono">
                  Event ID: {selectedEvent.event_id} · Action: {selectedEvent.action}
                </span>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* Metadata Badges */}
            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 text-[10px] block font-sans">Actor Information</span>
                <div className="text-white font-bold">{selectedEvent.actor_id}</div>
                <div className="text-blue-400 text-[10px]">Type: {selectedEvent.actor_type}</div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-slate-500 text-[10px] block font-sans">Resource Information</span>
                <div className="text-white font-bold">{selectedEvent.resource_id}</div>
                <div className="text-indigo-400 text-[10px]">Type: {selectedEvent.resource_type}</div>
              </div>
            </div>

            {/* State Diffs (Previous State vs New State) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
              <div className="space-y-1">
                <span className="text-slate-400 font-bold block text-[11px]">Previous State:</span>
                <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[10px] text-slate-400 overflow-x-auto max-h-48">
                  {selectedEvent.previous_state
                    ? JSON.stringify(selectedEvent.previous_state, null, 2)
                    : "// Initial Creation State (Null)"}
                </pre>
              </div>

              <div className="space-y-1">
                <span className="text-slate-400 font-bold block text-[11px]">New State:</span>
                <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[10px] text-emerald-300 overflow-x-auto max-h-48">
                  {selectedEvent.new_state
                    ? JSON.stringify(selectedEvent.new_state, null, 2)
                    : "// No State Transition Payload"}
                </pre>
              </div>
            </div>

            {/* Event Payload */}
            <div className="space-y-1 font-mono text-xs">
              <span className="text-slate-400 font-bold block text-[11px]">Event Payload:</span>
              <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[10px] text-indigo-300 overflow-x-auto max-h-36">
                {JSON.stringify(selectedEvent.payload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
