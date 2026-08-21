"use client";

import React, { useState } from "react";
import {
  Sliders,
  ShieldCheck,
  Check,
  Plus,
  Trash2,
  AlertCircle,
  ToggleLeft,
  ToggleRight,
  Info,
} from "lucide-react";

interface PolicyRuleItem {
  id: string;
  name: string;
  code: string;
  desc: string;
  active: boolean;
  priority: number;
  category: string;
}

export default function PoliciesPage() {
  const [rules, setRules] = useState<PolicyRuleItem[]>([
    {
      id: "rule_1",
      name: "Mandate Validity & Expiry Check",
      code: "MANDATE_VALIDITY_CHECK",
      desc: "Ensures caller holds an ACTIVE mandate that has not reached expiry or suspension.",
      active: true,
      priority: 10,
      category: "Lifecycle & Authority",
    },
    {
      id: "rule_2",
      name: "Per-Operation & Aggregate Budget Cap",
      code: "AMOUNT_BOUND_CHECK",
      desc: "Enforces single-operation caps and total aggregate remaining budget with two-phase CAS reservations.",
      active: true,
      priority: 20,
      category: "Financial Bounds",
    },
    {
      id: "rule_3",
      name: "Operation Type Allowlist Verification",
      code: "ALLOWED_OPERATION_TYPE_CHECK",
      desc: "Restricts operation types (e.g. Orders, Refunds, Payment Links) to explicit allowlists.",
      active: true,
      priority: 30,
      category: "Tool Permissions",
    },
    {
      id: "rule_4",
      name: "Hierarchical Delegation Ceiling Invariant",
      code: "DELEGATION_CEILING_CHECK",
      desc: "Prevents child delegated mandates from exceeding parent per-op limits, aggregate budget, or validity.",
      active: true,
      priority: 40,
      category: "Hierarchical Delegation",
    },
    {
      id: "rule_5",
      name: "Zero-Gateway-Dispatch Invariant",
      code: "ZERO_GATEWAY_DISPATCH_CHECK",
      desc: "Guarantees 0 Razorpay API calls are dispatched if any policy decision evaluates to DENY.",
      active: true,
      priority: 50,
      category: "Gateway Interception",
    },
  ]);

  const [showModal, setShowModal] = useState(false);
  const [newRuleName, setNewRuleName] = useState("");
  const [newRuleCode, setNewRuleCode] = useState("");
  const [newRuleDesc, setNewRuleDesc] = useState("");
  const [newCategory, setNewCategory] = useState("Custom Rules");

  const handleToggle = (id: string) => {
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r))
    );
  };

  const handleAddRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRuleName || !newRuleCode) return;

    const newRule: PolicyRuleItem = {
      id: `rule_custom_${Date.now()}`,
      name: newRuleName,
      code: newRuleCode.toUpperCase().replace(/\s+/g, "_"),
      desc: newRuleDesc || "Custom user-defined deterministic policy constraint.",
      active: true,
      priority: rules.length * 10 + 10,
      category: newCategory,
    };

    setRules((prev) => [...prev, newRule]);
    setNewRuleName("");
    setNewRuleCode("");
    setNewRuleDesc("");
    setShowModal(false);
  };

  const handleDeleteRule = (id: string) => {
    setRules((prev) => prev.filter((r) => r.id !== id));
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Sliders className="h-6 w-6 text-blue-400" />
            Deterministic Policy Engine Rules
          </h1>
          <p className="text-sm text-slate-400">
            Pre-flight verification rules evaluated synchronously in memory before any financial gateway dispatch.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 shadow-sm shadow-blue-500/20 transition-colors"
        >
          <Plus className="h-4 w-4" /> Add Custom Rule
        </button>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 space-y-3.5 shadow-xl flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                  {rule.code}
                </span>
                <button
                  onClick={() => handleToggle(rule.id)}
                  className={`text-xs flex items-center gap-1 font-medium transition-colors ${
                    rule.active ? "text-emerald-400" : "text-slate-500"
                  }`}
                >
                  {rule.active ? (
                    <>
                      <Check className="h-3.5 w-3.5" /> Enforced
                    </>
                  ) : (
                    <>
                      <ToggleLeft className="h-3.5 w-3.5" /> Disabled
                    </>
                  )}
                </button>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">
                  {rule.category}
                </span>
                <h3 className="font-semibold text-white text-sm mt-0.5">{rule.name}</h3>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">{rule.desc}</p>
            </div>

            <div className="pt-3 border-t border-[#1f293d] flex items-center justify-between text-[11px] font-mono text-slate-500">
              <span>Priority: #{rule.priority}</span>
              {rule.id.startsWith("rule_custom_") && (
                <button
                  onClick={() => handleDeleteRule(rule.id)}
                  className="text-rose-400 hover:text-rose-300 flex items-center gap-1 font-sans"
                >
                  <Trash2 className="h-3 w-3" /> Remove
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <h2 className="text-base font-semibold text-white">Create Custom Policy Rule</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddRule} className="space-y-3.5 text-xs font-sans">
              <div>
                <label className="text-slate-400 block mb-1">Rule Name</label>
                <input
                  type="text"
                  value={newRuleName}
                  onChange={(e) => setNewRuleName(e.target.value)}
                  placeholder="e.g. Velocity Rate Limiter Check"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-sans focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Rule Code Identifier</label>
                <input
                  type="text"
                  value={newRuleCode}
                  onChange={(e) => setNewRuleCode(e.target.value)}
                  placeholder="e.g. VELOCITY_BURST_RATE_LIMIT"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-sans focus:outline-none focus:border-blue-500"
                >
                  <option value="Risk & Security">Risk & Security</option>
                  <option value="Financial Bounds">Financial Bounds</option>
                  <option value="Tool Permissions">Tool Permissions</option>
                  <option value="Custom Rules">Custom Rules</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Description</label>
                <textarea
                  value={newRuleDesc}
                  onChange={(e) => setNewRuleDesc(e.target.value)}
                  placeholder="Describe the condition and invariant enforced by this rule..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-sans focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#1f293d]">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md"
                >
                  Add Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
