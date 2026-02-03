"""
Flight Database Model
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.database import Base


class FlightStatus(str, enum.Enum):
    """Flight status enumeration."""
    SCHEDULED = "SCHEDULED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"
    DEPARTED = "DEPARTED"
    ARRIVED = "ARRIVED"
    DIVERTED = "DIVERTED"




class Flight(Base):
    """Flight model representing scheduled and actual flight information."""
    
    __tablename__ = "flights"
    
    id = Column(String(50), primary_key=True)
    flight_number = Column(String(10), nullable=False, index=True)
    flight_date = Column(DateTime, nullable=False, index=True)
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    
    # Schedule
    scheduled_departure = Column(DateTime, nullable=False)
    scheduled_arrival = Column(DateTime, nullable=False)
    estimated_departure = Column(DateTime, nullable=True)
    estimated_arrival = Column(DateTime, nullable=True)
    actual_departure = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    
    # Status
    status = Column(SQLEnum(FlightStatus), default=FlightStatus.SCHEDULED, index=True)
    delay_minutes = Column(Integer, default=0)
    delay_reason = Column(String(100), nullable=True)
    
    # Aircraft
    aircraft_type = Column(String(20), nullable=True)
    aircraft_registration = Column(String(10), nullable=True)
    original_aircraft_type = Column(String(20), nullable=True)  # For aircraft swaps
    
    # Capacity
    cargo_capacity_kg = Column(Float, default=0)
    available_capacity_kg = Column(Float, default=0)
    booked_weight_kg = Column(Float, default=0)
    
    # Features
    has_temperature_control = Column(Boolean, default=False)
    has_dg_capability = Column(Boolean, default=True)
    has_live_animal_capability = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings = relationship("AWBBooking", back_populates="flight")
    
    def __repr__(self):
        return f"<Flight {self.flight_number} {self.origin}-{self.destination} {self.flight_date}>"
    
    @property
    def is_delayed(self) -> bool:
        return self.status == FlightStatus.DELAYED
    
    @property
    def is_cancelled(self) -> bool:
        return self.status == FlightStatus.CANCELLED
    
    @property
    def has_aircraft_change(self) -> bool:
        return (self.original_aircraft_type is not None and 
                self.original_aircraft_type != self.aircraft_type)


class FlightConnection(Base):
    """Flight connection information for transit routing."""
    
    __tablename__ = "flight_connections"
    
    id = Column(String(50), primary_key=True)
    inbound_flight_id = Column(String(50), nullable=False, index=True)
    outbound_flight_id = Column(String(50), nullable=False, index=True)
    connection_airport = Column(String(3), nullable=False)
    minimum_connect_time_minutes = Column(Integer, default=120)
    
    created_at = Column(DateTime, default=datetime.utcnow)
