"""
Weather Disruption Model
Tracks weather conditions affecting cargo bookings
"""
from sqlalchemy import Column, Integer, String, Date, Text
from app.db.database import Base


class WeatherDisruption(Base):
    """Weather disruption data for airports affecting cargo bookings"""
    __tablename__ = "weather_disruptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    airport_code = Column(String(3), nullable=False, index=True)
    disruption_date = Column(Date, nullable=False, index=True)
    weather_type = Column(String(50), nullable=False)  # THUNDERSTORM, FOG, SNOW, HURRICANE, etc.
    severity = Column(String(10), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    impact = Column(Text, nullable=True)  # Human-readable impact description
