"""
Booking Summary Database Model
"""
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Integer,
    Date,
    DECIMAL,
    CheckConstraint,
)
from datetime import datetime
from app.db.database import Base


class BookingSummary(Base):
    """Denormalized booking summary table for agentic views."""

    __tablename__ = "booking_summary"

    booking_id = Column(Integer, primary_key=True, autoincrement=True)

    awb_prefix = Column(String(3), nullable=False, index=True)
    awb_number = Column(String(8), nullable=False, index=True)
    ubr_number = Column(String(50), nullable=False, unique=True, index=True)

    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)

    shipping_date = Column(Date, nullable=False)

    pieces = Column(Integer, nullable=False)
    chargeable_weight = Column(DECIMAL(10, 2), nullable=False)

    total_revenue = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")

    booking_status = Column(String(1), nullable=False, default="C")  # C=Confirmed, Q=Queued
    agent_code = Column(String(50), nullable=False)
    
    # Special cargo designation
    cargo_type = Column(String(50), nullable=True, default=None)  # PERISHABLE, LIVE_ANIMALS, PHARMA, HAZMAT, etc.

    created_at = Column(Date, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("pieces > 0", name="ck_booking_pieces_positive"),
        CheckConstraint("chargeable_weight > 0", name="ck_booking_chargeable_positive"),
        CheckConstraint("total_revenue >= 0", name="ck_booking_revenue_nonnegative"),
    )

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<BookingSummary {self.awb_prefix}-{self.awb_number} {self.shipping_date}>"
