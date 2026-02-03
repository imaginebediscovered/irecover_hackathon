"""
Approval Database Model
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, Enum as SQLEnum, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.database import Base


class ApprovalLevel(str, enum.Enum):
    """Approval level enumeration."""
    AUTO = "AUTO"
    SUPERVISOR = "SUPERVISOR"
    MANAGER = "MANAGER"
    EXECUTIVE = "EXECUTIVE"


class ApprovalStatus(str, enum.Enum):
    """Approval status enumeration."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    ESCALATED = "ESCALATED"
    AUTO_APPROVED = "AUTO_APPROVED"


class Approval(Base):
    """Approval record for disruption recovery."""
    
    __tablename__ = "approvals"
    
    id = Column(String(50), primary_key=True)
    disruption_id = Column(String(50), ForeignKey("disruptions.id"), nullable=False, unique=True, index=True)
    
    # Approval routing
    required_level = Column(SQLEnum(ApprovalLevel), default=ApprovalLevel.SUPERVISOR)
    current_level = Column(SQLEnum(ApprovalLevel), default=ApprovalLevel.SUPERVISOR)
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True)
    
    # Assignment
    assigned_to = Column(String(100), nullable=True)
    assigned_to_email = Column(String(200), nullable=True)
    
    # Decision
    decision_by = Column(String(100), nullable=True)
    decision_by_email = Column(String(200), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    selected_scenario_id = Column(String(50), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Risk assessment
    risk_score = Column(Float, default=0.5)
    risk_factors = Column(JSON, default=list)  # [{factor, weight, value}]
    auto_approve_eligible = Column(Boolean, default=False)
    
    # Escalation
    escalation_count = Column(Integer, default=0)
    escalated_from = Column(String(100), nullable=True)
    escalation_reason = Column(String(200), nullable=True)
    
    # Timeout
    timeout_at = Column(DateTime, nullable=True)
    timeout_minutes = Column(Integer, default=10)
    
    # Comments
    comments = Column(JSON, default=list)  # [{user, comment, timestamp}]
    
    # Timestamps
    requested_at = Column(DateTime, default=datetime.utcnow)
    notification_sent_at = Column(DateTime, nullable=True)
    first_viewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    disruption = relationship("Disruption", back_populates="approval")
    
    def __repr__(self):
        return f"<Approval {self.id} {self.status.value}>"


class ExecutionStep(Base):
    """Execution step log for recovery actions."""
    
    __tablename__ = "execution_steps"
    
    id = Column(String(50), primary_key=True)
    disruption_id = Column(String(50), ForeignKey("disruptions.id"), nullable=False, index=True)
    
    # Step details
    step_number = Column(Integer, nullable=False)
    action_type = Column(String(50), nullable=False)  # BOOK_AWB, RESERVE_SLOT, ALLOCATE_ULD, etc.
    action_target = Column(String(100), nullable=True)  # AWB number, flight, ULD, etc.
    
    # Status
    status = Column(String(20), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, FAILED, ROLLED_BACK
    
    # Input/Output
    input_params = Column(JSON, default=dict)
    output_result = Column(JSON, default=dict)
    
    # References
    reference_id = Column(String(100), nullable=True)  # Booking ref, slot ID, etc.
    rollback_reference = Column(String(100), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Rollback
    rolled_back = Column(Boolean, default=False)
    rolled_back_at = Column(DateTime, nullable=True)
    rollback_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    disruption = relationship("Disruption", back_populates="execution_steps")
    
    def __repr__(self):
        return f"<ExecutionStep {self.step_number} {self.action_type} {self.status}>"
