"""
Bookings API Routes (agentic booking summary view)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.booking_summary import BookingSummary

router = APIRouter()


@router.get("/")
async def list_bookings(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    awb_number: Optional[str] = Query(None),
    ubr_number: Optional[str] = Query(None),
    sla_breach: Optional[bool] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List booking summaries with simple filters for agentic UX."""
    query = select(BookingSummary).order_by(BookingSummary.shipping_date.asc())

    filters = []
    if date_from:
        from datetime import datetime
        filters.append(BookingSummary.shipping_date >= datetime.fromisoformat(date_from).date())
    if date_to:
        from datetime import datetime
        filters.append(BookingSummary.shipping_date <= datetime.fromisoformat(date_to).date())
    if origin:
        filters.append(BookingSummary.origin == origin.upper())
    if destination:
        filters.append(BookingSummary.destination == destination.upper())
    if awb_number:
        filters.append(BookingSummary.awb_number.ilike(f"%{awb_number}%"))
    if ubr_number:
        filters.append(BookingSummary.ubr_number.ilike(f"%{ubr_number}%"))

    if filters:
        query = query.where(and_(*filters))

    # total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "booking_id": b.booking_id,
                "awb": f"{b.awb_prefix}-{b.awb_number}",
                "awb_prefix": b.awb_prefix,
                "awb_number": b.awb_number,
                "ubr_number": b.ubr_number,
                "origin": b.origin,
                "destination": b.destination,
                "shipping_date": b.shipping_date.isoformat(),
                "pieces": int(b.pieces),
                "chargeable_weight": float(b.chargeable_weight),
                "total_revenue": float(b.total_revenue),
                "currency": b.currency,
                "booking_status": b.booking_status,
                "agent_code": b.agent_code,
            }
            for b in items
        ],
    }


@router.get("/facets")
async def booking_facets(db: AsyncSession = Depends(get_db)):
    """Return simple facets for agentic UI (counts by origin, destination, agent_code)."""
    # origins
    origins_q = select(BookingSummary.origin, func.count().label("count")).group_by(BookingSummary.origin)
    dest_q = select(BookingSummary.destination, func.count().label("count")).group_by(BookingSummary.destination)
    agent_q = select(BookingSummary.agent_code, func.count().label("count")).group_by(BookingSummary.agent_code)

    origins = (await db.execute(origins_q)).all()
    dests = (await db.execute(dest_q)).all()
    agents = (await db.execute(agent_q)).all()

    return {
        "origins": [{"origin": o[0], "count": o[1]} for o in origins],
        "destinations": [{"destination": d[0], "count": d[1]} for d in dests],
        "agents": [{"agent_code": a[0], "count": a[1]} for a in agents],
    }


@router.get("/{booking_id}")
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookingSummary).where(BookingSummary.booking_id == booking_id))
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {
        "booking_id": b.booking_id,
        "awb_prefix": b.awb_prefix,
        "awb_number": b.awb_number,
        "ubr_number": b.ubr_number,
        "origin": b.origin,
        "destination": b.destination,
        "shipping_date": b.shipping_date.isoformat(),
        "pieces": int(b.pieces),
        "chargeable_weight": float(b.chargeable_weight),
        "total_revenue": float(b.total_revenue),
        "currency": b.currency,
        "booking_status": b.booking_status,
        "agent_code": b.agent_code,
    }
