"""
Booking Tools

Tools for creating, modifying, and cancelling cargo bookings.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import structlog

from app.db.database import get_async_session
from app.models.awb import AWB
from app.models.flight import Flight
from sqlalchemy import select

logger = structlog.get_logger()


async def create_booking(
    awb_id: str,
    flight_id: str,
    booking_class: str = "C",
    remarks: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new cargo booking on a flight.
    
    Args:
        awb_id: The AWB to book
        flight_id: The flight to book on
        booking_class: Booking class (C=Cargo, P=Priority, E=Express)
        remarks: Optional booking remarks
        
    Returns:
        Dictionary containing:
        - booking_id: Unique booking reference
        - status: Booking status
        - confirmation_number: Booking confirmation
    """
    async with get_async_session() as db:
        # Verify AWB exists
        awb_result = await db.execute(
            select(AWB).where(AWB.id == awb_id)
        )
        awb = awb_result.scalar_one_or_none()
        
        if not awb:
            return {"success": False, "error": f"AWB {awb_id} not found"}
        
        # Verify flight exists and has capacity
        flight_result = await db.execute(
            select(Flight).where(Flight.id == flight_id)
        )
        flight = flight_result.scalar_one_or_none()
        
        if not flight:
            return {"success": False, "error": f"Flight {flight_id} not found"}
        
        if flight.available_capacity_kg < awb.weight_kg:
            return {
                "success": False,
                "error": f"Insufficient capacity. Required: {awb.weight_kg}kg, Available: {flight.available_capacity_kg}kg"
            }
        
        # Create booking
        booking_id = str(uuid.uuid4())
        confirmation = f"BKG{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Update AWB with new flight
        awb.flight_id = flight_id
        awb.updated_at = datetime.utcnow()
        
        # Update flight capacity
        flight.booked_weight_kg += awb.weight_kg
        
        await db.commit()
        
        logger.info(
            "Booking created",
            booking_id=booking_id,
            awb_number=awb.awb_number,
            flight_number=flight.flight_number
        )
        
        return {
            "success": True,
            "booking_id": booking_id,
            "confirmation_number": confirmation,
            "awb_id": awb_id,
            "awb_number": awb.awb_number,
            "flight_id": flight_id,
            "flight_number": flight.flight_number,
            "weight_kg": awb.weight_kg,
            "booking_class": booking_class,
            "status": "CONFIRMED",
            "created_at": datetime.utcnow().isoformat()
        }


async def cancel_booking(
    awb_id: str,
    reason: str,
    cancel_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cancel an existing cargo booking.
    
    Args:
        awb_id: The AWB to cancel booking for
        reason: Reason for cancellation
        cancel_code: Optional cancellation code
        
    Returns:
        Dictionary containing:
        - success: boolean
        - cancelled_from: flight that was cancelled from
        - refund_applicable: if refund applies
    """
    async with get_async_session() as db:
        # Get AWB
        awb_result = await db.execute(
            select(AWB).where(AWB.id == awb_id)
        )
        awb = awb_result.scalar_one_or_none()
        
        if not awb:
            return {"success": False, "error": f"AWB {awb_id} not found"}
        
        if not awb.flight_id:
            return {"success": False, "error": "AWB has no active booking"}
        
        # Get current flight
        flight_result = await db.execute(
            select(Flight).where(Flight.id == awb.flight_id)
        )
        flight = flight_result.scalar_one_or_none()
        
        old_flight_id = awb.flight_id
        old_flight_number = flight.flight_number if flight else None
        
        # Update flight capacity
        if flight:
            flight.booked_weight_kg -= awb.weight_kg
        
        # Clear AWB flight assignment
        awb.flight_id = None
        awb.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(
            "Booking cancelled",
            awb_number=awb.awb_number,
            cancelled_flight=old_flight_number,
            reason=reason
        )
        
        return {
            "success": True,
            "awb_id": awb_id,
            "awb_number": awb.awb_number,
            "cancelled_from_flight_id": old_flight_id,
            "cancelled_from_flight_number": old_flight_number,
            "reason": reason,
            "cancel_code": cancel_code or "AGENT_RECOVERY",
            "refund_applicable": True,
            "cancelled_at": datetime.utcnow().isoformat()
        }


async def modify_booking(
    awb_id: str,
    new_flight_id: str,
    modification_reason: str,
    preserve_priority: bool = True
) -> Dict[str, Any]:
    """
    Modify an existing booking to a different flight.
    
    This is a composite operation that:
    1. Cancels the existing booking
    2. Creates a new booking on the target flight
    
    Args:
        awb_id: The AWB to modify
        new_flight_id: The new flight to book on
        modification_reason: Reason for the change
        preserve_priority: Whether to maintain booking priority
        
    Returns:
        Dictionary containing:
        - success: boolean
        - old_booking: details of cancelled booking
        - new_booking: details of new booking
    """
    async with get_async_session() as db:
        # Get AWB
        awb_result = await db.execute(
            select(AWB).where(AWB.id == awb_id)
        )
        awb = awb_result.scalar_one_or_none()
        
        if not awb:
            return {"success": False, "error": f"AWB {awb_id} not found"}
        
        old_flight_id = awb.flight_id
        old_flight_number = None
        
        # Get old flight details
        if old_flight_id:
            old_flight_result = await db.execute(
                select(Flight).where(Flight.id == old_flight_id)
            )
            old_flight = old_flight_result.scalar_one_or_none()
            if old_flight:
                old_flight_number = old_flight.flight_number
                old_flight.booked_weight_kg -= awb.weight_kg
        
        # Get new flight
        new_flight_result = await db.execute(
            select(Flight).where(Flight.id == new_flight_id)
        )
        new_flight = new_flight_result.scalar_one_or_none()
        
        if not new_flight:
            return {"success": False, "error": f"Flight {new_flight_id} not found"}
        
        # Capacity check
        if new_flight.available_capacity_kg < awb.weight_kg:
            return {
                "success": False,
                "error": f"Insufficient capacity on new flight. Required: {awb.weight_kg}kg, Available: {new_flight.available_capacity_kg}kg"
            }
        
        # Constraint checks
        if awb.requires_temperature_control and not new_flight.has_temperature_control:
            return {
                "success": False,
                "error": "New flight does not support temperature control"
            }
        
        if awb.is_dangerous_goods and not new_flight.has_dg_capability:
            return {
                "success": False,
                "error": "New flight does not support dangerous goods"
            }
        
        # Perform modification
        awb.flight_id = new_flight_id
        awb.updated_at = datetime.utcnow()
        new_flight.booked_weight_kg += awb.weight_kg
        
        await db.commit()
        
        logger.info(
            "Booking modified",
            awb_number=awb.awb_number,
            old_flight=old_flight_number,
            new_flight=new_flight.flight_number,
            reason=modification_reason
        )
        
        return {
            "success": True,
            "awb_id": awb_id,
            "awb_number": awb.awb_number,
            "old_booking": {
                "flight_id": old_flight_id,
                "flight_number": old_flight_number
            },
            "new_booking": {
                "flight_id": new_flight_id,
                "flight_number": new_flight.flight_number,
                "departure": new_flight.scheduled_departure.isoformat(),
                "arrival": new_flight.scheduled_arrival.isoformat()
            },
            "modification_reason": modification_reason,
            "modified_at": datetime.utcnow().isoformat()
        }
