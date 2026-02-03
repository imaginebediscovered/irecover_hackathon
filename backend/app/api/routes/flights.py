"""
Flight API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, date

from app.db.database import get_db
from app.models.flight import Flight, FlightStatus
from app.schemas import FlightResponse, FlightDetailResponse

router = APIRouter()


@router.get("/", response_model=List[FlightResponse])
async def list_flights(
    origin: Optional[str] = Query(None, max_length=3),
    destination: Optional[str] = Query(None, max_length=3),
    flight_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List flights with optional filters.
    """
    query = select(Flight).order_by(Flight.scheduled_departure.asc())
    
    if origin:
        query = query.where(Flight.origin == origin.upper())
    
    if destination:
        query = query.where(Flight.destination == destination.upper())
    
    if flight_date:
        start = datetime.combine(flight_date, datetime.min.time())
        end = datetime.combine(flight_date, datetime.max.time())
        query = query.where(Flight.flight_date >= start, Flight.flight_date <= end)
    
    if status:
        try:
            status_enum = FlightStatus(status)
            query = query.where(Flight.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    flights = result.scalars().all()
    
    return flights


@router.get("/search")
async def search_alternative_flights(
    origin: str = Query(..., max_length=3),
    destination: str = Query(..., max_length=3),
    earliest_departure: datetime = Query(...),
    min_capacity_kg: float = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for alternative flights with available capacity.
    Used by replan agent to find recovery options.
    """
    query = select(Flight).where(
        Flight.origin == origin.upper(),
        Flight.destination == destination.upper(),
        Flight.scheduled_departure >= earliest_departure,
        Flight.status.in_([FlightStatus.SCHEDULED, FlightStatus.DELAYED]),
        Flight.available_capacity_kg >= min_capacity_kg
    ).order_by(Flight.scheduled_departure.asc()).limit(10)
    
    result = await db.execute(query)
    flights = result.scalars().all()
    
    return [
        {
            "id": f.id,
            "flight_number": f.flight_number,
            "departure": f.scheduled_departure,
            "arrival": f.scheduled_arrival,
            "available_capacity_kg": f.available_capacity_kg,
            "aircraft_type": f.aircraft_type,
            "has_temperature_control": f.has_temperature_control,
            "has_dg_capability": f.has_dg_capability
        }
        for f in flights
    ]


@router.get("/{flight_id}", response_model=FlightDetailResponse)
async def get_flight(
    flight_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed flight information.
    """
    result = await db.execute(
        select(Flight).where(Flight.id == flight_id)
    )
    flight = result.scalar_one_or_none()
    
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    return flight


@router.get("/{flight_id}/capacity")
async def get_flight_capacity(
    flight_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed capacity information for a flight.
    """
    result = await db.execute(
        select(Flight).where(Flight.id == flight_id)
    )
    flight = result.scalar_one_or_none()
    
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    return {
        "flight_id": flight.id,
        "flight_number": flight.flight_number,
        "total_capacity_kg": flight.cargo_capacity_kg,
        "booked_weight_kg": flight.booked_weight_kg,
        "available_capacity_kg": flight.available_capacity_kg,
        "utilization_percent": (
            (flight.booked_weight_kg / flight.cargo_capacity_kg * 100)
            if flight.cargo_capacity_kg > 0 else 0
        ),
        "has_temperature_control": flight.has_temperature_control,
        "has_dg_capability": flight.has_dg_capability
    }
