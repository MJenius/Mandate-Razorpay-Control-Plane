"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  Send,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ShoppingCart,
  RefreshCcw,
  ChevronDown,
  ChevronRight,
  Terminal,
  Activity,
  Layers,
  ArrowRight,
  Cpu,
} from "lucide-react";
import { api, AgentChatResponse, AgentTrace } from "../../lib/api";

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

export default function AgentsPlaygroundPage() {
  const [selectedAgentId, setSelectedAgentId] = useState<string>("agt_shopping_parent_01");
  const [sessionId, setSessionId] = useState<string>("sess_init");
  const [mounted, setMounted] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "m_welcome",
      sender: "agent",
      text: "Hello! I am your Mandate Shopping Assistant. I can browse the product catalog and create bounded purchase orders or payment links under my financial mandate.",
      timestamp: "Ready",
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState<string>("");
  const [recentTraces, setRecentTraces] = useState<AgentTrace[]>([]);
  const [loadingTraces, setLoadingTraces] = useState(false);
  const [selectedTrace, setSelectedTrace] = useState<AgentTrace | null>(null);
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
    setSessionId(`sess_${Date.now()}`);
  }, []);

  const samplePrompts =
    selectedAgentId === "agt_shopping_parent_01"
      ? [
          "Browse the electronics catalog",
          "Buy 1 Keychron K2 Mechanical Keyboard for Alice",
          "Order 100 Keychron Keyboards for Rs. 6,50,000 (Bulk Escalation)",
          "Issue a customer refund of Rs. 2,500 to pay_attacker_01",
        ]
      : [
          "Procure 1 Keychron K2 Keyboard within delegated bound",
          "Order 5 Dell 4K Monitors for Rs. 3,75,000",
          "Issue refund of Rs. 1,000",
        ];

  // Auto-scroll chat on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Load actual execution traces from backend
  const loadTraces = async () => {
    setLoadingTraces(true);
    try {
      const traces = await api.getAgentTraces(selectedAgentId);
      setRecentTraces(traces);
    } catch {
      // Backend might be offline or empty
    } finally {
      setLoadingTraces(false);
    }
  };

  useEffect(() => {
    loadTraces();
  }, [selectedAgentId]);

  const toggleExpand = (id: string) => {
    setExpandedDetails((prev) => ({ ...prev, [id]: !prev[id] }));
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
    setActiveStep("1. Thinking & Planning...");

    const historyPayload = messages.slice(-6).map((m) => ({
      role: m.sender === "user" ? "user" : "assistant",
      content: m.text,
    }));

    try {
      // Step progression simulation for realistic UI feedback while network request processes
      setTimeout(() => setActiveStep("2. Generating Tool Call schema..."), 150);
      setTimeout(() => setActiveStep("3. Intercepting via Mandate Policy Engine..."), 300);

      const response = await api.chatWithAgent(
        selectedAgentId,
        promptToSend,
        sessionId,
        historyPayload
      );

      setActiveStep("4. Committing Audit Trace & Gateway effect...");

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
      await loadTraces();
    } catch (err: unknown) {
      const errorText = err instanceof Error ? err.message : "Network error contacting agent backend";
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: "agent",
        text: `⚠️ Communication Failure: ${errorText}. Please verify the FastAPI backend is active on http://localhost:8000.`,
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
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Bot className="h-6 w-6 text-blue-400" />
            AI Agent Console & Authorization Playground
          </h1>
          <p className="text-sm text-slate-400">
            Real-time interactive dialogue with autonomous agents. Tool calls are deterministically intercepted and evaluated by Mandate&apos;s Policy Gate.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1.5 rounded-xl">
          <button
            onClick={() => {
              setSelectedAgentId("agt_shopping_parent_01");
              setSessionId(`sess_${Date.now()}`);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedAgentId === "agt_shopping_parent_01"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <ShoppingCart className="h-3.5 w-3.5" />
            Shopping Agent (Primary)
          </button>
          <button
            onClick={() => {
              setSelectedAgentId("agt_procurement_child_01");
              setSessionId(`sess_${Date.now()}`);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedAgentId === "agt_procurement_child_01"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Cpu className="h-3.5 w-3.5" />
            Procurement Sub-Agent
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Console (2 Columns) */}
        <div className="lg:col-span-2 flex flex-col h-[700px] rounded-2xl bg-[#111827] border border-[#1f293d] shadow-xl overflow-hidden">
          {/* Console Header */}
          <div className="px-5 py-3.5 border-b border-[#1f293d] bg-slate-900/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-xs font-mono text-slate-300 font-medium">
                Connected: <strong className="text-white">{selectedAgentId}</strong>
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
                      text: "Session restarted. Ready for instructions.",
                      timestamp: new Date().toLocaleTimeString(),
                    },
                  ]);
                  setSessionId(`sess_${Date.now()}`);
                }}
                className="hover:text-slate-300 p-1"
                title="Reset session"
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
                    className={`h-8 w-8 rounded-full border flex items-center justify-center shrink-0 ${
                      m.isError
                        ? "bg-rose-950/60 border-rose-800 text-rose-400"
                        : "bg-blue-950/60 border-blue-800 text-blue-400"
                    }`}
                  >
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`max-w-[82%] space-y-2 rounded-2xl p-4 ${
                    m.sender === "user"
                      ? "bg-blue-600 text-white rounded-br-none shadow-md"
                      : m.isError
                      ? "bg-rose-950/30 border border-rose-900/50 text-rose-200 rounded-bl-none"
                      : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-sm"
                  }`}
                >
                  <div className="text-xs leading-relaxed whitespace-pre-line">{m.text}</div>

                  {/* Policy Decision & Tool Call Badge Inspector */}
                  {m.policyDecisions && m.policyDecisions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800 space-y-2 font-mono text-[11px]">
                      {m.policyDecisions.map((p, idx) => (
                        <div
                          key={idx}
                          className={`p-2.5 rounded-lg border flex flex-col gap-1.5 ${
                            p.decision === "ALLOW"
                              ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-300"
                              : p.decision === "DENY"
                              ? "bg-rose-950/30 border-rose-800/40 text-rose-300"
                              : "bg-amber-950/30 border-amber-800/40 text-amber-300"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold flex items-center gap-1.5">
                              {p.decision === "ALLOW" ? (
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                              ) : (
                                <XCircle className="h-3.5 w-3.5 text-rose-400" />
                              )}
                              MANDATE DECISION: {p.decision}
                            </span>
                            {m.latencyMs && <span>{m.latencyMs}ms</span>}
                          </div>

                          {p.rejection_reasons && p.rejection_reasons.length > 0 && (
                            <div className="text-[10px] text-rose-400 bg-rose-950/40 p-1.5 rounded border border-rose-900/30">
                              {p.rejection_reasons.join(", ")}
                            </div>
                          )}

                          {m.toolCalls && m.toolCalls[idx] && (
                            <div className="text-[10px] text-slate-400">
                              Tool: <span className="text-slate-200">{m.toolCalls[idx].tool_name}</span>
                              <button
                                onClick={() => toggleExpand(m.id)}
                                className="ml-2 text-blue-400 hover:underline inline-flex items-center gap-0.5"
                              >
                                {expandedDetails[m.id] ? "hide args" : "view args"}
                              </button>
                            </div>
                          )}

                          {expandedDetails[m.id] && m.toolCalls && m.toolCalls[idx] && (
                            <pre className="mt-1 p-2 rounded bg-black/60 text-[9px] text-slate-300 overflow-x-auto">
                              {JSON.stringify(m.toolCalls[idx].arguments, null, 2)}
                            </pre>
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
            {samplePrompts.map((p, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(p)}
                disabled={loading}
                className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium shrink-0 transition-colors disabled:opacity-50"
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
              placeholder="Give autonomous financial instruction (e.g. 'Buy 1 Keychron Keyboard for Alice')..."
              disabled={loading}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={loading || !inputPrompt.trim()}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-md"
            >
              <Send className="h-3.5 w-3.5" />
              Run
            </button>
          </div>
        </div>

        {/* Real Backend Trace Inspector (1 Column) */}
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-5 flex flex-col h-[700px] shadow-xl overflow-hidden space-y-4">
          <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-white">Execution Trace Inspector</h2>
            </div>
            <button
              onClick={loadTraces}
              disabled={loadingTraces}
              className="text-xs text-slate-400 hover:text-white p-1 rounded transition-colors"
            >
              <RefreshCcw className={`h-3.5 w-3.5 ${loadingTraces ? "animate-spin" : ""}`} />
            </button>
          </div>

          <p className="text-[11px] text-slate-400 leading-snug">
            Real structured audit logs from PostgreSQL table <code className="text-blue-400 font-mono">agent_execution_traces</code>.
          </p>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {recentTraces.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs text-center space-y-2">
                <Layers className="h-8 w-8 text-slate-700" />
                <span>No backend traces recorded yet for this agent. Send a prompt to trigger an execution trace.</span>
              </div>
            ) : (
              recentTraces.map((t) => (
                <div
                  key={t.id}
                  onClick={() => setSelectedTrace(t)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer font-mono text-[11px] space-y-1.5 ${
                    selectedTrace?.id === t.id
                      ? "bg-blue-950/40 border-blue-700 shadow-sm"
                      : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-[11px]">{t.tool_name || "dialogue_only"}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] ${
                        t.policy_decision === "ALLOW"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                          : t.policy_decision === "DENY"
                          ? "bg-rose-950 text-rose-300 border border-rose-800"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {t.policy_decision || "N/A"}
                    </span>
                  </div>

                  <div className="text-[10px] text-slate-400 truncate">
                    Prompt: &quot;{t.user_prompt}&quot;
                  </div>

                  <div className="flex items-center justify-between text-[9px] text-slate-500">
                    <span>Latency: {t.latency_ms}ms</span>
                    <span>{new Date(t.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Trace Detail Modal/Drawer */}
          {selectedTrace && (
            <div className="pt-3 border-t border-[#1f293d] space-y-2 font-mono text-[10px]">
              <div className="flex items-center justify-between text-slate-300 font-bold">
                <span>Trace Details ({selectedTrace.id.slice(0, 10)})</span>
                <button
                  onClick={() => setSelectedTrace(null)}
                  className="text-slate-500 hover:text-slate-300"
                >
                  close
                </button>
              </div>
              <div className="p-2.5 rounded-lg bg-black/60 border border-slate-800 space-y-1 text-slate-300 max-h-48 overflow-y-auto">
                <div>Model: <span className="text-white">{selectedTrace.model_name}</span></div>
                <div>Op ID: <span className="text-blue-400">{selectedTrace.operation_id || "None"}</span></div>
                <div className="text-slate-400 font-semibold mt-1">Arguments:</div>
                <pre className="text-[9px] text-emerald-400 overflow-x-auto">
                  {JSON.stringify(selectedTrace.tool_arguments, null, 2)}
                </pre>
                <div className="text-slate-400 font-semibold mt-1">Tool Result:</div>
                <pre className="text-[9px] text-indigo-300 overflow-x-auto">
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
