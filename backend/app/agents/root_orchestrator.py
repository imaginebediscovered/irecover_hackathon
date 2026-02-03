"""
Root Orchestrator Wrapper for Real-time Detection API

Provides simplified interface for the detection API to run full workflows.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.agents.detection_agent import DetectionAgent
from app.agents.impact_agent import ImpactAgent
from app.agents.replan_agent import ReplanAgent
from app.agents.approval_agent import ApprovalAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.notification_agent import NotificationAgent

logger = structlog.get_logger()


class RootOrchestrator:
    """
    Simplified orchestrator for running full agentic workflows.
    Processes events through: Detection → Impact → Replan → Approval → Execution → Notification
    """
    
    def __init__(self):
        self.detection_agent = DetectionAgent()
        self.impact_agent = ImpactAgent()
        self.replan_agent = ReplanAgent()
        self.approval_agent = ApprovalAgent()
        self.execution_agent = ExecutionAgent()
        self.notification_agent = NotificationAgent()
    
    async def run_workflow(
        self,
        event: Dict[str, Any],
        workflow_id: str,
        disruption_id: str,
        auto_execute: bool = False,
        db: Optional[AsyncSession] = None
    ) -> AgentContext:
        """
        Run full workflow through all agents sequentially.
        
        Args:
            event: Disruption event to process
            workflow_id: Unique workflow identifier
            disruption_id: Disruption identifier
            auto_execute: If True, auto-execute approved actions
            db: Optional database session
            
        Returns:
            Final agent context with all results
        """
        # Create initial context
        context = AgentContext(
            workflow_id=workflow_id,
            disruption_id=disruption_id
        )
        context.set_data("flight_event", event)
        context.set_data("auto_execute", auto_execute)
        
        logger.info(
            "Starting full workflow",
            workflow_id=workflow_id,
            event_type=event.get("event_type")
        )
        
        try:
            # Phase 1: Detection
            logger.info("Phase 1: Detection Agent", workflow_id=workflow_id)
            context = await self.detection_agent.run(context)
            
            if not context.get_data("disruption_detected", False):
                logger.info("No disruption detected, ending workflow", workflow_id=workflow_id)
                context.set_data("final_status", "NO_DISRUPTION")
                return context
            
            # Phase 2: Impact Analysis (if disruption detected)
            logger.info("Phase 2: Impact Analysis Agent", workflow_id=workflow_id)
            context = await self.impact_agent.run(context)

            print("Context: ", context)
            
            # Phase 3: Replanning
            logger.info("Phase 3: Replan Agent", workflow_id=workflow_id)
            context = await self.replan_agent.run(context)
            
            # Ensure a viable recommendation exists before approval
            scenarios = context.get_data("recovery_scenarios", [])
            recommended = context.get_data("recommended_scenario")
            
            print(f"Scenarios generated: {scenarios}")
            print(f"Recommended scenario: {recommended}")
            
            if not scenarios:
                logger.info("No recovery scenarios generated", workflow_id=workflow_id)
                context.set_data("final_status", "NO_RECOVERY_OPTIONS")
                return context
            
            if not recommended:
                sorted_by_risk = sorted(scenarios, key=lambda s: s.get("risk_score", 1))
                fallback = sorted_by_risk[0]
                fallback["is_recommended"] = True
                fallback.setdefault("recommendation_reason", "Lowest risk available option")
                context.set_data("recommended_scenario", fallback)
                recommended = fallback
            
            context.set_data("selected_scenario_id", recommended.get("id") if recommended else None)
            context.set_data("has_viable_recovery", recommended is not None)
            
            if not context.get_data("has_viable_recovery", False):
                logger.info("No viable recommendation after replanning", workflow_id=workflow_id)
                context.set_data("final_status", "NO_RECOVERY_OPTIONS")
                return context
            
            # Phase 4: Approval
            logger.info("Phase 4: Approval Agent", workflow_id=workflow_id)
            context = await self.approval_agent.run(context)
            
            approval_status = context.get_data("approval_status", "PENDING")
            
            if approval_status == "REJECTED":
                logger.info("Recovery plan rejected, ending workflow", workflow_id=workflow_id)
                context.set_data("final_status", "REJECTED")
                return context
            
            # Phase 5: Execution (if approved)
            if approval_status == "APPROVED" or auto_execute:
                logger.info("Phase 5: Execution Agent", workflow_id=workflow_id)
                context = await self.execution_agent.run(context)
            
            # Phase 6: Notification
            logger.info("Phase 6: Notification Agent", workflow_id=workflow_id)
            context = await self.notification_agent.run(context)
            
            context.set_data("final_status", "COMPLETED")
            logger.info("Workflow completed successfully", workflow_id=workflow_id)
            
            return context
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}", workflow_id=workflow_id, error=str(e))
            context.set_data("final_status", "FAILED")
            context.set_data("error", str(e))
            raise
