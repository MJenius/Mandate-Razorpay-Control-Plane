"""Pydantic schemas for data transfer and validation."""

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


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Principal Schemas
class PrincipalCreate(BaseSchema):
    name: str = Field(..., min_length=2, max_length=128)
    email: str = Field(..., min_length=5, max_length=255)
    role: PrincipalRole = PrincipalRole.DEVELOPER


class PrincipalResponse(BaseSchema):
    id: str
    name: str
    email: str
    role: PrincipalRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Agent Schemas
class AgentCreate(BaseSchema):
    name: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = None
    owner_id: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseSchema):
    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    status: AgentStatus
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# Mandate Schemas
class MandateCreate(BaseSchema):
    agent_id: str
    granted_by_id: str
    currency: str = Field(default="INR", min_length=3, max_length=3)
    max_amount_per_op: int = Field(..., gt=0, description="In smallest currency unit (paise/cents)")
    aggregate_spend_limit: int = Field(..., gt=0, description="Total budget in smallest currency unit")
    allowed_operations: List[OperationType] = Field(default_factory=list)
    policy_config: Dict[str, Any] = Field(default_factory=dict)
    valid_until: datetime


class MandateResponse(BaseSchema):
    id: str
    agent_id: str
    granted_by_id: str
    status: MandateStatus
    currency: str
    max_amount_per_op: int
    aggregate_spend_limit: int
    current_aggregate_spend: int
    allowed_operations: List[str]
    policy_config: Dict[str, Any]
    valid_from: datetime
    valid_until: datetime
    created_at: datetime
    updated_at: datetime


# Financial Operation Schemas
class OperationCreate(BaseSchema):
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    agent_id: str
    mandate_id: str
    operation_type: OperationType
    amount: int = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    payload: Dict[str, Any] = Field(default_factory=dict)


class OperationResponse(BaseSchema):
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
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Transaction Schemas
class TransactionResponse(BaseSchema):
    id: str
    operation_id: str
    gateway_name: str
    gateway_order_id: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    gateway_refund_id: Optional[str] = None
    amount: int
    currency: str
    status: TransactionStatus
    gateway_response: Dict[str, Any]
    created_at: datetime


# Audit Event Schemas
class AuditEventResponse(BaseSchema):
    id: str
    event_id: str
    action: AuditAction
    actor_id: str
    actor_type: str
    resource_id: str
    resource_type: str
    payload: Dict[str, Any]
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    timestamp: datetime
