"""Initial database schema migration for Mandate.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. Principals
    op.create_table(
        "principals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="DEVELOPER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_principals_email", "principals", ["email"], unique=True)

    # 2. Agents
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("principals.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("api_key_hash", sa.String(length=256), nullable=False),
        sa.Column("agent_type", sa.String(length=32), nullable=False, server_default="SHOPPING"),
        sa.Column("metadata_json", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])
    op.create_index("ix_agents_api_key_hash", "agents", ["api_key_hash"], unique=True)

    # 3. Mandates
    op.create_table(
        "mandates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("granted_by_id", sa.String(length=36), sa.ForeignKey("principals.id"), nullable=False),
        sa.Column("parent_mandate_id", sa.String(length=36), sa.ForeignKey("mandates.id"), nullable=True),
        sa.Column("delegation_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_delegation_depth", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("max_amount_per_op", sa.BigInteger(), nullable=False),
        sa.Column("aggregate_spend_limit", sa.BigInteger(), nullable=False),
        sa.Column("current_aggregate_spend", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("reserved_spend", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("delegated_child_budget_allocated", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("review_threshold_amount", sa.BigInteger(), nullable=True),
        sa.Column("allowed_operations", json_type, nullable=False),
        sa.Column("policy_config", json_type, nullable=False),
        sa.Column("suspension_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mandates_agent_id", "mandates", ["agent_id"])
    op.create_index("ix_mandates_parent_mandate_id", "mandates", ["parent_mandate_id"])

    # 4. Financial Operations
    op.create_table(
        "financial_operations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("operation_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("mandate_id", sa.String(length=36), sa.ForeignKey("mandates.id"), nullable=False),
        sa.Column("operation_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="INITIATED"),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("policy_evaluation_details", json_type, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("approved_by_id", sa.String(length=36), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_financial_operations_operation_id", "financial_operations", ["operation_id"], unique=True)
    op.create_index("ix_financial_operations_idempotency_key", "financial_operations", ["idempotency_key"], unique=True)
    op.create_index("ix_financial_operations_agent_id", "financial_operations", ["agent_id"])
    op.create_index("ix_financial_operations_mandate_id", "financial_operations", ["mandate_id"])
    op.create_index("ix_financial_operations_trace_id", "financial_operations", ["trace_id"])

    # 5. Transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("operation_id", sa.String(length=36), sa.ForeignKey("financial_operations.id"), nullable=False),
        sa.Column("gateway_name", sa.String(length=32), nullable=False, server_default="RAZORPAY"),
        sa.Column("gateway_order_id", sa.String(length=128), nullable=True),
        sa.Column("gateway_payment_id", sa.String(length=128), nullable=True),
        sa.Column("gateway_refund_id", sa.String(length=128), nullable=True),
        sa.Column("gateway_payment_link_id", sa.String(length=128), nullable=True),
        sa.Column("gateway_payment_link_url", sa.String(length=512), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CREATED"),
        sa.Column("gateway_response", json_type, nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transactions_operation_id", "transactions", ["operation_id"])
    op.create_index("ix_transactions_gateway_order_id", "transactions", ["gateway_order_id"])
    op.create_index("ix_transactions_gateway_payment_id", "transactions", ["gateway_payment_id"])
    op.create_index("ix_transactions_gateway_refund_id", "transactions", ["gateway_refund_id"])
    op.create_index("ix_transactions_gateway_payment_link_id", "transactions", ["gateway_payment_link_id"])

    # 6. Domain Outbox Events
    op.create_table(
        "domain_outbox_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_domain_outbox_events_event_id", "domain_outbox_events", ["event_id"], unique=True)
    op.create_index("ix_domain_outbox_events_topic", "domain_outbox_events", ["topic"])
    op.create_index("ix_domain_outbox_events_event_type", "domain_outbox_events", ["event_type"])
    op.create_index("ix_domain_outbox_events_status", "domain_outbox_events", ["status"])

    # 7. Webhook Events
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", json_type, nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RECEIVED"),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("processing_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"], unique=True)
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"])
    op.create_index("ix_webhook_events_payload_hash", "webhook_events", ["payload_hash"])
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"])
    op.create_index("ix_webhook_events_processed", "webhook_events", ["processed"])
    op.create_index("ix_webhook_events_trace_id", "webhook_events", ["trace_id"])

    # 8. Reconciliation Reports
    op.create_table(
        "reconciliation_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("total_audited", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inconsistencies_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("details", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reconciliation_reports_report_id", "reconciliation_reports", ["report_id"], unique=True)

    # 9. Agent Execution Traces
    op.create_table(
        "agent_execution_traces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("model_provider", sa.String(length=32), nullable=False, server_default="openai"),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=True),
        sa.Column("tool_arguments", json_type, nullable=False),
        sa.Column("tool_result", json_type, nullable=False),
        sa.Column("operation_id", sa.String(length=64), nullable=True),
        sa.Column("policy_decision", sa.String(length=32), nullable=True),
        sa.Column("agent_response_text", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_execution_traces_session_id", "agent_execution_traces", ["session_id"])
    op.create_index("ix_agent_execution_traces_agent_id", "agent_execution_traces", ["agent_id"])
    op.create_index("ix_agent_execution_traces_operation_id", "agent_execution_traces", ["operation_id"])

    # 10. Audit Events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("previous_state", json_type, nullable=True),
        sa.Column("new_state", json_type, nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_event_id", "audit_events", ["event_id"], unique=True)
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_resource_id", "audit_events", ["resource_id"])
    op.create_index("ix_audit_events_trace_id", "audit_events", ["trace_id"])
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])
    op.create_index("ix_audit_events_actor_timestamp", "audit_events", ["actor_id", "timestamp"])
    op.create_index("ix_audit_events_resource_timestamp", "audit_events", ["resource_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("agent_execution_traces")
    op.drop_table("reconciliation_reports")
    op.drop_table("webhook_events")
    op.drop_table("domain_outbox_events")
    op.drop_table("transactions")
    op.drop_table("financial_operations")
    op.drop_table("mandates")
    op.drop_table("agents")
    op.drop_table("principals")
