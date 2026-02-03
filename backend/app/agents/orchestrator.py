"""
Root Orchestrator Agent

The central coordinator that orchestrates all sub-agents for end-to-end
cargo recovery workflow: Detect → Analyze → Replan → Approve → Execute → Notify

This is the "brain" of the iRecover agentic system.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid
import asyncio
import structlog

from app.agents.base import AgentContext, AgentState
from app.agents.detection_agent import DetectionAgent
from app.agents.impact_agent import ImpactAgent
from app.agents.replan_agent import ReplanAgent
from app.agents.approval_agent import ApprovalAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.notification_agent import NotificationAgent
from app.api.websocket import broadcast_workflow_status

logger = structlog.get_logger()


class WorkflowState(str, Enum):
    """States of the recovery workflow."""
    IDLE = "IDLE"
    DETECTING = "DETECTING"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    APPROVING = "APPROVING"
    EXECUTING = "EXECUTING"
    NOTIFYING = "NOTIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    ESCALATED = "ESCALATED"


class WorkflowSession:
    """
    Maintains state across the entire recovery workflow.
    Enables replay, rollback, and audit trails.
    """
    
    def __init__(self, workflow_id: str, disruption_id: str):
        self.workflow_id = workflow_id
        self.disruption_id = disruption_id
        self.state = WorkflowState.IDLE
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        
        # State snapshots for replay capability
        self.state_snapshots: Dict[str, Dict[str, Any]] = {}
        
        # Execution results from each phase
        self.detection_result: Optional[Dict[str, Any]] = None
        self.impact_result: Optional[Dict[str, Any]] = None
        self.replan_result: Optional[Dict[str, Any]] = None
        self.approval_result: Optional[Dict[str, Any]] = None
        self.execution_result: Optional[Dict[str, Any]] = None
        self.notification_result: Optional[Dict[str, Any]] = None
        
        # Rollback tracking
        self.executed_actions: List[Dict[str, Any]] = []
        self.rollback_actions: List[Dict[str, Any]] = []
        
        # Audit trail
        self.audit_log: List[Dict[str, Any]] = []
        
    def save_snapshot(self, phase: str, data: Dict[str, Any]):
        """Save state snapshot for potential replay."""
        self.state_snapshots[phase] = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data.copy()
        }
        
    def log_action(self, action: str, actor: str, details: Dict[str, Any] = None):
        """Add entry to audit log."""
        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "actor": actor,
            "details": details or {},
            "workflow_state": self.state.value
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "workflow_id": self.workflow_id,
            "disruption_id": self.disruption_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "detection_result": self.detection_result,
            "impact_result": self.impact_result,
            "replan_result": self.replan_result,
            "approval_result": self.approval_result,
            "execution_result": self.execution_result,
            "notification_result": self.notification_result,
            "audit_log": self.audit_log
        }


class RecoveryOrchestrator:
    """
    Root Orchestrator - Coordinates all sub-agents for end-to-end recovery.
    
    Key Responsibilities:
    1. Coordinate agent handoffs in correct sequence
    2. Maintain workflow state and session
    3. Handle failures and trigger rollbacks
    4. Emit real-time status updates for observability
    5. Support workflow replay from any checkpoint
    """
    
    def __init__(self):
        # Initialize all sub-agents
        self.detection_agent = DetectionAgent()
        self.impact_agent = ImpactAgent()
        self.replan_agent = ReplanAgent()
        self.approval_agent = ApprovalAgent()
        self.execution_agent = ExecutionAgent()
        self.notification_agent = NotificationAgent()
        
        # Active workflows
        self._active_sessions: Dict[str, WorkflowSession] = {}
        
        logger.info("RecoveryOrchestrator initialized with all sub-agents")
    
    async def handle_disruption_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point - Process a disruption event through full recovery workflow.
        
        Workflow: Detect → Analyze → Replan → Approve → Execute → Notify
        
        Args:
            event: Flight disruption event with:
                - flight_id: ID of affected flight
                - event_type: DELAY, CANCELLATION, WEATHER, etc.
                - Additional event-specific fields
                
        Returns:
            Complete workflow result with all phase outcomes
        """
        # Create workflow session
        workflow_id = str(uuid.uuid4())
        disruption_id = event.get("disruption_id", str(uuid.uuid4()))
        session = WorkflowSession(workflow_id, disruption_id)
        self._active_sessions[workflow_id] = session
        
        # Create agent context
        context = AgentContext(
            workflow_id=workflow_id,
            disruption_id=disruption_id,
            data={"flight_event": event}
        )
        
        try:
            # ==========================================
            # PHASE 1: DETECTION
            # ==========================================
            session.state = WorkflowState.DETECTING
            await self._emit_status(session, "Starting disruption detection")
            session.log_action("workflow_started", "orchestrator", {"event": event})
            
            context = await self.detection_agent.process(context)
            session.detection_result = self._extract_phase_result(context, "detection")
            session.save_snapshot("detection", context.data)
            
            # Check if this is actually a disruption
            if not context.get_data("disruption_detected", False):
                session.state = WorkflowState.COMPLETED
                session.log_action("no_disruption_detected", "detection_agent")
                await self._emit_status(session, "No significant disruption detected")
                return self._build_result(session, "NO_DISRUPTION")
            
            # For LOW severity, might not need full workflow
            severity = context.get_data("severity", "MEDIUM")
            if severity == "LOW" and not context.get_data("requires_immediate_action", False):
                session.log_action("low_priority_handled", "orchestrator")
                # Still run impact and notify but skip heavy replanning
                pass  # Continue with workflow for now
            
            # ==========================================
            # PHASE 2: IMPACT ANALYSIS
            # ==========================================
            session.state = WorkflowState.ANALYZING
            await self._emit_status(session, "Analyzing disruption impact on cargo")
            
            context = await self.impact_agent.process(context)
            session.impact_result = self._extract_phase_result(context, "impact")
            session.save_snapshot("impact", context.data)
            
            # Check if recovery is needed
            if not context.get_data("needs_recovery", True):
                session.state = WorkflowState.COMPLETED
                session.log_action("recovery_not_needed", "impact_agent")
                await self._emit_status(session, "No cargo recovery needed")
                return self._build_result(session, "NO_RECOVERY_NEEDED")
            
            # ==========================================
            # PHASE 3: REPLAN GENERATION
            # ==========================================
            session.state = WorkflowState.PLANNING
            await self._emit_status(session, "Generating recovery scenarios")
            
            context = await self.replan_agent.process(context)
            session.replan_result = self._extract_phase_result(context, "replan")
            session.save_snapshot("replan", context.data)
            
            # Normalize and validate replan outputs before approval
            scenarios = context.get_data("recovery_scenarios", [])
            recommended = context.get_data("recommended_scenario")
            
            if not scenarios:
                session.state = WorkflowState.ESCALATED
                session.log_action("no_viable_options", "replan_agent")
                await self._emit_status(session, "No viable recovery options - escalating")
                return self._build_result(session, "ESCALATED_NO_OPTIONS")
            
            if not recommended:
                # Fallback: choose lowest-risk scenario so Approval has a target
                sorted_by_risk = sorted(scenarios, key=lambda s: s.get("risk_score", 1))
                fallback = sorted_by_risk[0]
                fallback["is_recommended"] = True
                fallback.setdefault("recommendation_reason", "Lowest risk available option")
                context.set_data("recommended_scenario", fallback)
                recommended = fallback
                context.add_to_history(
                    self.replan_agent.name,
                    "fallback_recommendation",
                    {"scenario_id": fallback.get("id"), "risk_score": fallback.get("risk_score")}
                )
            
            context.set_data("selected_scenario_id", recommended.get("id") if recommended else None)
            context.set_data("has_viable_recovery", recommended is not None)
            
            if not context.get_data("has_viable_recovery", False):
                session.state = WorkflowState.ESCALATED
                session.log_action("no_viable_recommendation", "replan_agent")
                await self._emit_status(session, "No recommended recovery option - escalating")
                return self._build_result(session, "ESCALATED_NO_OPTIONS")
            
            # ==========================================
            # PHASE 4: APPROVAL
            # ==========================================
            session.state = WorkflowState.APPROVING
            await self._emit_status(session, "Processing approval workflow")
            
            context = await self.approval_agent.process(context)
            session.approval_result = self._extract_phase_result(context, "approval")
            session.save_snapshot("approval", context.data)
            
            approval_status = context.get_data("approval_status", "PENDING")
            
            if approval_status == "REJECTED":
                session.state = WorkflowState.COMPLETED
                session.log_action("approval_rejected", "approval_agent")
                await self._emit_status(session, "Recovery plan rejected")
                return self._build_result(session, "REJECTED")
            
            if approval_status == "PENDING":
                # Waiting for human approval - workflow pauses here
                session.log_action("waiting_for_approval", "approval_agent")
                await self._emit_status(session, "Waiting for human approval")
                return self._build_result(session, "PENDING_APPROVAL")
            
            # ==========================================
            # PHASE 5: EXECUTION
            # ==========================================
            session.state = WorkflowState.EXECUTING
            await self._emit_status(session, "Executing recovery plan")
            
            context = await self.execution_agent.process(context)
            session.execution_result = self._extract_phase_result(context, "execution")
            session.save_snapshot("execution", context.data)
            
            execution_status = context.get_data("execution_status", "FAILED")
            
            if execution_status == "FAILED":
                # Trigger rollback
                session.state = WorkflowState.ROLLED_BACK
                session.log_action("execution_failed_rollback", "execution_agent")
                await self._emit_status(session, "Execution failed - rolled back")
                await self._trigger_rollback(session, context)
                return self._build_result(session, "ROLLED_BACK")
            
            # ==========================================
            # PHASE 6: NOTIFICATION
            # ==========================================
            session.state = WorkflowState.NOTIFYING
            await self._emit_status(session, "Sending stakeholder notifications")
            
            context = await self.notification_agent.process(context)
            session.notification_result = self._extract_phase_result(context, "notification")
            session.save_snapshot("notification", context.data)
            
            # ==========================================
            # COMPLETE
            # ==========================================
            session.state = WorkflowState.COMPLETED
            session.completed_at = datetime.utcnow()
            session.log_action("workflow_completed", "orchestrator")
            await self._emit_status(session, "Recovery workflow completed successfully")
            
            return self._build_result(session, "COMPLETED")
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}", workflow_id=workflow_id)
            session.state = WorkflowState.FAILED
            session.log_action("workflow_failed", "orchestrator", {"error": str(e)})
            await self._emit_status(session, f"Workflow failed: {str(e)}")
            
            # Attempt rollback if we got past execution
            if session.executed_actions:
                await self._trigger_rollback(session, context)
            
            return self._build_result(session, "FAILED", error=str(e))
    
    async def resume_from_approval(
        self,
        workflow_id: str,
        approval_decision: str,
        approved_by: str,
        selected_scenario_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resume workflow after human approval decision.
        
        Called when approver makes a decision on pending approval.
        """
        session = self._active_sessions.get(workflow_id)
        if not session:
            raise ValueError(f"Workflow {workflow_id} not found or expired")
        
        if session.state != WorkflowState.APPROVING:
            raise ValueError(f"Workflow not in APPROVING state: {session.state}")
        
        session.log_action(
            "approval_received",
            approved_by,
            {"decision": approval_decision, "scenario_id": selected_scenario_id}
        )
        
        # Rebuild context from snapshots
        context = AgentContext(
            workflow_id=workflow_id,
            disruption_id=session.disruption_id,
            data=session.state_snapshots["replan"]["data"].copy()
        )
        
        context.set_data("approval_status", approval_decision)
        context.set_data("approved_by", approved_by)
        context.set_data("selected_scenario_id", selected_scenario_id)
        
        if approval_decision == "REJECTED":
            session.state = WorkflowState.COMPLETED
            await self._emit_status(session, "Recovery plan rejected by approver")
            return self._build_result(session, "REJECTED")
        
        # Continue with execution and notification phases
        try:
            # PHASE 5: EXECUTION
            session.state = WorkflowState.EXECUTING
            await self._emit_status(session, "Executing approved recovery plan")
            
            context = await self.execution_agent.process(context)
            session.execution_result = self._extract_phase_result(context, "execution")
            
            execution_status = context.get_data("execution_status", "FAILED")
            if execution_status == "FAILED":
                session.state = WorkflowState.ROLLED_BACK
                await self._trigger_rollback(session, context)
                return self._build_result(session, "ROLLED_BACK")
            
            # PHASE 6: NOTIFICATION
            session.state = WorkflowState.NOTIFYING
            await self._emit_status(session, "Sending stakeholder notifications")
            
            context = await self.notification_agent.process(context)
            session.notification_result = self._extract_phase_result(context, "notification")
            
            # COMPLETE
            session.state = WorkflowState.COMPLETED
            session.completed_at = datetime.utcnow()
            await self._emit_status(session, "Recovery completed successfully")
            
            return self._build_result(session, "COMPLETED")
            
        except Exception as e:
            session.state = WorkflowState.FAILED
            logger.error(f"Resumption failed: {str(e)}", workflow_id=workflow_id)
            return self._build_result(session, "FAILED", error=str(e))
    
    async def replay_from_phase(
        self,
        workflow_id: str,
        from_phase: str
    ) -> Dict[str, Any]:
        """
        Replay workflow from a specific checkpoint.
        
        Useful for:
        - Retrying after transient failures
        - Testing different scenarios
        - Recovery after system restart
        """
        session = self._active_sessions.get(workflow_id)
        if not session:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if from_phase not in session.state_snapshots:
            raise ValueError(f"No snapshot available for phase: {from_phase}")
        
        session.log_action("workflow_replay", "orchestrator", {"from_phase": from_phase})
        
        # Restore context from snapshot
        snapshot = session.state_snapshots[from_phase]
        context = AgentContext(
            workflow_id=workflow_id,
            disruption_id=session.disruption_id,
            data=snapshot["data"].copy()
        )
        
        # Determine which phases to run
        phase_order = ["detection", "impact", "replan", "approval", "execution", "notification"]
        start_index = phase_order.index(from_phase) + 1
        
        # Run remaining phases
        for phase in phase_order[start_index:]:
            agent = getattr(self, f"{phase}_agent")
            context = await agent.process(context)
            session.save_snapshot(phase, context.data)
        
        session.state = WorkflowState.COMPLETED
        session.completed_at = datetime.utcnow()
        
        return self._build_result(session, "COMPLETED")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow."""
        session = self._active_sessions.get(workflow_id)
        if not session:
            return None
        return session.to_dict()
    
    async def _emit_status(self, session: WorkflowSession, message: str):
        """Emit workflow status update for real-time observability."""
        await broadcast_workflow_status(
            workflow_id=session.workflow_id,
            state=session.state.value,
            message=message
        )
        logger.info(
            message,
            workflow_id=session.workflow_id,
            state=session.state.value
        )
    
    async def _trigger_rollback(self, session: WorkflowSession, context: AgentContext):
        """Trigger rollback of executed actions."""
        logger.warning(
            "Triggering rollback",
            workflow_id=session.workflow_id,
            actions_to_rollback=len(session.executed_actions)
        )
        
        # Rollback in reverse order
        for action in reversed(session.executed_actions):
            try:
                # Call appropriate rollback tool based on action type
                rollback_result = await self._rollback_action(action)
                session.rollback_actions.append({
                    "original_action": action,
                    "rollback_status": "SUCCESS",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                session.rollback_actions.append({
                    "original_action": action,
                    "rollback_status": "FAILED",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        session.log_action(
            "rollback_completed",
            "orchestrator",
            {"total_rollbacks": len(session.rollback_actions)}
        )
    
    async def _rollback_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback a single executed action."""
        action_type = action.get("type")
        
        if action_type == "BOOKING":
            # Cancel the booking
            from app.tools.booking_tools import cancel_booking
            return await cancel_booking(
                booking_id=action.get("booking_id"),
                reason="Rollback due to workflow failure"
            )
        elif action_type == "AWB_UPDATE":
            # Revert AWB to original flight
            from app.tools.awb_tools import update_awb_flight
            return await update_awb_flight(
                awb_id=action.get("awb_id"),
                flight_id=action.get("original_flight_id")
            )
        # Add more rollback handlers as needed
        
        return {"status": "SKIPPED", "reason": f"Unknown action type: {action_type}"}
    
    def _extract_phase_result(self, context: AgentContext, phase: str) -> Dict[str, Any]:
        """Extract relevant data from context after phase completion."""
        phase_keys = {
            "detection": ["disruption_detected", "disruption_type", "severity", "requires_immediate_action"],
            "impact": ["total_awbs_affected", "critical_awbs_count", "sla_breach_count", "total_revenue_at_risk", "needs_recovery"],
            "replan": ["scenarios", "recommended_scenario", "has_viable_options"],
            "approval": ["approval_status", "approval_level", "approved_by"],
            "execution": ["execution_status", "awbs_processed", "awbs_failed"],
            "notification": ["notifications_sent", "notification_failures"]
        }
        
        keys = phase_keys.get(phase, [])
        return {key: context.get_data(key) for key in keys if context.get_data(key) is not None}
    
    def _build_result(
        self,
        session: WorkflowSession,
        status: str,
        error: str = None
    ) -> Dict[str, Any]:
        """Build final workflow result."""
        result = session.to_dict()
        result["final_status"] = status
        if error:
            result["error"] = error
        return result


# Singleton instance
_orchestrator: Optional[RecoveryOrchestrator] = None


def get_orchestrator() -> RecoveryOrchestrator:
    """Get or create the orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RecoveryOrchestrator()
    return _orchestrator
