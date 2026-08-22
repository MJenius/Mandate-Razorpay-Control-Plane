"use client";

import React, { useState, useEffect } from "react";
import {
  ShoppingBag,
  ShieldCheck,
  Terminal,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Bot,
  DollarSign,
  Send,
  Layers,
  Code,
  Zap,
  Lock,
  Cpu,
  AlertTriangle,
  Play,
} from "lucide-react";
import { api, MCPRegistryResponse, Agent } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import IntegrationBadge from "@/components/common/IntegrationBadge";
import { useToast } from "@/components/common/Toast";
import { SkeletonCard } from "@/components/common/Skeleton";
import ErrorState from "@/components/common/ErrorState";

export default function CommercePage() {
  const toast = useToast();
  const [registry, setRegistry] = useState<MCPRegistryResponse | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // MCP Tester state
  const [selectedAgentId, setSelectedAgentId] = useState<string>("agt_shopping_parent_01");
  const [selectedMethod, setSelectedMethod] = useState<"initialize" | "tools/list" | "tools/call">("tools/call");
  const [selectedToolName, setSelectedToolName] = useState<string>("payments_create_order");
  const [toolAmountInr, setToolAmountInr] = useState<number>(6500); // ₹6,500
  const [toolDescription, setToolDescription] = useState<string>("Keychron K2 Mechanical Keyboard");
  const [callingMcp, setCallingMcp] = useState(false);
  const [mcpResponse, setMcpResponse] = useState<Record<string, unknown> | null>(null);

  const loadMcpData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [regData, agentsData] = await Promise.all([
        api.getMcpRegistry(),
        api.getAgents(),
      ]);

      setRegistry(regData);
      setAgents(agentsData);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load Razorpay MCP registry");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMcpData();
  }, []);

  const handleExecuteMcpCall = async () => {
    setCallingMcp(true);
    setMcpResponse(null);
    try {
      let params: Record<string, unknown> = {};

      if (selectedMethod === "tools/call") {
        if (selectedToolName === "payments_create_order") {
          params = {
            name: "payments_create_order",
            arguments: {
              amount: Math.round(toolAmountInr * 100),
              currency: "INR",
              receipt: `rcpt_mcp_${Date.now().toString().slice(-6)}`,
            },
          };
        } else if (selectedToolName === "payments_create_payment_link") {
          params = {
            name: "payments_create_payment_link",
            arguments: {
              amount: Math.round(toolAmountInr * 100),
              currency: "INR",
              description: toolDescription,
              customer_name: "Customer Alice",
              customer_email: "alice@example.com",
            },
          };
        } else if (selectedToolName === "payments_fetch_order") {
          params = {
            name: "payments_fetch_order",
            arguments: { order_id: "order_mock_demo_01" },
          };
        } else if (selectedToolName === "payouts_create") {
          params = {
            name: "payouts_create",
            arguments: {
              account_number: "201004928192",
              fund_account_id: "fa_mock_99",
              amount: Math.round(toolAmountInr * 100),
              currency: "INR",
              mode: "IMPS",
              purpose: "unauthorized_disbursement",
            },
          };
        }
      }

      const res = await api.callMcpGateway(selectedAgentId, selectedMethod, params);
      setMcpResponse(res);

      if (res.error) {
        toast.warning("JSON-RPC Error", res.error.message);
      } else if (res.result && (res.result as Record<string, unknown>).isError) {
        toast.warning("Mandate Policy Rejected", "Operation was blocked by Policy Engine.");
      } else {
        toast.success("MCP Success", `Executed ${selectedMethod} through Mandate Gateway.`);
      }
    } catch (err: unknown) {
      toast.error("MCP Gateway Error", err instanceof Error ? err.message : String(err));
    } finally {
      setCallingMcp(false);
    }
  };

  const totalTools = registry?.total_registered_tools || 25;
  const shoppingReduction = registry?.profiles_summary?.shopping_agent?.attack_surface_reduction_pct || 88.0;
  const procurementReduction = registry?.profiles_summary?.procurement_agent?.attack_surface_reduction_pct || 92.0;
  const supportReduction = registry?.profiles_summary?.support_agent?.attack_surface_reduction_pct || 88.0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="Razorpay MCP Security Gateway & Agentic Commerce"
        icon={ShoppingBag}
        architecturePhase="Stage 4: JSON-RPC 2.0 Model Context Protocol Gateway"
        description="Connects AI agents to Razorpay APIs via the Model Context Protocol (MCP). Mandate acts as a security proxy that dynamically filters tool surfaces based on active financial mandates, enforces strict schema validation, isolates merchant credentials, and routes mutating tools through the Policy Engine."
        lastUpdated={lastUpdated}
        isLoading={loading}
        onRefresh={loadMcpData}
      />

      {error && <ErrorState message={error} onRetry={loadMcpData} isRetrying={loading} />}

      {/* Attack Surface Reduction Metrics Strip (Backend Derived) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span className="uppercase">Total MCP Tool Catalog</span>
            <Terminal className="h-4 w-4 text-blue-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-white">{totalTools} Tools</p>
          <span className="text-[11px] text-slate-400 font-mono">8 Functional Domains (Razorpay & RazorpayX)</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span className="uppercase">Shopping Agent Filter</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">{shoppingReduction}% Reduction</p>
          <span className="text-[11px] text-slate-400 font-mono">3 / {totalTools} Tools Exposed (Orders & Links)</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span className="uppercase">Procurement Sub-Agent</span>
            <ShieldCheck className="h-4 w-4 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-indigo-400">{procurementReduction}% Reduction</p>
          <span className="text-[11px] text-slate-400 font-mono">2 / {totalTools} Tools Exposed (Orders only)</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-1.5 shadow-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span className="uppercase">Customer Support Agent</span>
            <ShieldCheck className="h-4 w-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-purple-400">{supportReduction}% Reduction</p>
          <span className="text-[11px] text-slate-400 font-mono">3 / {totalTools} Tools Exposed (Refunds & Inquiries)</span>
        </div>
      </div>

      {/* Side-by-Side Architectural Comparison: Direct MCP vs Mandate Protected */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Direct MCP (Vulnerable) */}
        <div className="rounded-2xl bg-[#111827] border border-rose-500/30 p-6 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-rose-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="h-5 w-5 text-rose-400" />
              <h3 className="font-bold text-white text-sm">Direct Unprotected Razorpay MCP</h3>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
              UNCONSTRAINED RISK
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            Standard MCP architectures provide the AI agent with raw credentials and expose all {totalTools} tool definitions in the system prompt.
          </p>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-900/50 text-rose-300 flex items-start gap-2.5">
              <XCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-white block font-sans">Credential & Surface Exposure:</strong>
                <span className="text-[11px] text-rose-300 font-sans">
                  Agent holds full merchant keys; prompt injection can invoke privileged <code className="text-rose-400">payouts_create</code> or unlimited refunds.
                </span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-900/50 text-rose-300 flex items-start gap-2.5">
              <XCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-white block font-sans">0 Budget Controls & Race Conditions:</strong>
                <span className="text-[11px] text-rose-300 font-sans">
                  No per-operation caps or two-phase budget reservation. Concurrent agents can drain merchant balances.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Mandate-Protected MCP (Secure) */}
        <div className="rounded-2xl bg-[#111827] border border-blue-500/40 p-6 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-blue-500/20 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-blue-400" />
              <h3 className="font-bold text-white text-sm">Mandate-Protected MCP Security Gateway</h3>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              BOUNDED AGENTIC COMMERCE
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            AI agents connect strictly to Mandate&apos;s JSON-RPC 2.0 proxy. Mandate holds credentials safely, dynamically slashes tool surfaces, and evaluates the Policy Engine synchronously.
          </p>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-900/50 text-emerald-300 flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-white block font-sans">Dynamic Tool Filtering & Schema Validation:</strong>
                <span className="text-[11px] text-emerald-200 font-sans">
                  Slashes 88%–92% of attack surface. Rejects unexpected parameter injections with strict JSON-RPC error codes.
                </span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-900/50 text-emerald-300 flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-white block font-sans">Zero-Gateway-Dispatch Guarantee:</strong>
                <span className="text-[11px] text-emerald-200 font-sans">
                  Two-phase atomic CAS reservation commits spend only upon successful policy approval and Razorpay sandbox execution.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive JSON-RPC 2.0 MCP Gateway Tester */}
      <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 shadow-xl space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[#1f293d] pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Terminal className="h-4 w-4 text-indigo-400" />
              <span>Interactive JSON-RPC 2.0 MCP Gateway Console</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Send raw MCP protocol requests (initialize, tools/list, tools/call) and inspect live protocol responses.
            </p>
          </div>
          <IntegrationBadge type="razorpay_mcp" />
        </div>

        {/* Console Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-sans">
          <div>
            <label className="text-slate-400 block mb-1 font-mono">Authenticated Caller (X-Agent-Id)</label>
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-slate-400 block mb-1 font-mono">MCP Protocol Method</label>
            <select
              value={selectedMethod}
              onChange={(e) => setSelectedMethod(e.target.value as any)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
            >
              <option value="tools/call">tools/call (Execute Financial Tool)</option>
              <option value="tools/list">tools/list (Inspect Filtered Tools)</option>
              <option value="initialize">initialize (Protocol Handshake)</option>
            </select>
          </div>

          {selectedMethod === "tools/call" && (
            <>
              <div>
                <label className="text-slate-400 block mb-1 font-mono">Target Tool Name</label>
                <select
                  value={selectedToolName}
                  onChange={(e) => setSelectedToolName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                >
                  <option value="payments_create_order">payments_create_order (Order)</option>
                  <option value="payments_create_payment_link">payments_create_payment_link (Link)</option>
                  <option value="payments_fetch_order">payments_fetch_order (Read-Only)</option>
                  <option value="payouts_create">payouts_create (Restricted Bank Payout)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1 font-mono">Amount (₹ INR)</label>
                <input
                  type="number"
                  value={toolAmountInr}
                  onChange={(e) => setToolAmountInr(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                />
              </div>
            </>
          )}
        </div>

        {/* Action Button */}
        <div className="flex justify-end pt-1">
          <button
            onClick={handleExecuteMcpCall}
            disabled={callingMcp}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-blue-600/20 disabled:opacity-50"
          >
            <Send className={`h-3.5 w-3.5 ${callingMcp ? "animate-spin" : ""}`} />
            <span>{callingMcp ? "Dispatching MCP JSON-RPC..." : "Dispatch MCP Gateway Call"}</span>
          </button>
        </div>

        {/* Live MCP JSON-RPC Response View */}
        {mcpResponse && (
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between text-slate-400 text-[11px] border-b border-slate-800 pb-2">
              <span>JSON-RPC 2.0 Response Inspector</span>
              <span className="text-emerald-400">Status 200 OK</span>
            </div>
            <pre className="text-[11px] text-emerald-300 p-2 rounded-lg bg-black/60 overflow-x-auto max-h-80 leading-relaxed">
              {JSON.stringify(mcpResponse, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
