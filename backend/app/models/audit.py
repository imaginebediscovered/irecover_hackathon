"""
Audit Trail and Dev Console Logging Models
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, JSON, Text, Index
from datetime import datetime

from app.db.database import Base


class WorkflowSession(Base):
    """Workflow session for tracking complete orchestration."""
    
    __tablename__ = "workflow_sessions"
    
    id = Column(String(50), primary_key=True)
    disruption_id = Column(String(50), nullable=True, index=True)
    
    # State
    current_state = Column(String(30), default="IDLE")
    current_agent = Column(String(50), nullable=True)
    
    # Progress
    completed_steps = Column(JSON, default=list)
    pending_steps = Column(JSON, default=list)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_duration_ms = Column(Integer, nullable=True)
    
    # Results
    status = Column(String(20), default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, FAILED
    error = Column(Text, nullable=True)
    
    # Counts
    total_thinking_steps = Column(Integer, default=0)
    total_tool_calls = Column(Integer, default=0)
    total_llm_requests = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ThinkingLog(Base):
    """Agent thinking/reasoning log for dev console."""
    
    __tablename__ = "thinking_logs"
    
    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), nullable=False, index=True)
    
    # Agent info
    agent_name = Column(String(50), nullable=False, index=True)
    step = Column(String(100), nullable=False)
    sequence = Column(Integer, default=0)
    
    # Reasoning
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, default=0.5)
    decision = Column(Text, nullable=True)
    
    # Context
    data_considered = Column(JSON, default=dict)
    
    # Timing
    duration_ms = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_thinking_logs_workflow_agent', 'workflow_id', 'agent_name'),
    )

# Alias for backward compatibility
AgentThinkingLog = ThinkingLog


class ToolInvocation(Base):
    """Tool/function call log for dev console."""
    
    __tablename__ = "tool_invocations"
    
    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), nullable=False, index=True)
    
    # Tool info
    agent = Column(String(50), nullable=False)
    tool = Column(String(100), nullable=False, index=True)
    sequence = Column(Integer, default=0)
    
    # Input/Output
    inputs = Column(JSON, default=dict)
    outputs = Column(JSON, default=dict)
    
    # Status
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    
    # Timing
    duration_ms = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_tool_invocations_workflow_tool', 'workflow_id', 'tool'),
    )


class LLMRequest(Base):
    """LLM API request log for dev console."""
    
    __tablename__ = "llm_requests"
    
    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), nullable=False, index=True)
    
    # Request info
    agent = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    sequence = Column(Integer, default=0)
    
    # Prompts (can be large)
    system_prompt = Column(Text, nullable=True)
    user_prompt = Column(Text, nullable=True)
    tool_definitions = Column(JSON, default=list)
    
    # Response
    response = Column(Text, nullable=True)
    tool_calls = Column(JSON, default=list)
    
    # Token usage
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Status
    finish_reason = Column(String(20), nullable=True)  # stop, tool_calls, length, error
    error = Column(Text, nullable=True)
    
    # Timing
    latency_ms = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class ExecutionLog(Base):
    """General execution log for dev console."""
    
    __tablename__ = "execution_logs"
    
    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), nullable=False, index=True)
    
    # Log info
    level = Column(String(10), nullable=False, index=True)  # DEBUG, INFO, WARN, ERROR, HANDOFF
    source = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    
    # Context
    log_metadata = Column(JSON, default=dict)
    
    # Tracing
    trace_id = Column(String(50), nullable=True)
    span_id = Column(String(50), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_execution_logs_workflow_level', 'workflow_id', 'level'),
        Index('ix_execution_logs_workflow_timestamp', 'workflow_id', 'timestamp'),
    )


class AuditTrail(Base):
    """Audit trail for compliance and decision tracking."""
    
    __tablename__ = "audit_trails"
    
    id = Column(String(50), primary_key=True)
    disruption_id = Column(String(50), nullable=False, index=True)
    
    # Action
    action = Column(String(50), nullable=False)  # DETECTED, ANALYZED, APPROVED, EXECUTED, etc.
    actor = Column(String(100), nullable=False)  # Agent name or user email
    actor_type = Column(String(20), nullable=False)  # SYSTEM, AGENT, USER
    
    # Details
    description = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    
    # Context
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    
    # Rationale (for agent decisions)
    rationale = Column(Text, nullable=True)
    signals_considered = Column(JSON, default=list)
    constraints_checked = Column(JSON, default=list)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_audit_trails_disruption_action', 'disruption_id', 'action'),
    )


# Aliases for backward compatibility with routes
ToolInvocationLog = ToolInvocation
LLMRequestLog = LLMRequest
