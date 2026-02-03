"""
Flight Tools

Tools for querying and searching flight data.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.db.database import get_async_session
from app.models.flight import Flight, FlightStatus

logger = structlog.get_logger()


async def get_flight_details(flight_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific flight.
    
    Args:
        flight_id: The unique identifier of the flight
        
    Returns:
        Dictionary containing flight details including:
        - flight_number, origin, destination
        - scheduled/actual departure and arrival times
        - capacity and booking information
        - aircraft details
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalar_one_or_none()
        
        if not flight:
            return {"error": f"Flight {flight_id} not found", "found": False}
        
        return {
            "found": True,
            "id": flight.id,
            "flight_number": flight.flight_number,
            "origin": flight.origin,
            "destination": flight.destination,
            "scheduled_departure": flight.scheduled_departure.isoformat(),
            "scheduled_arrival": flight.scheduled_arrival.isoformat(),
            "estimated_departure": flight.estimated_departure.isoformat() if flight.estimated_departure else None,
            "estimated_arrival": flight.estimated_arrival.isoformat() if flight.estimated_arrival else None,
            "actual_departure": flight.actual_departure.isoformat() if flight.actual_departure else None,
            "status": flight.status.value,
            "delay_minutes": flight.delay_minutes,
            "delay_reason": flight.delay_reason if flight.delay_reason else None,
            "aircraft_type": flight.aircraft_type,
            "aircraft_registration": flight.aircraft_registration,
            "cargo_capacity_kg": flight.cargo_capacity_kg,
            "booked_weight_kg": flight.booked_weight_kg,
            "available_capacity_kg": flight.available_capacity_kg,
            "has_temperature_control": flight.has_temperature_control,
            "has_dg_capability": flight.has_dg_capability
        }


async def search_alternative_flights(
    origin: str,
    destination: str,
    earliest_departure: datetime,
    min_capacity_kg: float = 0,
    requires_temperature_control: bool = False,
    requires_dg_capability: bool = False,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for alternative flights that can accommodate cargo.
    
    Args:
        origin: Origin airport code (3 letters)
        destination: Destination airport code (3 letters)
        earliest_departure: Earliest acceptable departure time
        min_capacity_kg: Minimum required cargo capacity
        requires_temperature_control: If true, flight must have temp control
        requires_dg_capability: If true, flight must accept dangerous goods
        max_results: Maximum number of results to return
        
    Returns:
        List of matching flights with availability information
    """
    # Guard against None inputs that break SQLAlchemy comparisons
    safe_earliest = earliest_departure or datetime.utcnow()
    safe_capacity = min_capacity_kg or 0

    async with get_async_session() as db:
        query = select(Flight).where(
            Flight.origin == origin.upper(),
            Flight.destination == destination.upper(),
            Flight.scheduled_departure >= safe_earliest,
            Flight.status.in_([FlightStatus.SCHEDULED, FlightStatus.DELAYED]),
            Flight.available_capacity_kg >= safe_capacity
        )
        
        if requires_temperature_control:
            query = query.where(Flight.has_temperature_control == True)
        
        if requires_dg_capability:
            query = query.where(Flight.has_dg_capability == True)
        
        query = query.order_by(Flight.scheduled_departure.asc()).limit(max_results)
        
        result = await db.execute(query)
        flights = result.scalars().all()
        
        return [
            {
                "id": f.id,
                "flight_number": f.flight_number,
                "origin": f.origin,
                "destination": f.destination,
                "departure": f.scheduled_departure.isoformat(),
                "arrival": f.scheduled_arrival.isoformat(),
                "available_capacity_kg": f.available_capacity_kg,
                "aircraft_type": f.aircraft_type,
                "has_temperature_control": f.has_temperature_control,
                "has_dg_capability": f.has_dg_capability,
                "status": f.status.value,
                # Defensive: always return a valid delay_reason string or 'OTHER'
                "delay_reason": f.delay_reason if f.delay_reason else "OTHER"
            }
            for f in flights
        ]


async def get_flight_capacity(flight_id: str) -> Dict[str, Any]:
    """
    Get detailed capacity information for a specific flight.
    
    Args:
        flight_id: The unique identifier of the flight
        
    Returns:
        Dictionary containing capacity details:
        - total, booked, and available capacity
        - utilization percentage
        - special handling capabilities
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalar_one_or_none()
        
        if not flight:
            return {"error": f"Flight {flight_id} not found", "found": False}
        
        utilization = (
            (flight.booked_weight_kg / flight.cargo_capacity_kg * 100)
            if flight.cargo_capacity_kg > 0 else 0
        )
        
        return {
            "found": True,
            "flight_id": flight.id,
            "flight_number": flight.flight_number,
            "total_capacity_kg": flight.cargo_capacity_kg,
            "booked_weight_kg": flight.booked_weight_kg,
            "available_capacity_kg": flight.available_capacity_kg,
            "utilization_percent": round(utilization, 2),
            "has_temperature_control": flight.has_temperature_control,
            "has_dg_capability": flight.has_dg_capability,
            "can_accept_cargo": flight.available_capacity_kg > 0
        }


async def check_flight_status(flight_id: str) -> Dict[str, Any]:
    """
    Check the current operational status of a flight.
    
    Args:
        flight_id: The unique identifier of the flight
        
    Returns:
        Dictionary containing status information:
        - current status
        - delay information if applicable
        - estimated times
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(Flight).where(Flight.id == flight_id)
        )
        flight = result.scalar_one_or_none()
        
        if not flight:
            return {"error": f"Flight {flight_id} not found", "found": False}
        
        return {
            "found": True,
            "flight_id": flight.id,
            "flight_number": flight.flight_number,
            "status": flight.status.value,
            "is_cancelled": flight.status == FlightStatus.CANCELLED,
            "is_delayed": flight.status == FlightStatus.DELAYED,
            "delay_minutes": flight.delay_minutes,
            "delay_reason": flight.delay_reason if flight.delay_reason else None,
            "scheduled_departure": flight.scheduled_departure.isoformat(),
            "estimated_departure": flight.estimated_departure.isoformat() if flight.estimated_departure else None,
            "scheduled_arrival": flight.scheduled_arrival.isoformat(),
            "estimated_arrival": flight.estimated_arrival.isoformat() if flight.estimated_arrival else None
        }
