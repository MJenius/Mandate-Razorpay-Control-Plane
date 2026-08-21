"""SQLAlchemy ORM models representing the persistent domain layer."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from packages.core.enums import (
    AgentStatus,
    AuditAction,
    MandateStatus,
    OperationStatus,
    OperationType,
    PrincipalRole,
    TransactionStatus,
)

# Cross-dialect JSON type (Postgres JSONB with SQLite JSON fallback)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""
    pass


class Principal(Base):
    __tablename__ = "principals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    role: Mapped[PrincipalRole] = mapped_column(SQLEnum(PrincipalRole, native_enum=False), default=PrincipalRole.DEVELOPER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="owner")
    mandates_granted: Mapped[List["Mandate"]] = relationship("Mandate", back_populates="granted_by_principal")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("principals.id"), nullable=False, index=True)
    status: Mapped[AgentStatus] = mapped_column(SQLEnum(AgentStatus, native_enum=False), default=AgentStatus.ACTIVE, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(32), default="SHOPPING", nullable=False) # e.g. "SHOPPING", "SUPPORT", "CUSTOM"
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    owner: Mapped["Principal"] = relationship("Principal", back_populates="agents")
    mandates: Mapped[List["Mandate"]] = relationship("Mandate", back_populates="agent")
    operations: Mapped[List["FinancialOperation"]] = relationship("FinancialOperation", back_populates="agent")
    traces: Mapped[List["AgentExecutionTrace"]] = relationship("AgentExecutionTrace", back_populates="agent")


class Mandate(Base):
    __tablename__ = "mandates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    granted_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("principals.id"), nullable=False)
    status: Mapped[MandateStatus] = mapped_column(SQLEnum(MandateStatus, native_enum=False), default=MandateStatus.ACTIVE, nullable=False)
    
    # Financial Boundaries (in smallest currency unit, e.g. paise for INR)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    max_amount_per_op: Mapped[int] = mapped_column(BigInteger, nullable=False)
    aggregate_spend_limit: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Two-phase budget accounting
    current_aggregate_spend: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    reserved_spend: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    
    # Policy rule triggers
    review_threshold_amount: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    allowed_operations: Mapped[List[str]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    policy_config: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    suspension_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="mandates")
    granted_by_principal: Mapped["Principal"] = relationship("Principal", back_populates="mandates_granted")
    operations: Mapped[List["FinancialOperation"]] = relationship("FinancialOperation", back_populates="mandate")


class FinancialOperation(Base):
    __tablename__ = "financial_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    operation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(String(36), ForeignKey("mandates.id"), nullable=False, index=True)
    
    operation_type: Mapped[OperationType] = mapped_column(SQLEnum(OperationType, native_enum=False), nullable=False)
    status: Mapped[OperationStatus] = mapped_column(SQLEnum(OperationStatus, native_enum=False), default=OperationStatus.INITIATED, nullable=False)
    
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    policy_evaluation_details: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="operations")
    mandate: Mapped["Mandate"] = relationship("Mandate", back_populates="operations")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="operation")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    operation_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_operations.id"), nullable=False, index=True)
    
    gateway_name: Mapped[str] = mapped_column(String(32), default="RAZORPAY", nullable=False)
    gateway_order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    gateway_payment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    gateway_refund_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    gateway_payment_link_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    gateway_payment_link_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(SQLEnum(TransactionStatus, native_enum=False), default=TransactionStatus.CREATED, nullable=False)
    
    gateway_response: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    operation: Mapped["FinancialOperation"] = relationship("FinancialOperation", back_populates="transactions")


class AgentExecutionTrace(Base):
    """Stores structured tool calls, model outputs, and Mandate policy responses independently of LLM reasoning."""
    __tablename__ = "agent_execution_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(32), default="openai", nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Structured tool invocation separated from reasoning
    tool_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tool_arguments: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    tool_result: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    
    operation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    policy_decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    agent_response_text: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[float] = mapped_column(nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="traces")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    signature_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    processing_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction, native_enum=False), nullable=False)
    
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    previous_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    new_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_events_actor_timestamp", "actor_id", "timestamp"),
        Index("ix_audit_events_resource_timestamp", "resource_id", "timestamp"),
    )
