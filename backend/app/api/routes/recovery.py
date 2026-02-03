"""
Recovery Workflow API Routes

Endpoints for triggering and managing the agentic recovery workflow.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import structlog

from app.agents.orchestrator import get_orchestrator

logger = structlog.get_logger()
router = APIRouter(prefix="/recovery", tags=["Recovery Workflow"])


class DisruptionEventRequest(BaseModel):
    """Request model for triggering recovery workflow."""
    flight_id: str
    event_type: str
    delay_minutes: Optional[int] = 0
    capacity_change_percent: Optional[float] = 0
    weather_condition: Optional[str] = None
    cancellation_reason: Optional[str] = None
    diversion_reason: Optional[str] = None
    diverted_to: Optional[str] = None
    original_destination: Optional[str] = None
    embargo_type: Optional[str] = None
    temperature_deviation: Optional[float] = None
    cargo_type: Optional[str] = None
    sla_at_risk: Optional[bool] = False
    priority_reason: Optional[str] = None
    bumped_awb_count: Optional[int] = 0
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None


class ApprovalDecisionRequest(BaseModel):
    """Request model for approval decisions."""
    workflow_id: str
    decision: str  # APPROVED or REJECTED
    approved_by: str
    selected_scenario_id: Optional[str] = None
    comments: Optional[str] = None


class WorkflowReplayRequest(BaseModel):
    """Request model for workflow replay."""
    workflow_id: str
    from_phase: str


@router.post("/trigger")
async def trigger_recovery_workflow(
    request: DisruptionEventRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Trigger the recovery workflow for a disruption event.
    
    This initiates the full agentic workflow:
    Detect → Analyze → Replan → Approve → Execute → Notify
    
    For asynchronous processing, the workflow runs in background
    and returns a workflow_id for tracking.
    """
    logger.info(
        "Recovery workflow triggered",
        flight_id=request.flight_id,
        event_type=request.event_type
    )
    
    orchestrator = get_orchestrator()
    
    # Build event from request
    event = {
        "flight_id": request.flight_id,
        "event_type": request.event_type,
        "delay_minutes": request.delay_minutes,
        "capacity_change_percent": request.capacity_change_percent,
        "weather_condition": request.weather_condition,
        "cancellation_reason": request.cancellation_reason,
        "diversion_reason": request.diversion_reason,
        "diverted_to": request.diverted_to,
        "original_destination": request.original_destination,
        "embargo_type": request.embargo_type,
        "temperature_deviation": request.temperature_deviation,
        "cargo_type": request.cargo_type,
        "sla_at_risk": request.sla_at_risk,
        "priority_reason": request.priority_reason,
        "bumped_awb_count": request.bumped_awb_count,
        "triggered_at": datetime.utcnow().isoformat(),
        **(request.metadata or {})
    }
    
    # Run workflow (can be async in production)
    try:
        result = await orchestrator.handle_disruption_event(event)
        
        return {
            "status": "workflow_started",
            "workflow_id": result.get("workflow_id"),
            "current_state": result.get("state"),
            "final_status": result.get("final_status"),
            "message": "Recovery workflow initiated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to trigger workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-async")
async def trigger_recovery_workflow_async(
    request: DisruptionEventRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Trigger recovery workflow asynchronously (non-blocking).
    
    Returns immediately with workflow_id.
    Use /status/{workflow_id} to check progress.
    """
    import uuid
    workflow_id = str(uuid.uuid4())
    
    # Build event
    event = {
        "flight_id": request.flight_id,
        "event_type": request.event_type,
        "delay_minutes": request.delay_minutes,
        "disruption_id": workflow_id,
        **(request.metadata or {})
    }
    
    async def run_workflow():
        orchestrator = get_orchestrator()
        await orchestrator.handle_disruption_event(event)
    
    background_tasks.add_task(run_workflow)
    
    return {
        "status": "workflow_queued",
        "workflow_id": workflow_id,
        "message": "Recovery workflow queued for processing. Check status endpoint for updates."
    }


@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """
    Get current status of a recovery workflow.
    
    Returns full workflow state including:
    - Current phase
    - Phase results
    - Audit log
    """
    orchestrator = get_orchestrator()
    status = orchestrator.get_workflow_status(workflow_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    return status


@router.post("/approve")
async def submit_approval_decision(request: ApprovalDecisionRequest) -> Dict[str, Any]:
    """
    Submit an approval decision for a pending workflow.
    
    Called when a human approver makes a decision on a recovery plan.
    Resumes the workflow with execution phase if approved.
    """
    logger.info(
        "Approval decision received",
        workflow_id=request.workflow_id,
        decision=request.decision,
        approved_by=request.approved_by
    )
    
    if request.decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be APPROVED or REJECTED"
        )
    
    orchestrator = get_orchestrator()
    
    try:
        result = await orchestrator.resume_from_approval(
            workflow_id=request.workflow_id,
            approval_decision=request.decision,
            approved_by=request.approved_by,
            selected_scenario_id=request.selected_scenario_id
        )
        
        return {
            "status": "success",
            "workflow_id": request.workflow_id,
            "decision": request.decision,
            "workflow_result": result.get("final_status"),
            "message": f"Approval {request.decision.lower()} processed successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process approval: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replay")
async def replay_workflow(request: WorkflowReplayRequest) -> Dict[str, Any]:
    """
    Replay a workflow from a specific checkpoint.
    
    Useful for:
    - Retrying after transient failures
    - Testing different scenarios
    - Recovery after system restart
    """
    logger.info(
        "Workflow replay requested",
        workflow_id=request.workflow_id,
        from_phase=request.from_phase
    )
    
    orchestrator = get_orchestrator()
    
    try:
        result = await orchestrator.replay_from_phase(
            workflow_id=request.workflow_id,
            from_phase=request.from_phase
        )
        
        return {
            "status": "success",
            "workflow_id": request.workflow_id,
            "replayed_from": request.from_phase,
            "final_status": result.get("final_status")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to replay workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def list_active_workflows() -> Dict[str, Any]:
    """
    List all active (non-completed) workflows.
    
    Useful for monitoring and dashboard views.
    """
    orchestrator = get_orchestrator()
    
    active_workflows = []
    for workflow_id, session in orchestrator._active_sessions.items():
        if session.state.value not in ["COMPLETED", "FAILED", "ROLLED_BACK"]:
            active_workflows.append({
                "workflow_id": workflow_id,
                "disruption_id": session.disruption_id,
                "state": session.state.value,
                "started_at": session.started_at.isoformat()
            })
    
    return {
        "active_count": len(active_workflows),
        "workflows": active_workflows
    }


@router.get("/learning/summary")
async def get_learning_summary() -> Dict[str, Any]:
    """
    Get summary of learning data from the Learning Agent.
    
    Shows:
    - Scenario effectiveness
    - Disruption patterns
    - Overall success rates
    """
    from app.agents.learning_agent import LearningAgent
    
    learning_agent = LearningAgent()
    return learning_agent.get_learning_summary()


@router.get("/learning/recommendation/{disruption_type}")
async def get_learned_recommendation(disruption_type: str) -> Dict[str, Any]:
    """
    Get learned recommendation for a specific disruption type.
    
    Based on historical success data, suggests the best scenario type.
    """
    from app.agents.learning_agent import LearningAgent
    
    learning_agent = LearningAgent()
    recommendation = await learning_agent.get_recommendation_for_disruption(disruption_type)
    
    if not recommendation:
        return {
            "disruption_type": disruption_type,
            "recommendation": None,
            "message": "Not enough data to make a recommendation (minimum 3 outcomes needed)"
        }
    
    return recommendation
