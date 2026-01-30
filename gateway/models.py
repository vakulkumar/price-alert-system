"""Database models for the gateway."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class AlertCondition(str, enum.Enum):
    """Alert condition types."""
    ABOVE = "above"
    BELOW = "below"
    CROSSES = "crosses"
    RANGE = "range"


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")


class Alert(Base):
    """Price alert model."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    condition = Column(SQLEnum(AlertCondition), nullable=False)
    target_price = Column(Float, nullable=False)
    target_price_high = Column(Float, nullable=True)
    notification_types = Column(String(50), default="email")
    active = Column(Boolean, default=True, index=True)
    triggered_count = Column(Integer, default=0)
    cooldown_minutes = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="alerts")
