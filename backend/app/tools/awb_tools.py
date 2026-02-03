"""
AWB Tools

Tools for querying and updating AWB (Air Waybill) data.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from app.db.database import get_async_session
from app.models.awb import AWB, AWBPriority
from app.models.flight import Flight

logger = structlog.get_logger()


async def get_awbs_by_flight(flight_id: str) -> List[Dict[str, Any]]:
    """
    Get all AWBs booked on a specific flight.
    
    Args:
        flight_id: The unique identifier of the flight
        
    Returns:
        List of AWBs with their details including:
        - AWB number, origin, destination
        - weight, pieces
        - priority and special handling requirements
        - SLA information
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(AWB).where(AWB.flight_id == flight_id)
        )
        awbs = result.scalars().all()
        
        return [
            {
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
                "sla_deadline": awb.sla_deadline.isoformat() if awb.sla_deadline else None,
                "is_time_critical": awb.is_time_critical,
                "requires_temperature_control": awb.requires_temperature_control,
                "temperature_min": awb.temperature_min,
                "temperature_max": awb.temperature_max,
                "is_dangerous_goods": awb.is_dangerous_goods,
                "dg_class": awb.dg_class.value if awb.dg_class else None,
                "declared_value_usd": awb.declared_value_usd,
                "freight_charges": awb.freight_charges,
                "remarks": awb.remarks
            }
            for awb in awbs
        ]


async def get_awb_details(awb_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific AWB.
    
    Args:
        awb_id: The unique identifier of the AWB
        
    Returns:
        Dictionary containing full AWB details
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(AWB).where(AWB.id == awb_id)
        )
        awb = result.scalar_one_or_none()
        
        if not awb:
            return {"error": f"AWB {awb_id} not found", "found": False}
        
        return {
            "found": True,
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
            "flight_id": awb.flight_id,
            "sla_deadline": awb.sla_deadline.isoformat() if awb.sla_deadline else None,
            "is_time_critical": awb.is_time_critical,
            "requires_temperature_control": awb.requires_temperature_control,
            "temperature_min": awb.temperature_min,
            "temperature_max": awb.temperature_max,
            "is_dangerous_goods": awb.is_dangerous_goods,
            "dg_class": awb.dg_class.value if awb.dg_class else None,
            "declared_value_usd": awb.declared_value_usd,
            "freight_charges": awb.freight_charges,
            "remarks": awb.remarks,
            "created_at": awb.created_at.isoformat(),
            "updated_at": awb.updated_at.isoformat() if awb.updated_at else None
        }


async def update_awb_flight(
    awb_id: str,
    new_flight_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update the flight assignment for an AWB.
    
    Args:
        awb_id: The unique identifier of the AWB
        new_flight_id: The new flight to assign the AWB to
        reason: Optional reason for the reassignment
        
    Returns:
        Dictionary containing the result of the update operation
    """
    async with get_async_session() as db:
        # Get the AWB
        awb_result = await db.execute(
            select(AWB).where(AWB.id == awb_id)
        )
        awb = awb_result.scalar_one_or_none()
        
        if not awb:
            return {"success": False, "error": f"AWB {awb_id} not found"}
        
        # Verify new flight exists and has capacity
        flight_result = await db.execute(
            select(Flight).where(Flight.id == new_flight_id)
        )
        new_flight = flight_result.scalar_one_or_none()
        
        if not new_flight:
            return {"success": False, "error": f"Flight {new_flight_id} not found"}
        
        if new_flight.available_capacity_kg < awb.weight_kg:
            return {
                "success": False,
                "error": f"Insufficient capacity. Need {awb.weight_kg}kg, available {new_flight.available_capacity_kg}kg"
            }
        
        # Check special handling
        if awb.requires_temperature_control and not new_flight.has_temperature_control:
            return {
                "success": False,
                "error": "Flight does not have temperature control capability"
            }
        
        if awb.is_dangerous_goods and not new_flight.has_dg_capability:
            return {
                "success": False,
                "error": "Flight does not have dangerous goods capability"
            }
        
        # Store old flight for capacity update
        old_flight_id = awb.flight_id
        
        # Update AWB
        awb.flight_id = new_flight_id
        awb.updated_at = datetime.utcnow()
        
        # Update old flight capacity
        if old_flight_id:
            old_flight_result = await db.execute(
                select(Flight).where(Flight.id == old_flight_id)
            )
            old_flight = old_flight_result.scalar_one_or_none()
            if old_flight:
                old_flight.booked_weight_kg -= awb.weight_kg
        
        # Update new flight capacity
        new_flight.booked_weight_kg += awb.weight_kg
        
        await db.commit()
        
        logger.info(
            "AWB reassigned",
            awb_id=awb_id,
            awb_number=awb.awb_number,
            old_flight=old_flight_id,
            new_flight=new_flight_id,
            reason=reason
        )
        
        return {
            "success": True,
            "awb_id": awb_id,
            "awb_number": awb.awb_number,
            "old_flight_id": old_flight_id,
            "new_flight_id": new_flight_id,
            "weight_kg": awb.weight_kg,
            "reason": reason,
            "updated_at": awb.updated_at.isoformat()
        }


async def calculate_sla_risk(
    awb_id: str,
    new_arrival_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Calculate SLA breach risk for an AWB.
    
    Args:
        awb_id: The unique identifier of the AWB
        new_arrival_time: Optional new estimated arrival time
        
    Returns:
        Dictionary containing SLA risk assessment:
        - sla_deadline
        - estimated_arrival
        - time_buffer_hours
        - risk_level (SAFE, AT_RISK, BREACHED)
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(AWB).where(AWB.id == awb_id)
        )
        awb = result.scalar_one_or_none()
        
        if not awb:
            return {"error": f"AWB {awb_id} not found", "found": False}
        
        if not awb.sla_deadline:
            return {
                "found": True,
                "awb_id": awb_id,
                "has_sla": False,
                "risk_level": "NO_SLA"
            }
        
        # Determine arrival time
        if new_arrival_time:
            arrival = new_arrival_time
        elif awb.flight_id:
            # Get flight arrival
            flight_result = await db.execute(
                select(Flight).where(Flight.id == awb.flight_id)
            )
            flight = flight_result.scalar_one_or_none()
            arrival = flight.estimated_arrival or flight.scheduled_arrival if flight else None
        else:
            arrival = None
        
        if not arrival:
            return {
                "found": True,
                "awb_id": awb_id,
                "has_sla": True,
                "sla_deadline": awb.sla_deadline.isoformat(),
                "risk_level": "UNKNOWN",
                "reason": "No arrival time available"
            }
        
        # Calculate buffer
        buffer_hours = (awb.sla_deadline - arrival).total_seconds() / 3600
        
        if buffer_hours < 0:
            risk_level = "BREACHED"
        elif buffer_hours < 2:
            risk_level = "AT_RISK"
        elif buffer_hours < 6:
            risk_level = "WARNING"
        else:
            risk_level = "SAFE"
        
        return {
            "found": True,
            "awb_id": awb_id,
            "awb_number": awb.awb_number,
            "has_sla": True,
            "sla_deadline": awb.sla_deadline.isoformat(),
            "estimated_arrival": arrival.isoformat(),
            "time_buffer_hours": round(buffer_hours, 2),
            "risk_level": risk_level,
            "is_time_critical": awb.is_time_critical,
            "priority": awb.priority.value
        }
