"""
AWB (Air Waybill) API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.models.awb import AWB, AWBPriority, ProductType

router = APIRouter()


@router.get("/")
async def list_awbs(
    flight_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by AWB number"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List AWBs with optional filters.
    """
    query = select(AWB).order_by(AWB.created_at.desc())
    
    if flight_id:
        query = query.where(AWB.flight_id == flight_id)
    
    if priority:
        try:
            priority_enum = AWBPriority(priority)
            query = query.where(AWB.priority == priority_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
    
    if product_type:
        try:
            product_enum = ProductType(product_type)
            query = query.where(AWB.product_type == product_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid product type: {product_type}")
    
    if search:
        query = query.where(AWB.awb_number.ilike(f"%{search}%"))
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    awbs = result.scalars().all()
    
    return {
        "total": total,
        "items": [
            {
                "id": awb.id,
                "awb_number": awb.awb_number,
                "origin": awb.origin,
                "destination": awb.destination,
                "pieces": awb.pieces,
                "weight_kg": awb.weight_kg,
                "priority": awb.priority.value,
                "product_type": awb.product_type.value if awb.product_type else None,
                "shipper_name": awb.shipper_name,
                "consignee_name": awb.consignee_name,
                "booked_flight_id": awb.flight_id,
                "sla_deadline": awb.sla_deadline.isoformat() if awb.sla_deadline else None,
                "is_time_critical": awb.is_time_critical
            }
            for awb in awbs
        ]
    }


@router.get("/impacted")
async def get_impacted_awbs(
    disruption_id: str = Query(..., description="Disruption ID to get impacted AWBs for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AWBs impacted by a specific disruption.
    Used by impact-assessment agent.
    """
    # First get the disruption to find affected flight
    from app.models.disruption import Disruption
    
    disruption_result = await db.execute(
        select(Disruption).where(Disruption.id == disruption_id)
    )
    disruption = disruption_result.scalar_one_or_none()
    
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    
    # Get all AWBs on the affected flight
    query = select(AWB).where(AWB.flight_id == disruption.flight_id)
    
    result = await db.execute(query)
    awbs = result.scalars().all()
    
    # Categorize by priority and time-criticality
    categorized = {
        "total_count": len(awbs),
        "total_weight_kg": sum(awb.weight_kg for awb in awbs),
        "by_priority": {
            "critical": [],
            "high": [],
            "standard": [],
            "low": []
        },
        "time_critical": [],
        "special_handling": []
    }
    
    for awb in awbs:
        awb_data = {
            "id": awb.id,
            "awb_number": awb.awb_number,
            "origin": awb.origin,
            "destination": awb.destination,
            "weight_kg": awb.weight_kg,
            "pieces": awb.pieces,
            "shipper_name": awb.shipper_name,
            "consignee_name": awb.consignee_name,
            "sla_deadline": awb.sla_deadline.isoformat() if awb.sla_deadline else None,
            "requires_temperature_control": awb.requires_temperature_control,
            "is_dangerous_goods": awb.is_dangerous_goods
        }
        
        categorized["by_priority"][awb.priority.value].append(awb_data)
        
        if awb.is_time_critical:
            categorized["time_critical"].append(awb_data)
        
        if awb.requires_temperature_control or awb.is_dangerous_goods:
            categorized["special_handling"].append(awb_data)
    
    return categorized


@router.get("/{awb_id}")
async def get_awb(
    awb_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed AWB information.
    """
    result = await db.execute(
        select(AWB).where(AWB.id == awb_id)
    )
    awb = result.scalar_one_or_none()
    
    if not awb:
        raise HTTPException(status_code=404, detail="AWB not found")
    
    return {
        "id": awb.id,
        "awb_number": awb.awb_number,
        "origin": awb.origin,
        "destination": awb.destination,
        "pieces": awb.pieces,
        "weight_kg": awb.weight_kg,
        "volume_cbm": awb.volume_cbm,
        "priority": awb.priority.value,
        "product_type": awb.product_type.value if awb.product_type else None,
        "shipper_name": awb.shipper_name,
        "consignee_name": awb.consignee_name,
        "booked_flight_id": awb.flight_id,
        "sla_deadline": awb.sla_deadline.isoformat() if awb.sla_deadline else None,
        "is_time_critical": awb.is_time_critical,
        "requires_temperature_control": awb.requires_temperature_control,
        "temperature_min": awb.temperature_min,
        "temperature_max": awb.temperature_max,
        "is_dangerous_goods": awb.is_dangerous_goods,
        "dg_class": awb.dg_class.value if awb.dg_class else None,
        "declared_value_usd": awb.declared_value_usd,
        "remarks": awb.remarks,
        "created_at": awb.created_at.isoformat(),
        "updated_at": awb.updated_at.isoformat() if awb.updated_at else None
    }


@router.put("/{awb_id}/reassign")
async def reassign_awb(
    awb_id: str,
    new_flight_id: str = Query(..., description="New flight to assign AWB to"),
    reason: Optional[str] = Query(None, description="Reason for reassignment"),
    db: AsyncSession = Depends(get_db)
):
    """
    Reassign an AWB to a different flight.
    Used during recovery execution.
    """
    from app.models.flight import Flight
    
    # Get the AWB
    result = await db.execute(
        select(AWB).where(AWB.id == awb_id)
    )
    awb = result.scalar_one_or_none()
    
    if not awb:
        raise HTTPException(status_code=404, detail="AWB not found")
    
    # Verify new flight exists and has capacity
    flight_result = await db.execute(
        select(Flight).where(Flight.id == new_flight_id)
    )
    new_flight = flight_result.scalar_one_or_none()
    
    if not new_flight:
        raise HTTPException(status_code=404, detail="Target flight not found")
    
    if new_flight.available_capacity_kg < awb.weight_kg:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient capacity. Need {awb.weight_kg}kg, available {new_flight.available_capacity_kg}kg"
        )
    
    # Check special handling requirements
    if awb.requires_temperature_control and not new_flight.has_temperature_control:
        raise HTTPException(
            status_code=400,
            detail="Target flight does not have temperature control capability"
        )
    
    if awb.is_dangerous_goods and not new_flight.has_dg_capability:
        raise HTTPException(
            status_code=400,
            detail="Target flight does not have dangerous goods capability"
        )
    
    # Store old flight for logging
    old_flight_id = awb.flight_id
    
    # Update AWB
    awb.flight_id = new_flight_id
    awb.updated_at = datetime.utcnow()
    
    # Update flight capacities
    if old_flight_id:
        old_flight_result = await db.execute(
            select(Flight).where(Flight.id == old_flight_id)
        )
        old_flight = old_flight_result.scalar_one_or_none()
        if old_flight:
            old_flight.booked_weight_kg -= awb.weight_kg
    
    new_flight.booked_weight_kg += awb.weight_kg
    
    await db.commit()
    
    return {
        "success": True,
        "awb_id": awb_id,
        "awb_number": awb.awb_number,
        "old_flight_id": old_flight_id,
        "new_flight_id": new_flight_id,
        "reason": reason,
        "reassigned_at": datetime.utcnow().isoformat()
    }
