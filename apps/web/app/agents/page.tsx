import React from "react";
import { Bot, Key, Plus, ShieldAlert } from "lucide-react";

export default function AgentsPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">AI Agent Registry</h1>
          <p className="text-sm text-slate-400">
            Registered autonomous identities authorized to request financial actions.
          </p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20">
          <Plus className="h-4 w-4" /> Register New Agent
        </button>
      </div>

      <div className="rounded-xl bg-[#111827] border border-[#1f293d] overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900/60 text-slate-400 text-xs uppercase font-mono border-b border-[#1f293d]">
            <tr>
              <th className="px-6 py-4">Agent Identity</th>
              <th className="px-6 py-4">Owner Principal</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">API Key Hash</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1f293d] text-slate-300">
            {[
              { id: "ag_01", name: "Procurement Agent", owner: "Engineering Org (Admin)", status: "ACTIVE", hash: "sha256:8f4c...91a2" },
              { id: "ag_02", name: "Customer Support Refund Bot", owner: "Support Ops", status: "ACTIVE", hash: "sha256:3a1b...77e4" },
              { id: "ag_03", name: "Subscription Billing Worker", owner: "Finance System", status: "ACTIVE", hash: "sha256:9c0d...55f8" },
            ].map((agent) => (
              <tr key={agent.id} className="hover:bg-slate-800/20">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-blue-400" />
                    </div>
                    <div>
                      <div className="font-medium text-white">{agent.name}</div>
                      <div className="text-xs font-mono text-slate-500">{agent.id}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-400">{agent.owner}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    {agent.status}
                  </span>
                </td>
                <td className="px-6 py-4 font-mono text-xs text-slate-500">{agent.hash}</td>
                <td className="px-6 py-4 text-right">
                  <button className="text-xs text-blue-400 hover:text-blue-300 font-medium">Manage</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
