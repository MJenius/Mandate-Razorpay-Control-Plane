/**
 * Centralized, typed API Client and data access layer for Mandate Web.
 * Connects directly to FastAPI backend and reflects real control plane state.
 */

export const RAW_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Ensure no trailing slash for clean endpoint concatenation
export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, "");

export interface Agent {
  id: string;
  name: string;
  description: string;
  agent_type: "SHOPPING" | "PROCUREMENT" | "SUPPORT" | "FINANCE" | string;
  status: "ACTIVE" | "SUSPENDED" | "REVOKED";
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface Mandate {
  id: string;
  agent_id: string;
  granted_by_id: string;
  parent_mandate_id: string | null;
  delegation_depth: number;
  max_delegation_depth: number;
  status: "ACTIVE" | "PENDING_APPROVAL" | "SUSPENDED" | "EXPIRED" | "EXHAUSTED" | "REVOKED";
  suspension_reason?: string | null;
  currency: string;
  max_amount_per_op: number; // in paise
  aggregate_spend_limit: number; // in paise
  current_aggregate_spend: number; // in paise
  reserved_spend: number; // in paise
  delegated_child_budget_allocated: number; // in paise
  review_threshold_amount: number | null; // in paise
  allowed_operations: string[];
  policy_config: Record<string, unknown>;
  valid_from?: string;
  valid_until: string;
  version: number;
  created_at: string;
  updated_at?: string;
}

export interface PolicyRuleDiagnostic {
  rule_name: string;
  decision: "ALLOW" | "DENY" | "REQUIRE_HUMAN_REVIEW";
  passed: boolean;
  reason: string;
  latency_ms: number;
  context?: Record<string, unknown>;
}

export interface PolicyEvaluationDetails {
  decision?: "ALLOW" | "DENY" | "REQUIRE_HUMAN_REVIEW";
  approved?: boolean;
  requires_human_review?: boolean;
  operation_id?: string;
  agent_id?: string;
  mandate_id?: string;
  total_latency_ms?: number;
  total_evaluation_latency_ms?: number;
  rejection_reasons?: string[];
  review_reasons?: string[];
  rules_evaluated?: number;
  rule_diagnostics?: PolicyRuleDiagnostic[];
}

export interface FinancialOperation {
  id: string;
  operation_id: string;
  idempotency_key: string;
  agent_id: string;
  mandate_id: string;
  operation_type:
    | "CREATE_ORDER"
    | "CAPTURE_PAYMENT"
    | "CREATE_REFUND"
    | "CREATE_PAYMENT_LINK"
    | "CANCEL_PAYMENT_LINK";
  status:
    | "INITIATED"
    | "POLICY_CHECK_PENDING"
    | "POLICY_APPROVED"
    | "POLICY_REJECTED"
    | "REQUIRES_APPROVAL"
    | "RESERVED"
    | "EXECUTING"
    | "SUCCEEDED"
    | "FAILED"
    | "CANCELLED";
  amount: number; // in paise
  currency: string;
  payload: Record<string, unknown>;
  policy_evaluation_details: PolicyEvaluationDetails | null;
  error_message: string | null;
  approved_by_id: string | null;
  trace_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  operation_id: string;
  gateway_name: string;
  gateway_order_id: string | null;
  gateway_payment_id: string | null;
  gateway_refund_id: string | null;
  gateway_payment_link_id: string | null;
  gateway_payment_link_url: string | null;
  amount: number;
  currency: string;
  status: "CREATED" | "AUTHORIZED" | "CAPTURED" | "REFUNDED" | "FAILED";
  gateway_response: Record<string, unknown>;
  error_code: string | null;
  error_description: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  event_id: string;
  action: string;
  actor_id: string;
  actor_type: "AGENT" | "PRINCIPAL" | "SYSTEM" | string;
  resource_id: string;
  resource_type: string;
  previous_state: Record<string, unknown> | null;
  new_state: Record<string, unknown> | null;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface AgentChatResponse {
  reply: string;
  session_id: string;
  tool_calls: Array<{
    name: string;
    arguments: Record<string, unknown>;
    result?: Record<string, unknown>;
  }>;
  policy_decisions: Array<{
    decision: "ALLOW" | "DENY" | "REQUIRE_HUMAN_REVIEW";
    rejection_reasons?: string[];
    rules_evaluated?: number;
    total_evaluation_latency_ms?: number;
    rule_diagnostics?: PolicyRuleDiagnostic[];
  }>;
  operation_ids: string[];
  latency_ms: number;
}

export interface AgentTrace {
  id: string;
  session_id: string;
  agent_id: string;
  user_prompt: string;
  model_provider: string;
  model_name: string;
  tool_name: string | null;
  tool_arguments: Record<string, unknown>;
  tool_result: Record<string, unknown>;
  operation_id: string | null;
  policy_decision: string | null;
  latency_ms: number;
  created_at: string;
}

export interface SystemMetrics {
  total_operations: number;
  succeeded_operations: number;
  failed_operations: number;
  active_reservations: number;
  webhooks_processed: number;
  webhooks_in_dlq: number;
  reconciliation_reports_count: number;
  last_reconciliation_discrepancies: number;
}

export interface DelegationNode {
  id: string;
  parent_id: string | null;
  agent_id: string;
  agent_name: string;
  agent_type: string;
  status: string;
  currency: string;
  max_amount_per_op: number;
  aggregate_spend_limit: number;
  current_spend: number;
  reserved_spend: number;
  delegated_budget: number;
  depth: number;
  valid_until: string;
}

export interface PolicyRuleMetadata {
  name: string;
  order: number;
  category: string;
  invariant: string;
  description: string;
  enforcement: string;
}

export interface PolicyRulesResponse {
  engine: string;
  rule_count: number;
  zero_gateway_dispatch_invariant: boolean;
  rules: PolicyRuleMetadata[];
}

export interface MCPToolInfo {
  name: string;
  description: string;
  category: string;
  operation_type: string | null;
  inputSchema: Record<string, unknown>;
}

export interface MCPRegistryResponse {
  total_registered_tools: number;
  functional_categories_count: number;
  categories: string[];
  tools: MCPToolInfo[];
  profiles_summary: Record<
    string,
    {
      name: string;
      allowed_operations?: string[];
      permitted_tools?: string[];
      permitted_categories?: string[];
      exposed_tools_count: number;
      attack_surface_reduction_pct: number;
      credential_exposure?: string;
      risk?: string;
    }
  >;
}

export interface BenchmarkMetrics {
  total_scenarios: number;
  adversarial_scenarios: number;
  legitimate_scenarios: number;
  unauthorized_action_block_rate: number;
  policy_bypass_rate: number;
  legitimate_action_acceptance_rate: number;
  false_positive_rate: number;
  financial_loss_prevented_inr: number;
  counterfactual_baseline_loss_inr: number;
  unauthorized_razorpay_effects: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  avg_latency_ms: number;
  baseline_comparisons: Record<
    string,
    {
      block_rate: number;
      bypass_rate: number;
      financial_loss_inr?: number;
      description?: string;
      loss_vulnerability?: string;
    }
  >;
  detailed_results: Array<{
    scenario_id: string;
    name: string;
    profile: string;
    category: string;
    expected: string;
    actual: string;
    passed: boolean;
    latency_ms: number;
    protected_inr: number;
  }>;
}

export interface DemoStepResult {
  step_number: number;
  act_name?: string;
  title: string;
  description: string;
  flow_steps?: string[];
  decision: string;
  authorized: boolean;
  gateway_calls_dispatched?: number;
  operation_id: string | null;
  amount_inr: string;
  gateway_effect: string;
  audit_trace_id: string;
  backend_state?: Record<string, unknown>;
  details: Record<string, unknown>;
}

export interface HealthCheckResponse {
  status: "ok" | "ready" | "not_ready" | "degraded" | "error";
  service?: string;
  message?: string;
  dependencies?: {
    database?: string;
    redis?: string;
  };
}

/**
 * Standard fetch helper with timeout and typed error handling.
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          if (typeof errorJson.detail === "string") {
            errorDetail = errorJson.detail;
          } else if (Array.isArray(errorJson.detail)) {
            errorDetail = errorJson.detail
              .map((e: any) => e.msg || e.message || JSON.stringify(e))
              .join("; ");
          } else {
            errorDetail = JSON.stringify(errorJson.detail);
          }
        } else if (errorJson.message) {
          errorDetail =
            typeof errorJson.message === "string"
              ? errorJson.message
              : JSON.stringify(errorJson.message);
        }
      } catch {
        // use fallback text
      }
      throw new Error(errorDetail);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(`Request timeout: ${endpoint} did not respond within 60s (backend may be cold-starting).`);
    }
    if (err instanceof TypeError && err.message.includes("fetch")) {
      throw new Error(
        `Unable to reach Mandate control plane at ${API_BASE_URL}. The free-tier cloud backend may be waking up from sleep, or CORS is not permitted. Please retry in a few seconds.`
      );
    }
    throw err;
  }
}

export const api = {
  // Health & Liveness
  getHealth: () => request<{ status: string; service: string }>("/health"),
  getReadiness: () => request<HealthCheckResponse>("/ready"),

  // Principals & Agents
  getAgents: () => request<Agent[]>("/api/v1/agents").catch(() => []),
  getAgent: (id: string) => request<Agent>(`/api/v1/agents/${id}`),
  registerAgent: (payload: {
    name: string;
    description?: string;
    agent_type?: string;
    owner_id?: string;
    metadata_json?: Record<string, unknown>;
  }) =>
    request<Agent>("/api/v1/agents", {
      method: "POST",
      body: JSON.stringify({
        owner_id: payload.owner_id || "prn_demo_merchant_01",
        name: payload.name,
        description: payload.description || "",
        agent_type: payload.agent_type || "SHOPPING",
        metadata_json: payload.metadata_json || {},
      }),
    }),
  updateAgentStatus: (agentId: string, statusVal: string, reason?: string) =>
    request<Agent>(`/api/v1/agents/${agentId}/status`, {
      method: "POST",
      body: JSON.stringify({ status: statusVal, reason }),
    }),

  // Mandates
  getMandates: (agentId?: string) =>
    request<Mandate[]>(agentId ? `/api/v1/mandates?agent_id=${agentId}` : "/api/v1/mandates"),
  getMandate: (id: string) => request<Mandate>(`/api/v1/mandates/${id}`),
  createMandate: (payload: Record<string, unknown>) =>
    request<Mandate>("/api/v1/mandates", { method: "POST", body: JSON.stringify(payload) }),
  delegateChildMandate: (parentId: string, payload: Record<string, unknown>) =>
    request<Mandate>(`/api/v1/mandates/${parentId}/delegate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  suspendMandate: (id: string, reason: string) =>
    request<Mandate>(`/api/v1/mandates/${id}/suspend`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  activateMandate: (id: string) =>
    request<Mandate>(`/api/v1/mandates/${id}/activate`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  revokeMandate: (id: string, reason: string) =>
    request<Mandate>(`/api/v1/mandates/${id}/revoke`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  getDelegationTree: () => request<DelegationNode[]>("/api/v1/mandates/graph/tree"),

  // Policy Engine
  getPolicyRules: () => request<PolicyRulesResponse>("/api/v1/policies/rules"),
  testEvaluatePolicy: (payload: {
    agent_id: string;
    mandate_id: string;
    operation_type: string;
    amount: number;
    currency?: string;
    payload?: Record<string, unknown>;
  }) =>
    request<PolicyEvaluationDetails>("/api/v1/policies/test-evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Operations & Transactions
  getOperations: (mandateId?: string) =>
    request<FinancialOperation[]>(
      mandateId ? `/api/v1/operations?mandate_id=${mandateId}` : "/api/v1/operations"
    ),
  getOperation: (id: string) => request<FinancialOperation>(`/api/v1/operations/${id}`),
  createOperation: (payload: Record<string, unknown>) =>
    request<FinancialOperation>("/api/v1/operations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  approveOperation: (id: string, approverId: string, approved: boolean, reason?: string) =>
    request<FinancialOperation>(`/api/v1/operations/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by_id: approverId, approved, reason }),
    }),

  // Audit Logs
  getAuditLogs: (limit = 100, actorId?: string, resourceId?: string) => {
    let url = `/api/v1/audit?limit=${limit}`;
    if (actorId) url += `&actor_id=${encodeURIComponent(actorId)}`;
    if (resourceId) url += `&resource_id=${encodeURIComponent(resourceId)}`;
    return request<AuditEvent[]>(url);
  },

  // MCP Gateway & Tool Registry
  getMcpRegistry: () => request<MCPRegistryResponse>("/api/v1/mcp/registry"),
  callMcpGateway: (
    agentId: string,
    method: "initialize" | "tools/list" | "tools/call",
    params: Record<string, unknown> = {},
    id: string | number = 1
  ) =>
    request<{
      jsonrpc: string;
      id: string | number;
      result?: Record<string, unknown>;
      error?: { code: number; message: string };
    }>("/api/v1/mcp", {
      method: "POST",
      headers: { "X-Agent-Id": agentId },
      body: JSON.stringify({ jsonrpc: "2.0", id, method, params }),
    }),

  // Telemetry, Reconciliation, and Failure Injection
  getMetrics: () => request<SystemMetrics>("/api/v1/telemetry/metrics"),
  triggerReconciliation: () =>
    request<{
      status: string;
      reconciled_operations_count: number;
      orphan_reservations_released: number;
      discrepancies_detected: number;
      duration_ms: number;
      details?: Record<string, unknown>;
    }>("/api/v1/telemetry/reconcile-now", { method: "POST" }),
  injectFailure: (failureType: string, parameters: Record<string, unknown> = {}) =>
    request<{
      injected: boolean;
      failure_type: string;
      behavior?: string;
      details?: Record<string, unknown>;
    }>("/api/v1/telemetry/inject-failure", {
      method: "POST",
      body: JSON.stringify({ failure_type: failureType, parameters }),
    }),

  // Agent Dialogue & Traces
  chatWithAgent: (
    agentId: string,
    message: string,
    sessionId?: string,
    history: Array<Record<string, unknown>> = []
  ) =>
    request<AgentChatResponse>(`/api/v1/agents/${agentId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId, conversation_history: history }),
    }),
  getAgentTraces: (agentId: string) => request<AgentTrace[]>(`/api/v1/agents/${agentId}/traces`),

  // Evaluation & Benchmark
  getEvaluationScenarios: () =>
    request<Array<Record<string, unknown>>>("/api/v1/evaluation/scenarios"),
  getBaselines: () =>
    request<{ models: Record<string, Record<string, unknown>> }>("/api/v1/evaluation/baselines"),
  runEvaluation: (seed = 42, multiplier = 1, agentId?: string) =>
    request<BenchmarkMetrics>("/api/v1/evaluation/run", {
      method: "POST",
      body: JSON.stringify({ seed, multiplier, agent_id: agentId }),
    }),

  // Demo Suite
  resetDemo: () =>
    request<{
      status: string;
      message: string;
      seeded_principal_id: string;
      parent_agent_id: string;
      child_agent_id: string;
      parent_mandate_id: string;
      child_mandate_id: string;
      seeded_at_utc: string;
    }>("/api/v1/demo/reset", { method: "POST" }),
  runDemoScenario: (stepNumber: number) =>
    request<DemoStepResult>("/api/v1/demo/run-scenario", {
      method: "POST",
      body: JSON.stringify({ step_number: stepNumber }),
    }),
  runDemoJourney: () =>
    request<{
      status: string;
      total_acts: number;
      total_gateway_calls: number;
      total_loss_prevented_inr: string;
      journey_steps: DemoStepResult[];
    }>("/api/v1/demo/run-journey", { method: "POST" }),
};
