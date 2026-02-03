"""
News Database Model
"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime
from app.db.database import Base


class News(Base):
    """
    News table to store news articles with headline, content, place, and date.
    """
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    headline = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    place = Column(String(255), nullable=False, index=True)
    date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<News(id={self.id}, headline='{self.headline}', place='{self.place}', date={self.date})>"
