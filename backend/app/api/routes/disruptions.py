"""
Disruption API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.db.database import get_db
from app.models.disruption import Disruption, AWBImpact, RecoveryScenario, DisruptionStatus, DisruptionSeverity
from app.models.audit import AuditTrail
from app.schemas import (
    DisruptionResponse, DisruptionDetailResponse,
    AWBImpactResponse, RecoveryScenarioResponse,
    AuditTrailResponse
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=List[DisruptionResponse])
async def list_disruptions(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    since: Optional[datetime] = Query(None, description="Filter disruptions since this time"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List all disruptions with optional filters.
    """
    query = select(Disruption).order_by(Disruption.detected_at.desc())
    
    if status:
        try:
            status_enum = DisruptionStatus(status)
            query = query.where(Disruption.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if severity:
        try:
            severity_enum = DisruptionSeverity(severity)
            query = query.where(Disruption.severity == severity_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    if since:
        query = query.where(Disruption.detected_at >= since)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    disruptions = result.scalars().all()
    
    return disruptions


@router.get("/stats")
async def get_disruption_stats(
    hours: int = Query(24, description="Stats for last N hours"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get disruption statistics for dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Active disruptions count
    active_query = select(func.count(Disruption.id)).where(
        Disruption.status.in_([
            DisruptionStatus.DETECTED,
            DisruptionStatus.ANALYZING,
            DisruptionStatus.PENDING_APPROVAL,
            DisruptionStatus.EXECUTING
        ])
    )
    active_result = await db.execute(active_query)
    active_count = active_result.scalar() or 0
    
    # Pending approvals
    pending_query = select(func.count(Disruption.id)).where(
        Disruption.status == DisruptionStatus.PENDING_APPROVAL
    )
    pending_result = await db.execute(pending_query)
    pending_count = pending_result.scalar() or 0
    
    # Resolved in time period
    resolved_query = select(func.count(Disruption.id)).where(
        Disruption.status == DisruptionStatus.COMPLETED,
        Disruption.resolved_at >= since
    )
    resolved_result = await db.execute(resolved_query)
    resolved_count = resolved_result.scalar() or 0
    
    # By severity
    severity_query = select(
        Disruption.severity,
        func.count(Disruption.id)
    ).where(
        Disruption.detected_at >= since
    ).group_by(Disruption.severity)
    severity_result = await db.execute(severity_query)
    severity_counts = {str(row[0].value): row[1] for row in severity_result.all()}
    
    return {
        "active_disruptions": active_count,
        "pending_approvals": pending_count,
        "resolved_today": resolved_count,
        "by_severity": severity_counts,
        "period_hours": hours
    }


@router.get("/{disruption_id}", response_model=DisruptionDetailResponse)
async def get_disruption(
    disruption_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed disruption information.
    """
    result = await db.execute(
        select(Disruption).where(Disruption.id == disruption_id)
    )
    disruption = result.scalar_one_or_none()
    
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    
    return disruption


@router.get("/{disruption_id}/impacts", response_model=List[AWBImpactResponse])
async def get_disruption_impacts(
    disruption_id: str,
    critical_only: bool = Query(False, description="Only return critical AWBs"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all AWB impacts for a disruption.
    """
    query = select(AWBImpact).where(AWBImpact.disruption_id == disruption_id)
    
    if critical_only:
        query = query.where(AWBImpact.is_critical == True)
    
    query = query.order_by(AWBImpact.time_to_breach_minutes.asc())
    
    result = await db.execute(query)
    impacts = result.scalars().all()
    
    return impacts


@router.get("/{disruption_id}/scenarios", response_model=List[RecoveryScenarioResponse])
async def get_disruption_scenarios(
    disruption_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all recovery scenarios for a disruption.
    """
    result = await db.execute(
        select(RecoveryScenario)
        .where(RecoveryScenario.disruption_id == disruption_id)
        .order_by(RecoveryScenario.overall_score.desc())
    )
    scenarios = result.scalars().all()
    
    return scenarios


@router.get("/{disruption_id}/audit-trail", response_model=List[AuditTrailResponse])
async def get_audit_trail(
    disruption_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete decision audit trail for a disruption.
    """
    result = await db.execute(
        select(AuditTrail)
        .where(AuditTrail.disruption_id == disruption_id)
        .order_by(AuditTrail.timestamp.asc())
    )
    trail = result.scalars().all()
    
    return trail


@router.post("/{disruption_id}/trigger-analysis")
async def trigger_analysis(
    disruption_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger impact analysis for a disruption.
    Used when automatic analysis needs to be re-run.
    """
    result = await db.execute(
        select(Disruption).where(Disruption.id == disruption_id)
    )
    disruption = result.scalar_one_or_none()
    
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    
    # Update status to trigger analysis
    disruption.status = DisruptionStatus.ANALYZING
    disruption.analysis_started_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info("Manual analysis triggered", disruption_id=disruption_id)
    
    # TODO: Trigger orchestrator to run analysis
    # This will be done via message queue or direct call
    
    return {
        "message": "Analysis triggered",
        "disruption_id": disruption_id,
        "status": "ANALYZING"
    }
