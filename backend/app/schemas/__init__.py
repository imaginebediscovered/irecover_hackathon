"""
Pydantic Schemas for API Request/Response
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DisruptionStatusEnum(str, Enum):
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class ApprovalLevelEnum(str, Enum):
    AUTO = "AUTO"
    SUPERVISOR = "SUPERVISOR"
    MANAGER = "MANAGER"
    EXECUTIVE = "EXECUTIVE"


class ApprovalStatusEnum(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    ESCALATED = "ESCALATED"
    AUTO_APPROVED = "AUTO_APPROVED"


class ScenarioTypeEnum(str, Enum):
    REPROTECT = "REPROTECT"
    REROUTE = "REROUTE"
    INTERLINE = "INTERLINE"
    TRUCK = "TRUCK"
    SPLIT = "SPLIT"


# ==================== Flight Schemas ====================

class FlightBase(BaseModel):
    flight_number: str
    origin: str = Field(max_length=3)
    destination: str = Field(max_length=3)
    scheduled_departure: datetime
    scheduled_arrival: datetime


class FlightResponse(FlightBase):
    id: str
    status: str
    delay_minutes: int = 0
    aircraft_type: Optional[str] = None
    available_capacity_kg: float = 0
    has_temperature_control: bool = False

    class Config:
        from_attributes = True


class FlightDetailResponse(FlightResponse):
    estimated_departure: Optional[datetime] = None
    estimated_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    delay_reason: Optional[str] = None
    aircraft_registration: Optional[str] = None
    cargo_capacity_kg: float = 0
    booked_weight_kg: float = 0


# ==================== AWB Schemas ====================

class AWBBase(BaseModel):
    awb_number: str
    origin: str = Field(max_length=3)
    destination: str = Field(max_length=3)
    pieces: int = 1
    weight_kg: float


class AWBResponse(AWBBase):
    customer_id: str
    customer_name: Optional[str] = None
    commodity: Optional[str] = None
    priority: str = "STANDARD"
    sla_commitment: Optional[datetime] = None
    is_dangerous_goods: bool = False
    is_temperature_controlled: bool = False

    class Config:
        from_attributes = True


class AWBDetailResponse(AWBResponse):
    final_destination: Optional[str] = None
    commodity_type: str = "GENERAL"
    dg_class: Optional[str] = None
    temp_min_celsius: Optional[float] = None
    temp_max_celsius: Optional[float] = None
    special_handling_codes: List[str] = []
    current_location: Optional[str] = None
    status: str = "BOOKED"


# ==================== Disruption Schemas ====================

class DisruptionBase(BaseModel):
    flight_number: str
    origin: str
    destination: str
    disruption_type: str
    delay_minutes: int = 0


class DisruptionCreate(DisruptionBase):
    flight_id: str
    flight_date: datetime
    severity: SeverityEnum
    delay_reason: Optional[str] = None


class DisruptionResponse(BaseModel):
    id: str
    flight_number: str
    origin: str
    destination: str
    flight_date: datetime
    disruption_type: str
    severity: SeverityEnum
    status: DisruptionStatusEnum
    delay_minutes: int = 0
    total_awbs_affected: int = 0
    critical_awbs_count: int = 0
    revenue_at_risk: float = 0
    detected_at: datetime

    class Config:
        from_attributes = True


class DisruptionDetailResponse(DisruptionResponse):
    delay_reason: Optional[str] = None
    original_aircraft_type: Optional[str] = None
    new_aircraft_type: Optional[str] = None
    capacity_reduction_percent: float = 0
    sla_breach_count: int = 0
    selected_scenario_id: Optional[str] = None
    analysis_completed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ==================== Impact Schemas ====================

class AWBImpactResponse(BaseModel):
    id: str
    awb_number: str
    original_eta: Optional[datetime] = None
    new_eta: Optional[datetime] = None
    sla_commitment: Optional[datetime] = None
    time_to_breach_minutes: Optional[int] = None
    breach_risk: str = "LOW"
    revenue_at_risk: float = 0
    is_critical: bool = False
    dg_compatible: Optional[bool] = None
    temp_compatible: Optional[bool] = None
    embargo_clear: Optional[bool] = None
    resolved: bool = False

    class Config:
        from_attributes = True


# ==================== Scenario Schemas ====================

class ConstraintResult(BaseModel):
    constraint: str
    passed: bool
    details: str


class RecoveryScenarioResponse(BaseModel):
    id: str
    scenario_type: ScenarioTypeEnum
    description: Optional[str] = None
    target_flight_number: Optional[str] = None
    target_departure: Optional[datetime] = None
    sla_saved_count: int = 0
    sla_at_risk_count: int = 0
    risk_score: float = 0.5
    execution_time_minutes: int = 0
    estimated_cost: float = 0
    constraint_results: Dict[str, ConstraintResult] = {}
    all_constraints_satisfied: bool = False
    is_recommended: bool = False
    recommendation_reason: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Approval Schemas ====================

class ApprovalResponse(BaseModel):
    id: str
    disruption_id: str
    required_level: ApprovalLevelEnum
    status: ApprovalStatusEnum
    risk_score: float = 0.5
    auto_approve_eligible: bool = False
    assigned_to: Optional[str] = None
    requested_at: datetime
    timeout_at: Optional[datetime] = None
    decision_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    selected_scenario_id: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    scenario_id: str
    comments: Optional[str] = None


class ApprovalRejectRequest(BaseModel):
    reason: str


# ==================== Execution Schemas ====================

class ExecutionStepResponse(BaseModel):
    id: str
    step_number: int
    action_type: str
    action_target: Optional[str] = None
    status: str
    reference_id: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


# ==================== Dev Console Schemas ====================

class WorkflowStateResponse(BaseModel):
    workflow_id: str
    current_state: str
    current_agent: Optional[str] = None
    completed_steps: List[str] = []
    pending_steps: List[str] = []
    started_at: datetime
    status: str = "IN_PROGRESS"
    error: Optional[str] = None


class ThinkingLogResponse(BaseModel):
    id: str
    timestamp: datetime
    agent: str
    step: str
    reasoning: str
    confidence: float
    decision: Optional[str] = None
    duration_ms: int = 0
    sequence: int = 0

    class Config:
        from_attributes = True


class ToolInvocationResponse(BaseModel):
    id: str
    timestamp: datetime
    agent: str
    tool: str
    inputs: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}
    success: bool = True
    error: Optional[str] = None
    duration_ms: int = 0
    sequence: int = 0

    class Config:
        from_attributes = True


class LLMRequestResponse(BaseModel):
    id: str
    timestamp: datetime
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    finish_reason: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = []
    sequence: int = 0

    class Config:
        from_attributes = True


class LLMRequestDetailResponse(LLMRequestResponse):
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    response: Optional[str] = None
    tool_definitions: List[Dict[str, Any]] = []


class ExecutionLogResponse(BaseModel):
    id: str
    timestamp: datetime
    level: str
    source: str
    message: str
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class WorkflowDetailResponse(BaseModel):
    workflow: WorkflowStateResponse
    thinking_logs: List[ThinkingLogResponse] = []
    tool_invocations: List[ToolInvocationResponse] = []
    llm_requests: List[LLMRequestResponse] = []
    execution_logs: List[ExecutionLogResponse] = []


# ==================== Audit Trail Schemas ====================

class AuditTrailResponse(BaseModel):
    id: str
    disruption_id: str
    action: str
    actor: str
    actor_type: str
    description: Optional[str] = None
    details: Dict[str, Any] = {}
    rationale: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# ==================== Dev Console Extended Schemas ====================

class AgentThinkingLogResponse(BaseModel):
    """Response schema for agent thinking logs."""
    id: str
    workflow_id: str
    agent_name: str
    step_name: Optional[str] = None
    thinking_content: str
    confidence_score: Optional[float] = None
    timestamp: datetime
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class LLMRequestLogResponse(BaseModel):
    """Response schema for LLM request logs."""
    id: str
    workflow_id: str
    agent_name: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    timestamp: datetime
    status: str = "success"
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ToolInvocationLogResponse(BaseModel):
    """Response schema for tool invocation logs."""
    id: str
    workflow_id: str
    agent_name: str
    tool_name: str
    tool_category: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    status: str = "success"
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DevConsoleState(BaseModel):
    """Current state of the dev console."""
    connected_clients: int = 0
    recent_thinking_logs: int = 0
    recent_llm_requests: int = 0
    recent_tool_invocations: int = 0
    recent_errors: int = 0
    active_workflows: List[str] = []
    timestamp: str
