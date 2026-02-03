"""
iRecover Agentic AI System

Multi-Agent Architecture for Autonomous Cargo Recovery

Agents:
- Orchestrator: Root coordinator for end-to-end workflow
- Detection Agent: Monitors and detects cargo disruptions (12 types)
- Impact Agent: Assesses impact on AWBs and calculates risks
- Replan Agent: Generates recovery scenarios (reprotect, reroute, interline, truck)
- Approval Agent: Manages human-in-the-loop workflows
- Execution Agent: Executes approved recovery plans with rollback
- Notification Agent: Handles multi-channel stakeholder communications
- Learning Agent: Captures outcomes and improves future decisions

Workflow: Detect → Analyze → Replan → Approve → Execute → Notify → Learn
"""

from app.agents.base import AgentContext, AgentState, BaseAgent
from app.agents.orchestrator import RecoveryOrchestrator, get_orchestrator
from app.agents.detection_agent import DetectionAgent
from app.agents.impact_agent import ImpactAgent
from app.agents.replan_agent import ReplanAgent
from app.agents.approval_agent import ApprovalAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.learning_agent import LearningAgent

__all__ = [
    # Base classes
    "AgentContext",
    "AgentState", 
    "BaseAgent",
    # Orchestrator
    "RecoveryOrchestrator",
    "get_orchestrator",
    # Sub-agents
    "DetectionAgent",
    "ImpactAgent",
    "ReplanAgent",
    "ApprovalAgent",
    "ExecutionAgent",
    "NotificationAgent",
    "LearningAgent",
]
