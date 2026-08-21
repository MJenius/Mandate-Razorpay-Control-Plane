"""Pydantic request and response schemas for API serialization."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from packages.core.enums import (
    AgentStatus,
    AuditAction,
    MandateStatus,
    OperationStatus,
    OperationType,
    PrincipalRole,
    TransactionStatus,
)


class PrincipalCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    email: str = Field(..., min_length=5, max_length=255)
    role: PrincipalRole = PrincipalRole.DEVELOPER


class PrincipalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: PrincipalRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = None
    owner_id: str
    agent_type: str = "SHOPPING"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class AgentStatusUpdate(BaseModel):
    status: AgentStatus
    reason: Optional[str] = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    owner_id: str
    status: AgentStatus
    agent_type: str
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MandateCreate(BaseModel):
    agent_id: str
    granted_by_id: str
    currency: str = "INR"
    max_amount_per_op: int = Field(..., gt=0, description="Amount in smallest unit, e.g. paise for INR")
    aggregate_spend_limit: int = Field(..., gt=0, description="Amount in smallest unit, e.g. paise for INR")
    review_threshold_amount: Optional[int] = Field(None, gt=0)
    allowed_operations: List[str] = Field(default_factory=list)
    policy_config: Dict[str, Any] = Field(default_factory=dict)
    valid_until: datetime


class MandateDelegateRequest(BaseModel):
    """Request to delegate a bounded child sub-mandate to another agent."""
    target_agent_id: str
    currency: Optional[str] = None
    max_amount_per_op: int = Field(..., gt=0, description="Must be <= parent.max_amount_per_op")
    aggregate_spend_limit: int = Field(..., gt=0, description="Must be <= parent available budget")
    review_threshold_amount: Optional[int] = None
    allowed_operations: List[str] = Field(default_factory=list, description="Must be subset of parent allowed operations")
    valid_until: datetime = Field(..., description="Must be <= parent.valid_until")


class MandateStatusUpdate(BaseModel):
    reason: Optional[str] = None


class MandateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    granted_by_id: str
    parent_mandate_id: Optional[str] = None
    delegation_depth: int = 0
    max_delegation_depth: int = 2
    status: MandateStatus
    currency: str
    max_amount_per_op: int
    aggregate_spend_limit: int
    current_aggregate_spend: int
    reserved_spend: int
    delegated_child_budget_allocated: int = 0
    review_threshold_amount: Optional[int]
    allowed_operations: List[str]
    policy_config: Dict[str, Any]
    suspension_reason: Optional[str]
    version: int
    valid_from: datetime
    valid_until: datetime
    created_at: datetime
    updated_at: datetime


class OperationCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    agent_id: str
    mandate_id: str
    operation_type: OperationType
    amount: int = Field(..., gt=0)
    currency: str = "INR"
    payload: Dict[str, Any] = Field(default_factory=dict)


class HumanApprovalRequest(BaseModel):
    approved_by_id: str
    approved: bool
    reason: Optional[str] = None


class OperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operation_id: str
    idempotency_key: str
    agent_id: str
    mandate_id: str
    operation_type: OperationType
    status: OperationStatus
    amount: int
    currency: str
    payload: Dict[str, Any]
    policy_evaluation_details: Dict[str, Any]
    error_message: Optional[str]
    approved_by_id: Optional[str]
    trace_id: str
    created_at: datetime
    updated_at: datetime


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operation_id: str
    gateway_name: str
    gateway_order_id: Optional[str]
    gateway_payment_id: Optional[str]
    gateway_refund_id: Optional[str]
    gateway_payment_link_id: Optional[str]
    gateway_payment_link_url: Optional[str]
    amount: int
    currency: str
    status: TransactionStatus
    gateway_response: Dict[str, Any]
    error_code: Optional[str]
    error_description: Optional[str]
    created_at: datetime
    updated_at: datetime


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class RefundCreateRequest(BaseModel):
    payment_id: str
    amount: Optional[int] = None
    notes: Dict[str, Any] = Field(default_factory=dict)


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    event_type: str
    status: str
    processed: bool
    processing_attempts: int
    error_message: Optional[str]
    received_at: datetime
    processed_at: Optional[datetime]


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    action: AuditAction
    actor_id: str
    actor_type: str
    resource_id: str
    resource_type: str
    payload: Dict[str, Any]
    previous_state: Optional[Dict[str, Any]]
    new_state: Optional[Dict[str, Any]]
    trace_id: Optional[str]
    timestamp: datetime
