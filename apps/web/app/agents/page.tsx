"use client";

import React, { useState } from "react";
import { Bot, Send, ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Clock, ShoppingCart, RefreshCcw } from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "agent";
  text: string;
  toolCalls?: any[];
  policyDecisions?: any[];
}

export default function AgentsPlaygroundPage() {
  const [selectedAgent, setSelectedAgent] = useState<"shopping" | "support">("shopping");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "m_welcome",
      sender: "agent",
      text: "Hello! I am your Mandate Shopping Assistant. I can browse the product catalog and create bounded purchase orders or payment links under my financial mandate.",
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [latestTrace, setLatestTrace] = useState<any>(null);

  const samplePrompts = selectedAgent === "shopping" ? [
    "Browse the electronics catalog",
    "Buy 1 Keychron K2 Mechanical Keyboard for Alice",
    "Order 1 Dell 4K Monitor for Rs. 75,000 (Exceeds limit)",
  ] : [
    "Look up status of operation op_test_123",
    "Issue a Rs. 1,500 refund for payment pay_legit_01",
    "Issue a Rs. 50,000 refund (Exceeds refund cap)",
  ];

  const handleSendMessage = async (customPrompt?: string) => {
    const promptToSend = customPrompt || inputPrompt;
    if (!promptToSend.trim() || loading) return;

    const userMsg: Message = {
      id: `usr_${Date.now()}`,
      sender: "user",
      text: promptToSend,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");
    setLoading(true);

    try {
      // Demo simulated response matching backend AgentRunner
      let replyText = "";
      let simulatedTrace: any = null;

      if (promptToSend.toLowerCase().includes("browse")) {
        replyText = "Here are the available items in the catalog:\n\n• Keychron K2 Mechanical Keyboard — ₹6,500 (15 in stock)\n• Logitech MX Master 3S Mouse — ₹8,999 (8 in stock)\n• Ergonomic Wool Felt Desk Mat — ₹1,500 (50 in stock)\n• Dell UltraSharp 32-inch 4K Monitor — ₹75,000 (3 in stock)";
      } else if (promptToSend.toLowerCase().includes("exceeds limit") || promptToSend.includes("75,000") || promptToSend.includes("50,000")) {
        replyText = "I attempted to create the order, but Mandate's Policy Engine **DENIED** the request: Operation amount exceeds your mandate's per-transaction limit of ₹50,000.";
        simulatedTrace = {
          decision: "DENY",
          reasons: ["[PER_TRANSACTION_LIMIT_CHECK] Requested amount exceeds per-transaction limit 5000000"],
          tool: selectedAgent === "shopping" ? "create_purchase_order" : "issue_customer_refund",
          razorpayDispatched: false,
          latency: "1.8ms",
        };
      } else if (promptToSend.toLowerCase().includes("buy") || promptToSend.toLowerCase().includes("keychron")) {
        replyText = "I have created purchase order **order_mock_49f82d1** for Keychron K2 (₹6,500). Mandate Policy Engine evaluated and **APPROVED** the transaction. Razorpay order is active.";
        simulatedTrace = {
          decision: "ALLOW",
          tool: "create_purchase_order",
          operationId: "op_49fa02",
          razorpayOrderId: "order_mock_49f82d1",
          razorpayDispatched: true,
          latency: "1.2ms",
        };
      } else {
        replyText = `Processed request for ${selectedAgent} agent. Policy bounds verified.`;
      }

      setLatestTrace(simulatedTrace);
      setMessages((prev) => [
        ...prev,
        {
          id: `ag_${Date.now()}`,
          sender: "agent",
          text: replyText,
          policyDecisions: simulatedTrace ? [simulatedTrace] : [],
        },
      ]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">AI Agent Execution Playground</h1>
          <p className="text-sm text-slate-400">
            Interact with autonomous agents operating strictly within Mandate-enforced financial contracts.
          </p>
        </div>
        <div className="flex rounded-lg bg-slate-900 border border-slate-800 p-1">
          <button
            onClick={() => {
              setSelectedAgent("shopping");
              setMessages([{ id: "w1", sender: "agent", text: "Hello! I am your Mandate Shopping Assistant. What can I purchase for you?" }]);
            }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              selectedAgent === "shopping" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            <ShoppingCart className="h-3.5 w-3.5" /> Shopping Agent
          </button>
          <button
            onClick={() => {
              setSelectedAgent("support");
              setMessages([{ id: "w2", sender: "agent", text: "Hello! I am your Customer Support Agent. Provide an operation ID or payment ID to inspect or refund." }]);
            }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              selectedAgent === "support" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            <RefreshCcw className="h-3.5 w-3.5" /> Support Agent
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Chat Window */}
        <div className="lg:col-span-2 rounded-xl bg-[#111827] border border-[#1f293d] flex flex-col h-[550px]">
          {/* Header */}
          <div className="px-5 py-3 border-b border-[#1f293d] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                <Bot className="h-4 w-4 text-blue-400" />
              </div>
              <div>
                <span className="text-sm font-semibold text-white capitalize">{selectedAgent} Agent</span>
                <span className="block text-[10px] text-emerald-400">● Bounded by Mandate #mnd_q3</span>
              </div>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Model: GPT-4o-mini (Tools Enabled)</span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                    m.sender === "user"
                      ? "bg-blue-600 text-white rounded-br-none shadow-sm shadow-blue-500/20"
                      : "bg-slate-900/90 text-slate-200 border border-slate-800 rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-line leading-relaxed">{m.text}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Quick Prompts */}
          <div className="px-4 py-2 bg-slate-900/40 border-t border-[#1f293d] flex gap-2 overflow-x-auto text-xs">
            {samplePrompts.map((p) => (
              <button
                key={p}
                onClick={() => handleSendMessage(p)}
                className="whitespace-nowrap rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 px-2.5 py-1 transition-colors border border-slate-700/50"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="p-3 border-t border-[#1f293d] flex gap-2">
            <input
              type="text"
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
              placeholder={`Ask the ${selectedAgent} agent...`}
              className="flex-1 rounded-lg bg-slate-900 border border-slate-800 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={loading}
              className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-500 transition-colors disabled:opacity-50 flex items-center justify-center shadow-sm"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Right: Real-Time Policy Inspector */}
        <div className="rounded-xl bg-[#111827] border border-[#1f293d] p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-[#1f293d] pb-3">
            <ShieldCheck className="h-4 w-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-white">Mandate Policy Inspector</h2>
          </div>

          {latestTrace ? (
            <div className="space-y-3.5 text-xs">
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 font-medium">Policy Engine Decision</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                      latestTrace.decision === "ALLOW"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-red-500/10 text-red-400 border border-red-500/20"
                    }`}
                  >
                    {latestTrace.decision}
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Decision Latency:</span>
                  <span className="font-mono text-slate-200">{latestTrace.latency}</span>
                </div>
              </div>

              {latestTrace.reasons && (
                <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20 text-red-400 space-y-1">
                  <span className="font-semibold block text-[11px]">Rejection Reason:</span>
                  <p className="text-[11px] leading-relaxed">{latestTrace.reasons[0]}</p>
                </div>
              )}

              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1.5">
                <span className="text-slate-400 font-medium block">Gateway Dispatch Invariant</span>
                <div className="flex items-center gap-2">
                  {latestTrace.razorpayDispatched ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      <span className="text-emerald-400 font-mono text-[11px]">Razorpay Dispatch: ALLOWED</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 text-amber-400" />
                      <span className="text-amber-400 font-mono text-[11px]">Razorpay Dispatch: BLOCKED (0 Gateway Calls)</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-lg bg-slate-900/40 border border-dashed border-slate-800 text-center text-xs text-slate-500 space-y-1">
              <Clock className="h-5 w-5 mx-auto text-slate-600 mb-1" />
              <p>No tool execution triggered yet.</p>
              <p className="text-[11px]">Send a prompt to observe Mandate's real-time policy evaluation.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
