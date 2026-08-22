"use client";

import React, { useState } from "react";
import {
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  CreditCard,
  UserCheck,
  Bot,
  Zap,
  Terminal,
  Clock,
  Sparkles,
  Lock,
  Layers,
} from "lucide-react";
import { api, DemoStepResult } from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import StatusBadge from "@/components/common/StatusBadge";
import IntegrationBadge from "@/components/common/IntegrationBadge";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { useToast } from "@/components/common/Toast";

interface StepConfig {
  stepNumber: number;
  title: string;
  category: "AUTHORIZED" | "BLOCKED" | "REVIEW";
  agentName: string;
  agentId: string;
  amountInr: string;
  operationType: string;
  description: string;
  securityInvariant: string;
  expectedDecision: "ALLOW" | "DENY" | "REQUIRE_HUMAN_REVIEW";
}

const DEMO_STEPS: StepConfig[] = [
  {
    stepNumber: 1,
    title: "1. Authorized Purchase Within Mandate Bounds",
    category: "AUTHORIZED",
    agentName: "Procurement Sub-Agent",
    agentId: "agt_procurement_child_01",
    amountInr: "₹6,500",
    operationType: "CREATE_ORDER",
    description:
      "Procurement sub-agent purchases 1 Keychron K2 Keyboard for ₹6,500. This is strictly within the ₹10,000 delegated sub-budget bound.",
    securityInvariant: "All 8 deterministic policy rules pass in <2ms. Two-phase budget reservation commits spend to Razorpay Test Mode.",
    expectedDecision: "ALLOW",
  },
  {
    stepNumber: 2,
    title: "2. Adversarial Bulk Escalation Attack Blocked",
    category: "BLOCKED",
    agentName: "Compromised Agent",
    agentId: "agt_procurement_child_01",
    amountInr: "₹6,50,000",
    operationType: "CREATE_ORDER",
    description:
      "Adversarial prompt injection attempts unauthorized 100x bulk order for ₹6,50,000, attempting to drain enterprise capital.",
    securityInvariant: "PER_TRANSACTION_LIMIT_CHECK & AGGREGATE_SPEND_LIMIT_CHECK block execution. Zero-Gateway-Dispatch Guarantee: 0 calls touch Razorpay.",
    expectedDecision: "DENY",
  },
  {
    stepNumber: 3,
    title: "3. Unauthorized Cross-Role Refund Attack Blocked",
    category: "BLOCKED",
    agentName: "Buyer Agent (Unprivileged)",
    agentId: "agt_procurement_child_01",
    amountInr: "₹2,500",
    operationType: "CREATE_REFUND",
    description:
      "Prompt injection attempts to invoke customer refund capabilities from a buyer agent to siphon funds into an external account.",
    securityInvariant: "OPERATION_TYPE_CHECK strictly verifies operation allowlist. Procurement agents cannot create refunds; rejected with 0 gateway dispatches.",
    expectedDecision: "DENY",
  },
  {
    stepNumber: 4,
    title: "4. Event-Driven Webhook Auto-Convergence",
    category: "AUTHORIZED",
    agentName: "Procurement Sub-Agent",
    agentId: "agt_procurement_child_01",
    amountInr: "₹1,500",
    operationType: "CREATE_ORDER",
    description:
      "Inbound Razorpay payment.captured webhook arrives with cryptographic HMAC-SHA256 signature, transitioning state from RESERVED to SUCCEEDED.",
    securityInvariant: "HMAC signature verification and idempotency locks prevent double-spend and guarantee ledger auto-convergence.",
    expectedDecision: "ALLOW",
  },
  {
    stepNumber: 5,
    title: "5. Cascading Parent Revocation Propagation",
    category: "BLOCKED",
    agentName: "Alpha Commerce Enterprise (Admin)",
    agentId: "prn_alpha_corp_01",
    amountInr: "₹0.00",
    operationType: "MANDATE_REVOKED",
    description:
      "Root parent mandate revoked by enterprise admin. Suspension/revocation instantly cascades down the DAG, permanently disabling all child authority.",
    securityInvariant: "HIERARCHICAL_DELEGATION_CHECK immediately invalidates child mandates if any ancestor in the tree is revoked.",
    expectedDecision: "DENY",
  },
];

export default function DemoPage() {
  const toast = useToast();
  const [selectedStepNumber, setSelectedStepNumber] = useState<number>(1);
  const [stepResults, setStepResults] = useState<Record<number, DemoStepResult>>({});
  const [runningStep, setRunningStep] = useState<number | null>(null);
  const [runningAll, setRunningAll] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [confirmResetOpen, setConfirmResetOpen] = useState(false);

  const activeStepConfig =
    DEMO_STEPS.find((s) => s.stepNumber === selectedStepNumber) || DEMO_STEPS[0];

  const handleResetDataset = async () => {
    setResetting(true);
    try {
      const res = await api.resetDemo();
      setStepResults({});
      toast.success(
        "Clean Slate Reset Complete",
        `Bootstrapped principal, 2 agents, 2 mandates, and clean ledger.`
      );
    } catch (err: unknown) {
      toast.error("Reset Failed", err instanceof Error ? err.message : String(err));
    } finally {
      setResetting(false);
      setConfirmResetOpen(false);
    }
  };

  const handleRunStep = async (stepNum: number) => {
    setRunningStep(stepNum);
    try {
      const res = await api.runDemoScenario(stepNum);
      setStepResults((prev) => ({ ...prev, [stepNum]: res }));

      if (res.decision === "ALLOW") {
        toast.success(`Step ${stepNum} Executed`, `Decision: ALLOW · Razorpay Order Created`);
      } else if (res.decision === "DENY") {
        toast.warning(`Step ${stepNum} Blocked`, `Decision: DENY · 0 Gateway Dispatches`);
      } else {
        toast.info(`Step ${stepNum} Review Required`, `Decision: REQUIRE_HUMAN_REVIEW`);
      }
    } catch (err: unknown) {
      toast.error(`Step ${stepNum} Failed`, err instanceof Error ? err.message : String(err));
    } finally {
      setRunningStep(null);
    }
  };

  const handleRunAllSteps = async () => {
    setRunningAll(true);
    try {
      toast.info("Starting Guided 5-Step Runner", "Executing scenarios sequentially...");
      for (const step of DEMO_STEPS) {
        setSelectedStepNumber(step.stepNumber);
        setRunningStep(step.stepNumber);
        const res = await api.runDemoScenario(step.stepNumber);
        setStepResults((prev) => ({ ...prev, [step.stepNumber]: res }));
        await new Promise((r) => setTimeout(r, 600));
      }
      toast.success("Showcase Complete", "All 5 competition demo scenarios evaluated.");
    } catch (err: unknown) {
      toast.error("Runner Interrupted", err instanceof Error ? err.message : String(err));
    } finally {
      setRunningStep(null);
      setRunningAll(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Page Header */}
      <PageHeader
        title="Competition Showcase & 5-Step Guided Runner"
        icon={Sparkles}
        architecturePhase="Comprehensive System Verification"
        description="A guided 5-step scenario runner that proves every core architectural guarantee: valid within-bound shopping, delegated sub-mandates, blocked adversarial prompt injection attacks, blocked privilege escalation, and human-in-the-loop approval thresholds."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setConfirmResetOpen(true)}
              disabled={resetting || runningAll}
              className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3.5 py-2 text-xs font-semibold transition-all disabled:opacity-50"
            >
              <RotateCcw className={`h-3.5 w-3.5 ${resetting ? "animate-spin" : ""}`} />
              <span>Reset Clean Slate</span>
            </button>
            <button
              onClick={handleRunAllSteps}
              disabled={runningAll || runningStep !== null}
              className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-blue-600/25 transition-all disabled:opacity-50"
            >
              <Play className={`h-3.5 w-3.5 ${runningAll ? "animate-spin" : ""}`} />
              <span>{runningAll ? "Running All 5 Steps..." : "Run All 5 Steps"}</span>
            </button>
          </div>
        }
      />

      {/* 5-Step Pipeline Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {DEMO_STEPS.map((step) => {
          const isSelected = selectedStepNumber === step.stepNumber;
          const isExecuting = runningStep === step.stepNumber;
          const result = stepResults[step.stepNumber];

          return (
            <button
              key={step.stepNumber}
              onClick={() => setSelectedStepNumber(step.stepNumber)}
              className={`p-4 rounded-2xl border text-left transition-all relative flex flex-col justify-between space-y-3 ${
                isSelected
                  ? "bg-blue-600/15 border-blue-500 shadow-lg shadow-blue-500/10 scale-[1.02]"
                  : "bg-[#111827] border-[#1f293d] hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="h-6 w-6 rounded-lg bg-slate-900 border border-slate-800 text-blue-400 flex items-center justify-center font-mono font-bold text-xs">
                  #{step.stepNumber}
                </span>
                {result ? (
                  <StatusBadge status={result.decision} />
                ) : (
                  <span className="text-[10px] font-mono text-slate-500">READY</span>
                )}
              </div>

              <div className="space-y-1">
                <h3 className="font-bold text-white text-xs leading-snug line-clamp-2">
                  {step.title.split(". ")[1]}
                </h3>
                <p className="text-[10px] text-slate-400 font-mono">
                  {step.amountInr} · {step.operationType}
                </p>
              </div>

              <div className="text-[9px] font-mono text-slate-500 pt-1 border-t border-slate-800/80">
                {step.agentName}
              </div>
            </button>
          );
        })}
      </div>

      {/* Active Step Details & Live Execution Console */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Step Scenario Specifications */}
        <div className="lg:col-span-2 rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-5 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[#1f293d] pb-3">
            <div>
              <span className="text-[10px] font-mono text-blue-400 uppercase tracking-wider block">
                Scenario #{activeStepConfig.stepNumber} Focus
              </span>
              <h2 className="text-base font-bold text-white mt-0.5">{activeStepConfig.title}</h2>
            </div>
            <button
              onClick={() => handleRunStep(activeStepConfig.stepNumber)}
              disabled={runningStep !== null || runningAll}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-emerald-600/25 transition-all disabled:opacity-50"
            >
              <Play className={`h-3.5 w-3.5 ${runningStep === activeStepConfig.stepNumber ? "animate-spin" : ""}`} />
              <span>
                {runningStep === activeStepConfig.stepNumber
                  ? "Evaluating Step..."
                  : `Execute Step ${activeStepConfig.stepNumber}`}
              </span>
            </button>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {activeStepConfig.description}
          </p>

          {/* Parameters Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-0.5">
              <span className="text-slate-500 text-[10px] block font-sans">Target Agent</span>
              <strong className="text-white text-xs">{activeStepConfig.agentName}</strong>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-0.5">
              <span className="text-slate-500 text-[10px] block font-sans">Operation</span>
              <strong className="text-blue-300 text-xs">{activeStepConfig.operationType}</strong>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-0.5">
              <span className="text-slate-500 text-[10px] block font-sans">Amount (INR)</span>
              <strong className="text-emerald-400 text-xs">{activeStepConfig.amountInr}</strong>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-0.5">
              <span className="text-slate-500 text-[10px] block font-sans">Expected Decision</span>
              <strong className="text-purple-300 text-xs">{activeStepConfig.expectedDecision}</strong>
            </div>
          </div>

          {/* Security Invariant Guarantee Banner */}
          <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-900/40 text-blue-300 space-y-1 text-xs font-sans">
            <div className="flex items-center gap-2 font-bold text-white">
              <ShieldCheck className="h-4 w-4 text-blue-400" />
              <span>Architectural Invariant Guarantee:</span>
            </div>
            <p className="text-[11px] text-blue-200/90 leading-relaxed">
              {activeStepConfig.securityInvariant}
            </p>
          </div>
        </div>

        {/* Right Col: Live Execution Output & Verification Scorecard */}
        <div className="rounded-2xl bg-[#111827] border border-[#1f293d] p-6 space-y-4 shadow-xl flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Terminal className="h-4 w-4 text-indigo-400" />
                <span>Backend Execution Result</span>
              </h3>
              {stepResults[activeStepConfig.stepNumber] && (
                <StatusBadge status={stepResults[activeStepConfig.stepNumber].decision} />
              )}
            </div>

            {stepResults[activeStepConfig.stepNumber] ? (
              <div className="space-y-3 font-mono text-xs animate-in fade-in duration-150">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                  <div className="flex justify-between text-slate-400">
                    <span>Authorized:</span>
                    <strong
                      className={
                        stepResults[activeStepConfig.stepNumber].authorized
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }
                    >
                      {stepResults[activeStepConfig.stepNumber].authorized ? "YES" : "NO"}
                    </strong>
                  </div>

                  <div className="flex justify-between text-slate-400">
                    <span>Operation ID:</span>
                    <span className="text-white">
                      {stepResults[activeStepConfig.stepNumber].operation_id || "None (Blocked)"}
                    </span>
                  </div>

                  <div className="flex justify-between text-slate-400">
                    <span>Audit Trace ID:</span>
                    <span className="text-blue-400">
                      {stepResults[activeStepConfig.stepNumber].audit_trace_id}
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 block font-sans">Gateway Effect:</span>
                  <p className="text-xs font-bold text-white">
                    {stepResults[activeStepConfig.stepNumber].gateway_effect}
                  </p>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-400 block">Raw Backend Response:</span>
                  <pre className="p-2.5 rounded-xl bg-black/60 border border-slate-800 text-[10px] text-emerald-400 overflow-x-auto max-h-36">
                    {JSON.stringify(stepResults[activeStepConfig.stepNumber].details, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs font-mono space-y-2">
                <Clock className="h-8 w-8 mx-auto text-slate-700" />
                <p>Click &quot;Execute Step {activeStepConfig.stepNumber}&quot; to run live evaluation against FastAPI backend.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Dialog for Reset */}
      <ConfirmDialog
        isOpen={confirmResetOpen}
        title="Reset Demo Dataset to Clean Slate?"
        description="This will clear all transactions, reset parent/child agent mandates to initial ₹1,00,000 / ₹15,000 budgets, and initialize the clean baseline dataset."
        confirmLabel="Reset Clean Slate"
        isDestructive={true}
        isLoading={resetting}
        onConfirm={handleResetDataset}
        onCancel={() => setConfirmResetOpen(false)}
      />
    </div>
  );
}
