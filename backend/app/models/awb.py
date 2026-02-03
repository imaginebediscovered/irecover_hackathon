"""
AWB (Air Waybill) Database Model
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.database import Base


class Priority(str, enum.Enum):
    """AWB priority levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    STANDARD = "STANDARD"
    LOW = "LOW"

# Alias for backward compatibility
AWBPriority = Priority


class CommodityType(str, enum.Enum):
    """Commodity type classification."""
    GENERAL = "GENERAL"
    PHARMA = "PHARMA"
    PERISHABLE = "PERISHABLE"
    DANGEROUS_GOODS = "DANGEROUS_GOODS"
    LIVE_ANIMALS = "LIVE_ANIMALS"
    VALUABLE = "VALUABLE"
    HUMAN_REMAINS = "HUMAN_REMAINS"
    MAIL = "MAIL"
    EXPRESS = "EXPRESS"

# Alias for backward compatibility
ProductType = CommodityType


class AWB(Base):
    """Air Waybill model representing cargo shipment."""
    
    __tablename__ = "awbs"
    
    awb_number = Column(String(20), primary_key=True)
    
    # Route
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    final_destination = Column(String(3), nullable=True)  # If connecting
    
    # Cargo details
    pieces = Column(Integer, default=1)
    weight_kg = Column(Float, nullable=False)
    volume_cbm = Column(Float, nullable=True)
    chargeable_weight_kg = Column(Float, nullable=True)
    
    # Commodity
    commodity = Column(String(100), nullable=True)
    commodity_code = Column(String(20), nullable=True)
    commodity_type = Column(SQLEnum(CommodityType), default=CommodityType.GENERAL)
    
    # Customer
    customer_id = Column(String(50), nullable=False, index=True)
    customer_name = Column(String(200), nullable=True)
    shipper_name = Column(String(200), nullable=True)
    consignee_name = Column(String(200), nullable=True)
    
    # SLA & Priority
    sla_commitment = Column(DateTime, nullable=True)
    priority = Column(SQLEnum(Priority), default=Priority.STANDARD, index=True)
    is_time_critical = Column(Boolean, default=False)
    
    # Special handling - Dangerous Goods
    is_dangerous_goods = Column(Boolean, default=False, index=True)
    dg_class = Column(String(10), nullable=True)
    dg_un_number = Column(String(10), nullable=True)
    dg_proper_shipping_name = Column(String(200), nullable=True)
    dg_packing_group = Column(String(5), nullable=True)
    
    # Special handling - Temperature
    is_temperature_controlled = Column(Boolean, default=False, index=True)
    temp_min_celsius = Column(Float, nullable=True)
    temp_max_celsius = Column(Float, nullable=True)
    
    # Special handling - Other
    is_live_animal = Column(Boolean, default=False)
    requires_customs_clearance = Column(Boolean, default=False)
    special_handling_codes = Column(JSON, default=list)  # e.g., ["PER", "COL", "EAT"]
    
    # ULD
    uld_type_required = Column(String(10), nullable=True)
    
    # Status
    current_location = Column(String(3), nullable=True)
    status = Column(String(20), default="BOOKED")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings = relationship("AWBBooking", back_populates="awb")
    impacts = relationship("AWBImpact", back_populates="awb")
    
    def __repr__(self):
        return f"<AWB {self.awb_number} {self.origin}-{self.destination}>"
    
    @property
    def has_special_handling(self) -> bool:
        return (self.is_dangerous_goods or 
                self.is_temperature_controlled or 
                self.is_live_animal)
    
    @property
    def is_critical_cargo(self) -> bool:
        return (self.priority == Priority.CRITICAL or 
                self.commodity_type in [CommodityType.PHARMA, CommodityType.PERISHABLE])


class AWBBooking(Base):
    """AWB booking on a specific flight."""
    
    __tablename__ = "awb_bookings"
    
    id = Column(String(50), primary_key=True)
    awb_number = Column(String(20), ForeignKey("awbs.awb_number"), nullable=False, index=True)
    flight_id = Column(String(50), ForeignKey("flights.id"), nullable=False, index=True)
    
    booking_reference = Column(String(50), nullable=True)
    pieces = Column(Integer, default=1)
    weight_kg = Column(Float, nullable=False)
    
    status = Column(String(20), default="CONFIRMED")  # CONFIRMED, CANCELLED, OFFLOADED
    position = Column(String(50), nullable=True)  # e.g., MAIN_DECK_FWD
    
    # ULD assignment
    uld_number = Column(String(20), nullable=True)
    uld_type = Column(String(10), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relationships
    awb = relationship("AWB", back_populates="bookings")
    flight = relationship("Flight", back_populates="bookings")


class Customer(Base):
    """Customer/Account information."""
    
    __tablename__ = "customers"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    account_number = Column(String(50), nullable=True)
    
    # Priority
    priority_level = Column(Integer, default=3)  # 1=VIP, 2=Premium, 3=Standard
    is_vip = Column(Boolean, default=False)
    
    # Contact
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Preferences
    preferred_notification_channel = Column(String(20), default="EMAIL")  # EMAIL, SMS, WHATSAPP
    preferred_language = Column(String(5), default="en")
    timezone = Column(String(50), default="UTC")
    
    # Contract
    has_sla_agreement = Column(Boolean, default=False)
    sla_penalty_rate = Column(Float, default=0)  # Penalty per hour of delay
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
