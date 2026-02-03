"""
Disruption Database Model
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, Enum as SQLEnum, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.database import Base


class DisruptionSeverity(str, enum.Enum):
    """Disruption severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DisruptionStatus(str, enum.Enum):
    """Disruption processing status."""
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class DisruptionType(str, enum.Enum):
    """Type of disruption."""
    # Flight-related disruptions
    DELAY = "DELAY"
    CANCELLATION = "CANCELLATION"
    DIVERSION = "DIVERSION"
    
    # Aircraft-related disruptions
    AIRCRAFT_CHANGE = "AIRCRAFT_CHANGE"
    CAPACITY_REDUCTION = "CAPACITY_REDUCTION"
    
    # External factors
    WEATHER = "WEATHER"
    SLOT_CHANGE = "SLOT_CHANGE"
    GROUND_HANDLING = "GROUND_HANDLING"
    EMBARGO = "EMBARGO"
    
    # Cargo-specific disruptions
    MISSED_CONNECTION = "MISSED_CONNECTION"
    TEMPERATURE_EXCURSION = "TEMPERATURE_EXCURSION"
    PRIORITY_BUMP = "PRIORITY_BUMP"
    
    # Other
    OTHER = "OTHER"


class Disruption(Base):
    """Disruption event model."""
    
    __tablename__ = "disruptions"
    
    id = Column(String(50), primary_key=True)
    
    # Flight reference
    flight_id = Column(String(50), ForeignKey("flights.id"), nullable=False, index=True)
    flight_number = Column(String(10), nullable=False, index=True)
    flight_date = Column(DateTime, nullable=False)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    
    # Disruption details
    disruption_type = Column(SQLEnum(DisruptionType), nullable=False)
    severity = Column(SQLEnum(DisruptionSeverity), nullable=False, index=True)
    status = Column(SQLEnum(DisruptionStatus), default=DisruptionStatus.DETECTED, index=True)
    
    # Delay info
    delay_minutes = Column(Integer, default=0)
    delay_reason = Column(String(100), nullable=True)
    
    # Aircraft change info
    original_aircraft_type = Column(String(20), nullable=True)
    new_aircraft_type = Column(String(20), nullable=True)
    capacity_reduction_percent = Column(Float, default=0)
    
    # Impact summary
    total_awbs_affected = Column(Integer, default=0)
    critical_awbs_count = Column(Integer, default=0)
    revenue_at_risk = Column(Float, default=0)
    sla_breach_count = Column(Integer, default=0)
    
    # Selected recovery
    selected_scenario_id = Column(String(50), nullable=True)
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow)
    analysis_started_at = Column(DateTime, nullable=True)
    analysis_completed_at = Column(DateTime, nullable=True)
    approval_requested_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    flight = relationship("Flight")
    awb_impacts = relationship("AWBImpact", back_populates="disruption")
    scenarios = relationship("RecoveryScenario", back_populates="disruption")
    approval = relationship("Approval", back_populates="disruption", uselist=False)
    execution_steps = relationship("ExecutionStep", back_populates="disruption")
    
    def __repr__(self):
        return f"<Disruption {self.id} {self.flight_number} {self.severity.value}>"


class AWBImpact(Base):
    """Impact of disruption on individual AWB."""
    
    __tablename__ = "awb_impacts"
    
    id = Column(String(50), primary_key=True)
    disruption_id = Column(String(50), ForeignKey("disruptions.id"), nullable=False, index=True)
    awb_number = Column(String(20), ForeignKey("awbs.awb_number"), nullable=False, index=True)
    
    # SLA impact
    original_eta = Column(DateTime, nullable=True)
    new_eta = Column(DateTime, nullable=True)
    sla_commitment = Column(DateTime, nullable=True)
    time_to_breach_minutes = Column(Integer, nullable=True)
    breach_risk = Column(String(20), default="LOW")  # LOW, MEDIUM, HIGH, IMMINENT
    
    # Revenue impact
    revenue_at_risk = Column(Float, default=0)
    penalty_amount = Column(Float, default=0)
    
    # Priority
    is_critical = Column(Boolean, default=False)
    customer_priority = Column(Integer, default=3)
    
    # Constraint status
    dg_compatible = Column(Boolean, nullable=True)
    temp_compatible = Column(Boolean, nullable=True)
    embargo_clear = Column(Boolean, nullable=True)
    
    # Resolution
    recovery_action = Column(String(50), nullable=True)
    new_flight_id = Column(String(50), nullable=True)
    resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    disruption = relationship("Disruption", back_populates="awb_impacts")
    awb = relationship("AWB", back_populates="impacts")


class RecoveryScenario(Base):
    """Recovery scenario generated by replan agent."""
    
    __tablename__ = "recovery_scenarios"
    
    id = Column(String(50), primary_key=True)
    disruption_id = Column(String(50), ForeignKey("disruptions.id"), nullable=False, index=True)
    
    # Scenario type
    scenario_type = Column(String(20), nullable=False)  # REPROTECT, REROUTE, INTERLINE, TRUCK, SPLIT
    description = Column(Text, nullable=True)
    
    # Target
    target_flight_id = Column(String(50), nullable=True)
    target_flight_number = Column(String(10), nullable=True)
    target_departure = Column(DateTime, nullable=True)
    target_arrival = Column(DateTime, nullable=True)
    routing = Column(JSON, default=list)  # List of flight legs
    
    # Scores
    sla_saved_count = Column(Integer, default=0)
    sla_at_risk_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.5)  # 0-1, lower is better
    cost_score = Column(Float, default=0)
    customer_impact_score = Column(Float, default=0)
    overall_score = Column(Float, default=0)  # Weighted combination
    
    # Execution
    execution_time_minutes = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0)
    
    # Constraints
    constraint_results = Column(JSON, default=dict)  # {constraint: {passed, details}}
    all_constraints_satisfied = Column(Boolean, default=False)
    
    # Recommendation
    is_recommended = Column(Boolean, default=False)
    recommendation_reason = Column(Text, nullable=True)
    
    # Optimization details
    optimization_solver = Column(String(50), nullable=True)
    optimization_objective = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    disruption = relationship("Disruption", back_populates="scenarios")
    
    def __repr__(self):
        return f"<RecoveryScenario {self.id} {self.scenario_type}>"
