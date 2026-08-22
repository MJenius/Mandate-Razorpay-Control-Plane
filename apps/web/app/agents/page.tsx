"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  Send,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  ShoppingCart,
  RefreshCcw,
  Terminal,
  Activity,
  Layers,
  ArrowRight,
  Cpu,
  HelpCircle,
  Sliders,
  DollarSign,
  AlertTriangle,
  UserCheck,
} from "lucide-react";
import { api, AgentChatResponse, AgentTrace, Agent, Mandate } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import { useToast } from "@/components/common/Toast";

interface ChatMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  toolCalls?: AgentChatResponse["tool_calls"];
  policyDecisions?: AgentChatResponse["policy_decisions"];
  operationIds?: string[];
  latencyMs?: number;
  timestamp: string;
  isError?: boolean;
}

const AGENT_ROLES = [
  {
    id: "agt_shopping_parent_01",
    name: "Primary Shopping Agent",
    type: "SHOPPING",
    icon: ShoppingCart,
    color: "blue",
    description: "Autonomous customer commerce and order orchestrator holding root financial authority.",
    tools: ["browse_catalog", "create_purchase_order", "create_payment_link_for_customer"],
    samplePrompts: [
      "Browse the electronics catalog",
      "Buy 1 Keychron K2 Mechanical Keyboard for Alice",
      "Order 100 Keychron Keyboards for Rs. 6,50,000 (Bulk Escalation Attack)",
      "Issue a customer refund of Rs. 2,500 to pay_attacker_01 (Unauthorized Action)",
    ],
  },
  {
    id: "agt_procurement_child_01",
    name: "Procurement Sub-Agent",
    type: "PROCUREMENT",
    icon: Cpu,
    color: "indigo",
    description: "Delegated sub-agent for accessories and peripherals, operating under a bounded child mandate.",
    tools: ["browse_catalog", "create_purchase_order"],
    samplePrompts: [
      "Procure 1 Keychron K2 Keyboard within delegated bound",
      "Order 5 Dell 4K Monitors for Rs. 3,75,000 (Exceeds Per-Op Ceiling)",
      "Issue refund of Rs. 1,000 (Privilege Escalation Attempt)",
    ],
  },
  {
    id: "agt_support_dispute_01",
    name: "Customer Support Agent",
    type: "SUPPORT",
    icon: HelpCircle,
    color: "purple",
    description: "Handles customer order inspection and bounded refund authorization.",
    tools: ["lookup_transaction", "issue_customer_refund"],
    samplePrompts: [
      "Lookup transaction op_demo_step1",
      "Issue customer refund of Rs. 1,500 for pay_demo_cap_01",
      "Create a purchase order for Rs. 50,000 (Unpermitted for Support Agent)",
    ],
  },
];

export default function AgentsPage() {
  const toast = useToast();
  const [selectedAgentId, setSelectedAgentId] = useState<string>("agt_shopping_parent_01");
  const [agentDetails, setAgentDetails] = useState<Agent | null>(null);
  const [agentMandate, setAgentMandate] = useState<Mandate | null>(null);
  const [sessionId, setSessionId] = useState<string>("sess_init");
  const [mounted, setMounted] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState<string>("");
  const [recentTraces, setRecentTraces] = useState<AgentTrace[]>([]);
  const [loadingTraces, setLoadingTraces] = useState(false);
  const [selectedTrace, setSelectedTrace] = useState<AgentTrace | null>(null);
  const [expandedDiagnostics, setExpandedDiagnostics] = useState<Record<string, boolean>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);

  const activeRole = AGENT_ROLES.find((r) => r.id === selectedAgentId) || AGENT_ROLES[0];

  // Initialize session and welcome message
  useEffect(() => {
    setMounted(true);
    const newSession = `sess_${Date.now()}`;
    setSessionId(newSession);
    setMessages([
      {
        id: "m_welcome",
        sender: "agent",
        text: `Connected to ${activeRole.name}. Ready to process natural language instructions. Tool calls will be intercepted and evaluated by Mandate's Deterministic Policy Engine.`,
        timestamp: "Ready",
      },
    ]);
  }, [selectedAgentId]);

  // Load Agent metadata & active mandate
  const loadAgentContext = async () => {
    try {
      const [agentData, mandatesData] = await Promise.all([
        api.getAgent(selectedAgentId).catch(() => null),
        api.getMandates(selectedAgentId).catch(() => []),
      ]);

      if (agentData) setAgentDetails(agentData);
      if (mandatesData && mandatesData.length > 0) {
        setAgentMandate(mandatesData.find((m) => m.status === "ACTIVE") || mandatesData[0]);
      } else {
        setAgentMandate(null);
      }
    } catch {
      // Ignore
    }
  };

  // Load agent execution traces from PostgreSQL
  const loadTraces = async () => {
    setLoadingTraces(true);
    try {
      const traces = await api.getAgentTraces(selectedAgentId);
      setRecentTraces(traces);
    } catch {
      // Backend may have 0 traces
    } finally {
      setLoadingTraces(false);
    }
  };

  useEffect(() => {
    loadAgentContext();
    loadTraces();
  }, [selectedAgentId]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const toggleDiagnostic = (id: string) => {
    setExpandedDiagnostics((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSendMessage = async (customPrompt?: string) => {
    const promptToSend = customPrompt || inputPrompt;
    if (!promptToSend.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: "user",
      text: promptToSend,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");
    setLoading(true);
    setActiveStep("1. LLM Tool Selection Turn...");

    const historyPayload = messages.slice(-6).map((m) => ({
      role: m.sender === "user" ? "user" : "assistant",
      content: m.text,
    }));

    try {
      setTimeout(() => setActiveStep("2. Intercepting via Deterministic Policy Engine (8 Rules)..."), 200);

      const response = await api.chatWithAgent(
        selectedAgentId,
        promptToSend,
        sessionId,
        historyPayload
      );

      setActiveStep("3. Synchronizing Two-Phase Reservation & Gateway State...");

      const agentMsg: ChatMessage = {
        id: `ag_${Date.now()}`,
        sender: "agent",
        text: response.reply,
        toolCalls: response.tool_calls,
        policyDecisions: response.policy_decisions,
        operationIds: response.operation_ids,
        latencyMs: response.latency_ms,
        timestamp: new Date().toLocaleTimeString(),
      };

      setMessages((prev) => [...prev, agentMsg]);
      await Promise.all([loadTraces(), loadAgentContext()]);
    } catch (err: unknown) {
      const errorText = err instanceof Error ? err.message : "Network error contacting agent backend";
      toast.error("Agent Execution Failed", errorText);

      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: "agent",
        text: `⚠️ Execution Intercepted / Failure: ${errorText}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      setActiveStep("");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="AI Agent Console & Authorization Playground"
        icon={Bot}
        architecturePhase="Stage 1: AI Agent Tool-Calling Runtime"
        description="Interact directly with specialized AI agents in natural language. Every financial action (orders, refunds, payment links) proposed by an LLM is intercepted and evaluated deterministically by Mandate's Policy Gate before touching Razorpay."
        actions={
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 p-1 rounded-xl">
            {AGENT_ROLES.map((role) => {
              const RoleIcon = role.icon;
              const isSelected = selectedAgentId === role.id;
              return (
                <button
                  key={role.id}
                  onClick={() => setSelectedAgentId(role.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isSelected
                      ? "bg-blue-600 text-white shadow-sm font-semibold"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <RoleIcon className="h-3.5 w-3.5" />
                  <span>{role.name}</span>
                </button>
              );
            })}
          </div>
        }
      />

      {/* Active Agent Contract & Capabilities Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Agent Role Summary */}
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono uppercase tracking-wider">Agent Role</span>
            <StatusBadge status={agentDetails?.status || "ACTIVE"} />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm flex items-center gap-2">
              <activeRole.icon className="h-4 w-4 text-blue-400" />
              {activeRole.name}
            </h3>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">{activeRole.description}</p>
          </div>
          <div className="text-[10px] font-mono text-slate-500 pt-1">
            Agent ID: <code className="text-slate-300">{selectedAgentId}</code>
          </div>
        </div>

        {/* Bound Authority Contract */}
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono uppercase tracking-wider">Bound Mandate</span>
            {agentMandate && <StatusBadge status={agentMandate.status} />}
          </div>
          {agentMandate ? (
            <div className="space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-[11px]">Per-Op Ceiling:</span>
                <span className="font-bold text-white">
                  ₹{(agentMandate.max_amount_per_op / 100).toLocaleString("en-IN")}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-[11px]">Aggregate Budget:</span>
                <span className="font-bold text-emerald-400">
                  ₹{(agentMandate.aggregate_spend_limit / 100).toLocaleString("en-IN")}
                </span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800">
                <span>Spent: ₹{(agentMandate.current_aggregate_spend / 100).toLocaleString("en-IN")}</span>
                <span>Depth: {agentMandate.delegation_depth}</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 font-mono">No active mandate found for agent.</p>
          )}
        </div>

        {/* Permitted Operations Allowlist */}
        <div className="p-4 rounded-2xl bg-[#111827] border border-[#1f293d] space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono uppercase tracking-wider">Authorized Tools</span>
            <span className="text-[10px] font-mono text-blue-400">
              {activeRole.tools.length} Tools Whitelisted
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {activeRole.tools.map((t) => (
              <span
                key={t}
                className="px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300"
              >
                {t}
              </span>
            ))}
          </div>
          <p className="text-[10px] text-slate-500 leading-snug">
            All other Razorpay MCP tools (payouts, settlements, bulk refunds) are strictly rejected.
          </p>
        </div>
      </div>

      {/* Main Grid: Interactive Chat Console (2 Cols) + Real Trace Inspector (1 Col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Console */}
        <div className="lg:col-span-2 flex flex-col h-[700px] rounded-2xl bg-[#111827] border border-[#1f293d] shadow-xl overflow-hidden">
          {/* Console Header */}
          <div className="px-5 py-3.5 border-b border-[#1f293d] bg-slate-900/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-mono text-slate-300">
                Connected Agent: <strong className="text-white">{activeRole.name}</strong>
              </span>
            </div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
              <span suppressHydrationWarning>
                Session: {mounted ? `${sessionId.slice(0, 14)}...` : "sess_..."}
              </span>
              <button
                onClick={() => {
                  setMessages([
                    {
                      id: "m_welcome",
                      sender: "agent",
                      text: `Session restarted with ${activeRole.name}. Ready for instructions.`,
                      timestamp: new Date().toLocaleTimeString(),
                    },
                  ]);
                  setSessionId(`sess_${Date.now()}`);
                }}
                className="hover:text-slate-300 p-1 transition-colors"
                title="Restart dialogue session"
              >
                <RefreshCcw className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4 font-sans text-sm">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-3 ${m.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.sender === "agent" && (
                  <div
                    className={`h-8 w-8 rounded-xl border flex items-center justify-center shrink-0 ${
                      m.isError
                        ? "bg-rose-950/60 border-rose-800 text-rose-400"
                        : "bg-blue-950/60 border-blue-800 text-blue-400"
                    }`}
                  >
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] space-y-2 rounded-2xl p-4 ${
                    m.sender === "user"
                      ? "bg-blue-600 text-white rounded-br-none shadow-md"
                      : m.isError
                      ? "bg-rose-950/30 border border-rose-900/50 text-rose-200 rounded-bl-none"
                      : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-sm"
                  }`}
                >
                  <div className="text-xs leading-relaxed whitespace-pre-line">{m.text}</div>

                  {/* Policy Decision & Individual Rule Diagnostics Inspector */}
                  {m.policyDecisions && m.policyDecisions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800 space-y-2.5 font-mono text-[11px]">
                      {m.policyDecisions.map((p, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-xl border flex flex-col gap-2 ${
                            p.decision === "ALLOW"
                              ? "bg-emerald-950/30 border-emerald-800/50 text-emerald-300"
                              : p.decision === "DENY"
                              ? "bg-rose-950/30 border-rose-800/50 text-rose-300"
                              : "bg-amber-950/30 border-amber-800/50 text-amber-300"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold flex items-center gap-1.5">
                              {p.decision === "ALLOW" ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                              ) : (
                                <XCircle className="h-4 w-4 text-rose-400" />
                              )}
                              MANDATE POLICY DECISION: {p.decision}
                            </span>
                            {m.latencyMs && <span>{m.latencyMs}ms</span>}
                          </div>

                          {p.rejection_reasons && p.rejection_reasons.length > 0 && (
                            <div className="text-[10px] text-rose-300 bg-rose-950/60 p-2 rounded-lg border border-rose-900/50 space-y-0.5">
                              <strong className="block text-rose-400">Rejection Cause:</strong>
                              {p.rejection_reasons.map((r, rIdx) => (
                                <div key={rIdx}>• {r}</div>
                              ))}
                            </div>
                          )}

                          {/* Gateway Effect Reference */}
                          <div className="text-[10px] text-slate-300 flex items-center justify-between pt-1 border-t border-black/30">
                            <span>
                              Gateway Effect:{" "}
                              <strong className={p.decision === "ALLOW" ? "text-emerald-400" : "text-rose-400"}>
                                {p.decision === "ALLOW"
                                  ? "Razorpay Test Mode Dispatched"
                                  : "0 Gateway Calls Dispatched (Invariant)"}
                              </strong>
                            </span>
                            {m.operationIds && m.operationIds[idx] && (
                              <span className="text-blue-400">Op: {m.operationIds[idx]}</span>
                            )}
                          </div>

                          {/* Toggle Diagnostic Rules */}
                          {p.rule_diagnostics && p.rule_diagnostics.length > 0 && (
                            <div>
                              <button
                                onClick={() => toggleDiagnostic(m.id)}
                                className="text-[10px] text-blue-400 hover:underline inline-flex items-center gap-1 mt-1"
                              >
                                <span>{expandedDiagnostics[m.id] ? "Hide" : "View"} 8 Rule Diagnostics</span>
                              </button>

                              {expandedDiagnostics[m.id] && (
                                <div className="mt-2 space-y-1 bg-black/60 p-2 rounded-lg text-[9px]">
                                  {p.rule_diagnostics.map((rd) => (
                                    <div key={rd.rule_name} className="flex items-center justify-between py-0.5 border-b border-slate-900">
                                      <span className="text-slate-300">{rd.rule_name}</span>
                                      <span className={rd.passed ? "text-emerald-400" : "text-rose-400"}>
                                        {rd.passed ? "PASS" : "FAIL"} ({rd.latency_ms}ms)
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <div
                    suppressHydrationWarning
                    className={`text-[9px] font-mono text-right ${
                      m.sender === "user" ? "text-blue-200" : "text-slate-500"
                    }`}
                  >
                    {m.timestamp}
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 items-center text-xs text-blue-400 font-mono p-3 bg-blue-950/20 border border-blue-900/30 rounded-xl animate-pulse">
                <Activity className="h-4 w-4 animate-spin" />
                <span>{activeStep || "Evaluating Mandate Policy Gate..."}</span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="px-4 py-2 bg-slate-900/40 border-t border-[#1f293d] flex items-center gap-2 overflow-x-auto">
            <span className="text-[10px] font-mono text-slate-500 shrink-0">Sample Prompts:</span>
            {activeRole.samplePrompts.map((p, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(p)}
                disabled={loading}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium shrink-0 transition-colors disabled:opacity-50"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="p-4 border-t border-[#1f293d] bg-slate-900/80 flex gap-2">
            <input
              type="text"
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !loading && handleSendMessage()}
              placeholder={`Give instructions to ${activeRole.name}...`}
              disabled={loading}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50 font-sans"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={loading || !inputPrompt.trim()}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-md shadow-blue-600/20"
            >
              <Send className="h-3.5 w-3.5" />
              <span>Execute</span>
            </button>
          </div>
        </div>

        {/* Real Execution Trace Inspector (PostgreSQL agent_execution_traces) */}
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 flex flex-col h-[700px] shadow-xl overflow-hidden space-y-4">
          <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-white">Execution Trace Stream</h2>
            </div>
            <button
              onClick={loadTraces}
              disabled={loadingTraces}
              className="text-xs text-slate-400 hover:text-white p-1 rounded transition-colors"
              title="Refresh traces"
            >
              <RefreshCcw className={`h-3.5 w-3.5 ${loadingTraces ? "animate-spin" : ""}`} />
            </button>
          </div>

          <p className="text-[11px] text-slate-400 leading-snug">
            Real structured execution traces from PostgreSQL table <code className="text-blue-400 font-mono">agent_execution_traces</code>.
          </p>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 font-mono text-[11px]">
            {recentTraces.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs text-center space-y-2">
                <Layers className="h-8 w-8 text-slate-700" />
                <span>No backend traces recorded yet. Send a prompt to execute an action.</span>
              </div>
            ) : (
              recentTraces.map((t) => (
                <div
                  key={t.id}
                  onClick={() => setSelectedTrace(t)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer space-y-1.5 ${
                    selectedTrace?.id === t.id
                      ? "bg-blue-950/40 border-blue-700 shadow-sm"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-[11px]">{t.tool_name || "dialogue"}</span>
                    <StatusBadge status={t.policy_decision || "INFO"} />
                  </div>

                  <div className="text-[10px] text-slate-400 truncate">
                    Prompt: &quot;{t.user_prompt}&quot;
                  </div>

                  <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-800">
                    <span>Latency: {t.latency_ms}ms</span>
                    <span>{new Date(t.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Trace Detail Modal */}
          {selectedTrace && (
            <div className="pt-3 border-t border-[#1f293d] space-y-2 font-mono text-[10px]">
              <div className="flex items-center justify-between text-slate-300 font-bold">
                <span>Trace Details ({selectedTrace.id.slice(0, 12)})</span>
                <button
                  onClick={() => setSelectedTrace(null)}
                  className="text-slate-500 hover:text-slate-300"
                >
                  close
                </button>
              </div>
              <div className="p-2.5 rounded-xl bg-black/70 border border-slate-800 space-y-1.5 text-slate-300 max-h-48 overflow-y-auto">
                <div>Model: <span className="text-white">{selectedTrace.model_name} ({selectedTrace.model_provider})</span></div>
                <div>Operation ID: <span className="text-blue-400">{selectedTrace.operation_id || "None"}</span></div>
                <div className="text-slate-400 font-semibold mt-1">Tool Arguments:</div>
                <pre className="text-[9px] text-emerald-400 bg-slate-950 p-2 rounded overflow-x-auto">
                  {JSON.stringify(selectedTrace.tool_arguments, null, 2)}
                </pre>
                <div className="text-slate-400 font-semibold mt-1">Tool Execution Result:</div>
                <pre className="text-[9px] text-indigo-300 bg-slate-950 p-2 rounded overflow-x-auto">
                  {JSON.stringify(selectedTrace.tool_result, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
