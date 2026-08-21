import React from "react";
import { FileText, Shield, User, Bot, Clock } from "lucide-react";

export default function AuditPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Immutable Audit Trail</h1>
        <p className="text-sm text-slate-400">
          Cryptographically auditable log stream of all agent operations, mandate updates, and policy evaluations.
        </p>
      </div>

      <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3 text-xs text-slate-400">
          <span>Displaying latest system events</span>
          <span className="font-mono">Total Events: 1,429</span>
        </div>

        <div className="divide-y divide-[#1f293d]">
          {[
            { id: "aud_7109a", action: "POLICY_EVALUATED", actor: "ag_01 (Procurement)", resource: "op_49fa02", status: "APPROVED", time: "2 mins ago", detail: "Amount bound and valid mandate verified." },
            { id: "aud_71099", action: "OPERATION_REQUESTED", actor: "ag_01 (Procurement)", resource: "op_49fa02", status: "INITIATED", time: "2 mins ago", detail: "Requested CREATE_ORDER for ₹ 15,000" },
            { id: "aud_71098", action: "MANDATE_ISSUED", actor: "usr_admin_01", resource: "mnd_procure_q3", status: "ACTIVE", time: "3 hours ago", detail: "Issued limit ₹ 1,00,000 to ag_01" },
            { id: "aud_71097", action: "AGENT_REGISTERED", actor: "usr_admin_01", resource: "ag_01", status: "CREATED", time: "5 hours ago", detail: "Registered agent identity with API key hash." },
          ].map((event) => (
            <div key={event.id} className="py-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">
                    {event.action}
                  </span>
                  <span className="text-xs font-mono text-slate-500">{event.id}</span>
                </div>
                <p className="text-sm text-slate-200">{event.detail}</p>
                <div className="flex items-center gap-4 text-xs text-slate-400">
                  <span>Actor: <strong className="text-slate-300 font-mono">{event.actor}</strong></span>
                  <span>Resource: <strong className="text-slate-300 font-mono">{event.resource}</strong></span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-500 flex items-center gap-1 sm:justify-end">
                  <Clock className="h-3 w-3" /> {event.time}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
