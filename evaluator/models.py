"""SQLAlchemy database models for the alert system."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY
import enum

Base = declarative_base()


class AlertCondition(str, enum.Enum):
    """Alert condition types."""
    ABOVE = "above"
    BELOW = "below"
    CROSSES = "crosses"
    RANGE = "range"


class NotificationType(str, enum.Enum):
    """Notification channel types."""
    EMAIL = "email"
    SMS = "sms"


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
    
    # Relationships
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")


class Alert(Base):
    """Price alert model."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    condition = Column(SQLEnum(AlertCondition), nullable=False)
    target_price = Column(Float, nullable=False)
    target_price_high = Column(Float, nullable=True)  # For range alerts
    notification_types = Column(String(50), default="email")  # Comma-separated
    active = Column(Boolean, default=True, index=True)
    triggered_count = Column(Integer, default=0)
    cooldown_minutes = Column(Integer, default=60)  # Minimum time between notifications
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    
    def get_notification_types(self) -> List[str]:
        """Parse notification types from string."""
        return self.notification_types.split(",") if self.notification_types else ["email"]
    
    def can_trigger(self) -> bool:
        """Check if alert can trigger (respects cooldown)."""
        if not self.active:
            return False
        if not self.last_triggered_at:
            return True
        elapsed = (datetime.utcnow() - self.last_triggered_at).total_seconds()
        return elapsed >= (self.cooldown_minutes * 60)


class NotificationLog(Base):
    """Log of sent notifications."""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    trigger_price = Column(Float, nullable=False)
    notification_type = Column(SQLEnum(NotificationType), nullable=False)
    status = Column(String(20), default="pending")  # pending, sent, failed
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_database_url() -> str:
    """Get database URL from environment."""
    import os
    return os.getenv("DATABASE_URL", "postgresql://alertuser:alertpass@localhost:5432/alertsdb")


def create_db_engine():
    """Create SQLAlchemy engine."""
    return create_engine(get_database_url(), pool_pre_ping=True)


def get_session_factory():
    """Create session factory."""
    engine = create_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    engine = create_db_engine()
    Base.metadata.create_all(bind=engine)
