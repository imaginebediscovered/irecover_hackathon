"""
Approval API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import structlog

from app.db.database import get_db
from app.models.approval import Approval, ApprovalStatus, ApprovalLevel, ExecutionStep
from app.models.disruption import Disruption, DisruptionStatus, AWBImpact, RecoveryScenario
from app.models.awb import AWB
from app.agents.base import AgentContext
from app.agents.execution_agent import ExecutionAgent
import uuid
from app.schemas import (
    ApprovalResponse, ApprovalRequest, ApprovalRejectRequest,
    ExecutionStepResponse
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/pending", response_model=List[ApprovalResponse])
async def get_pending_approvals(
    level: Optional[str] = Query(None, description="Filter by approval level"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending approvals.
    In production, this would filter by the current user's approval level.
    """
    query = select(Approval).where(Approval.status == ApprovalStatus.PENDING)
    
    if level:
        try:
            level_enum = ApprovalLevel(level)
            query = query.where(Approval.required_level == level_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid level: {level}")
    
    query = query.order_by(Approval.requested_at.asc())
    
    result = await db.execute(query)
    approvals = result.scalars().all()
    
    return approvals


@router.get("/pending-rich")
async def get_pending_approvals_rich(
    level: Optional[str] = Query(None, description="Filter by approval level"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending approvals with full disruption details, AWB impacts, and scenarios.
    This is the enhanced endpoint for the ApprovalsQueue UI.
    """
    from sqlalchemy.orm import selectinload
    
    query = select(Approval).where(Approval.status == ApprovalStatus.PENDING)
    
    if level:
        try:
            level_enum = ApprovalLevel(level)
            query = query.where(Approval.required_level == level_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid level: {level}")
    
    query = query.order_by(Approval.requested_at.asc())
    
    result = await db.execute(query)
    approvals = result.scalars().all()
    
    # Build rich response with all related data
    rich_approvals = []
    for approval in approvals:
        # Load disruption
        disruption_result = await db.execute(
            select(Disruption).where(Disruption.id == approval.disruption_id)
        )
        disruption = disruption_result.scalar_one_or_none()
        
        if not disruption:
            continue
        
        # Load AWB impacts
        impacts_result = await db.execute(
            select(AWBImpact, AWB)
            .join(AWB, AWBImpact.awb_number == AWB.awb_number)
            .where(AWBImpact.disruption_id == disruption.id)
        )
        impact_rows = impacts_result.all()
        
        awb_impacts = []
        for impact, awb in impact_rows:
            awb_impacts.append({
                "awb_number": awb.awb_number,
                "origin": awb.origin,
                "destination": awb.destination,
                "priority": awb.priority.value if hasattr(awb.priority, 'value') else str(awb.priority),
                "product_type": awb.commodity_type.value if hasattr(awb.commodity_type, 'value') else str(awb.commodity_type) if awb.commodity_type else None,
                "special_handling": awb.special_handling_codes or [],
                "weight_kg": float(awb.weight_kg or 0),
                "volume_mc": float(awb.volume_cbm or 0),
                "shipper_name": awb.shipper_name,
                "consignee_name": awb.consignee_name,
                "sla_deadline": awb.sla_commitment.isoformat() if awb.sla_commitment else None,
                "original_eta": impact.original_eta.isoformat() if impact.original_eta else None,
                "new_eta": impact.new_eta.isoformat() if impact.new_eta else None,
                "breach_risk": impact.breach_risk,
                "revenue_at_risk": float(impact.revenue_at_risk or 0),
                "is_critical": impact.is_critical,
            })
        
        # Load scenarios
        scenarios_result = await db.execute(
            select(RecoveryScenario).where(RecoveryScenario.disruption_id == disruption.id)
        )
        scenarios = scenarios_result.scalars().all()
        
        scenario_list = []
        for s in scenarios:
            scenario_list.append({
                "id": s.id,
                "scenario_type": s.scenario_type,
                "description": s.description,
                "target_flight_number": s.target_flight_number,
                "target_departure": s.target_departure.isoformat() if s.target_departure else None,
                "sla_saved_count": s.sla_saved_count,
                "sla_at_risk_count": s.sla_at_risk_count,
                "risk_score": s.risk_score,
                "execution_time_minutes": s.execution_time_minutes,
                "estimated_cost": float(s.estimated_cost or 0),
                "is_recommended": s.is_recommended,
                "recommendation_reason": s.recommendation_reason,
                "constraint_results": s.constraint_results or {},
                "all_constraints_satisfied": s.all_constraints_satisfied,
            })
        
        rich_approvals.append({
            "id": approval.id,
            "disruption_id": approval.disruption_id,
            "required_level": approval.required_level.value,
            "status": approval.status.value,
            "risk_score": approval.risk_score,
            "risk_factors": approval.risk_factors or [],
            "auto_approve_eligible": approval.auto_approve_eligible,
            "assigned_to": approval.assigned_to,
            "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
            "timeout_at": approval.timeout_at.isoformat() if approval.timeout_at else None,
            "comments": approval.comments or [],
            "disruption": {
                "id": disruption.id,
                "flight_number": disruption.flight_number,
                "flight_date": disruption.flight_date.isoformat() if disruption.flight_date else None,
                "origin": disruption.origin,
                "destination": disruption.destination,
                "disruption_type": disruption.disruption_type.value,
                "severity": disruption.severity.value,
                "status": disruption.status.value,
                "delay_minutes": disruption.delay_minutes,
                "delay_reason": disruption.delay_reason,
                "total_awbs_affected": disruption.total_awbs_affected,
                "critical_awbs_count": disruption.critical_awbs_count,
                "revenue_at_risk": float(disruption.revenue_at_risk or 0),
                "sla_breach_count": disruption.sla_breach_count,
                "detected_at": disruption.detected_at.isoformat() if disruption.detected_at else None,
            },
            "awb_impacts": awb_impacts,
            "scenarios": scenario_list,
        })
    
    return rich_approvals


@router.get("/stats")
async def get_approval_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get approval statistics for dashboard.
    """
    # Pending by level
    pending_query = select(Approval).where(Approval.status == ApprovalStatus.PENDING)
    result = await db.execute(pending_query)
    pending_approvals = result.scalars().all()
    
    by_level = {}
    for approval in pending_approvals:
        level = approval.required_level.value
        by_level[level] = by_level.get(level, 0) + 1
    
    # Auto-approved count
    auto_query = select(Approval).where(Approval.status == ApprovalStatus.AUTO_APPROVED)
    auto_result = await db.execute(auto_query)
    auto_count = len(auto_result.scalars().all())
    
    return {
        "pending_count": len(pending_approvals),
        "pending_by_level": by_level,
        "auto_approved_count": auto_count
    }


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get approval details.
    """
    result = await db.execute(
        select(Approval).where(Approval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    return approval


@router.post("/{approval_id}/approve")
async def approve_scenario(
    approval_id: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a recovery scenario and trigger execution.
    """
    result = await db.execute(
        select(Approval).where(Approval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot approve - current status is {approval.status.value}"
        )
    
    # Update approval
    approval.status = ApprovalStatus.APPROVED
    approval.selected_scenario_id = request.scenario_id
    approval.decided_at = datetime.utcnow()
    approval.decision_by = "user@example.com"  # TODO: Get from auth
    
    if request.comments:
        approval.comments = approval.comments + [{
            "user": "user@example.com",
            "comment": request.comments,
            "timestamp": datetime.utcnow().isoformat()
        }]
    
    # Update disruption status
    disruption_result = await db.execute(
        select(Disruption).where(Disruption.id == approval.disruption_id)
    )
    disruption = disruption_result.scalar_one_or_none()
    
    if disruption:
        disruption.status = DisruptionStatus.EXECUTING
        disruption.selected_scenario_id = request.scenario_id
        disruption.approved_at = datetime.utcnow()
        disruption.execution_started_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(
        "Approval granted",
        approval_id=approval_id,
        scenario_id=request.scenario_id
    )
    
    # TODO: Trigger execution agent
    
    return {
        "message": "Approved successfully",
        "approval_id": approval_id,
        "scenario_id": request.scenario_id,
        "status": "EXECUTING"
    }


@router.post("/{approval_id}/execute")
async def execute_approved_plan(
    approval_id: str,
    scenario_id: Optional[str] = Query(None, description="Override scenario to execute"),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger execution of an approved disruption's recovery plan.

    Preconditions:
    - Approval must exist and be in APPROVED or AUTO_APPROVED state
    - A recovery scenario must be available (selected on approval or via override)
    """
    # Load approval
    result = await db.execute(
        select(Approval).where(Approval.id == approval_id)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status not in [ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED]:
        raise HTTPException(status_code=400, detail=f"Cannot execute - approval status is {approval.status.value}")

    # Load disruption
    disruption_result = await db.execute(
        select(Disruption).where(Disruption.id == approval.disruption_id)
    )
    disruption = disruption_result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found for this approval")

    # Resolve scenario to execute
    scenario_to_use_id = scenario_id or approval.selected_scenario_id or disruption.selected_scenario_id
    scenario_obj: Optional[RecoveryScenario] = None
    if scenario_to_use_id:
        scenario_res = await db.execute(
            select(RecoveryScenario).where(RecoveryScenario.id == scenario_to_use_id)
        )
        scenario_obj = scenario_res.scalar_one_or_none()
    if not scenario_obj:
        # Fallback: pick a recommended scenario if available
        scen_res = await db.execute(
            select(RecoveryScenario).where(RecoveryScenario.disruption_id == disruption.id)
        )
        all_scen = scen_res.scalars().all()
        scenario_obj = next((s for s in all_scen if getattr(s, "is_recommended", False)), None) or (all_scen[0] if all_scen else None)
    if not scenario_obj:
        raise HTTPException(status_code=400, detail="No recovery scenario available to execute")

    # Build impact results by joining AWBImpact and AWB
    impacts_res = await db.execute(
        select(AWBImpact, AWB)
        .join(AWB, AWBImpact.awb_number == AWB.awb_number)
        .where(AWBImpact.disruption_id == disruption.id)
    )
    rows = impacts_res.all()
    impact_results = []
    for impact, awb in rows:
        impact_results.append({
            "awb_id": impact.awb_number,
            "awb_number": awb.awb_number,
            "weight_kg": float(awb.weight_kg or 0),
            "priority": (awb.priority.value if hasattr(awb.priority, 'value') else str(awb.priority or 'STANDARD')),
        })

    # Construct execution context
    workflow_id = f"manual-exec-{approval_id}-{uuid.uuid4().hex[:8]}"
    context = AgentContext(
        workflow_id=workflow_id,
        disruption_id=disruption.id,
        data={
            "approval_status": approval.status.value,
            "recommended_scenario": {
                "scenario_type": scenario_obj.scenario_type,
                "target_flight_id": scenario_obj.target_flight_id,
                "target_flight_number": scenario_obj.target_flight_number,
            },
            "impact_results": impact_results,
        },
    )

    # Run execution agent
    agent = ExecutionAgent()
    result_context = await agent.run(context)

    execution_status = result_context.get_data("execution_status")

    # Update disruption status timestamps
    if execution_status in ("COMPLETED", "PARTIAL"):
        disruption.status = DisruptionStatus.COMPLETED if execution_status == "COMPLETED" else DisruptionStatus.EXECUTING
        disruption.execution_completed_at = datetime.utcnow()
        await db.commit()

    logger.info(
        "Manual execution completed",
        approval_id=approval_id,
        disruption_id=disruption.id,
        status=execution_status
    )

    return {
        "workflow_id": workflow_id,
        "disruption_id": disruption.id,
        "approval_id": approval_id,
        "status": execution_status,
        "awbs_recovered": result_context.get_data("awbs_recovered"),
        "awbs_failed": result_context.get_data("awbs_failed"),
    }


@router.post("/{approval_id}/reject")
async def reject_scenario(
    approval_id: str,
    request: ApprovalRejectRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reject all scenarios for a disruption.
    """
    result = await db.execute(
        select(Approval).where(Approval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject - current status is {approval.status.value}"
        )
    
    # Update approval
    approval.status = ApprovalStatus.REJECTED
    approval.rejection_reason = request.reason
    approval.decided_at = datetime.utcnow()
    approval.decision_by = "user@example.com"  # TODO: Get from auth
    
    # Update disruption status
    disruption_result = await db.execute(
        select(Disruption).where(Disruption.id == approval.disruption_id)
    )
    disruption = disruption_result.scalar_one_or_none()
    
    if disruption:
        disruption.status = DisruptionStatus.FAILED
    
    await db.commit()
    
    logger.info(
        "Approval rejected",
        approval_id=approval_id,
        reason=request.reason
    )
    
    return {
        "message": "Rejected",
        "approval_id": approval_id,
        "reason": request.reason
    }


@router.get("/{approval_id}/execution-steps", response_model=List[ExecutionStepResponse])
async def get_execution_steps(
    approval_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get execution steps for an approved disruption.
    """
    # Get approval to find disruption
    approval_result = await db.execute(
        select(Approval).where(Approval.id == approval_id)
    )
    approval = approval_result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Get execution steps
    result = await db.execute(
        select(ExecutionStep)
        .where(ExecutionStep.disruption_id == approval.disruption_id)
        .order_by(ExecutionStep.step_number.asc())
    )
    steps = result.scalars().all()
    
    return steps
