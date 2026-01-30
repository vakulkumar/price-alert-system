"""Shared Pydantic schemas for Kafka messages."""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PriceSource(str, Enum):
    """Source of price data."""
    COINGECKO = "coingecko"
    YAHOO = "yahoo"


class AlertCondition(str, Enum):
    """Types of alert conditions."""
    ABOVE = "above"
    BELOW = "below"
    CROSSES = "crosses"
    RANGE = "range"


class NotificationType(str, Enum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"


# ============================================
# Kafka Message Schemas
# ============================================

class PriceEvent(BaseModel):
    """Price update event published to Kafka."""
    symbol: str = Field(..., description="Instrument symbol (e.g., BTC, NIFTY)")
    price: float = Field(..., description="Current price")
    previous_price: Optional[float] = Field(None, description="Previous price for cross detection")
    currency: str = Field(default="USD", description="Price currency")
    source: PriceSource = Field(..., description="Data source")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationEvent(BaseModel):
    """Notification event for the Notifier service."""
    alert_id: int = Field(..., description="ID of the triggered alert")
    user_id: int = Field(..., description="User to notify")
    user_email: str = Field(..., description="User email address")
    user_phone: Optional[str] = Field(None, description="User phone number")
    symbol: str = Field(..., description="Triggered symbol")
    condition: AlertCondition = Field(..., description="Alert condition type")
    target_price: float = Field(..., description="Target price from alert")
    current_price: float = Field(..., description="Current market price")
    notification_types: list[NotificationType] = Field(
        default=[NotificationType.EMAIL],
        description="Notification channels to use"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# API Request/Response Schemas
# ============================================

class AlertCreate(BaseModel):
    """Request schema for creating an alert."""
    symbol: str = Field(..., min_length=1, max_length=20)
    condition: AlertCondition
    target_price: float = Field(..., gt=0)
    target_price_high: Optional[float] = Field(None, gt=0, description="Upper bound for range alerts")
    notification_types: list[NotificationType] = Field(default=[NotificationType.EMAIL])


class AlertResponse(BaseModel):
    """Response schema for an alert."""
    id: int
    symbol: str
    condition: AlertCondition
    target_price: float
    target_price_high: Optional[float]
    notification_types: list[NotificationType]
    active: bool
    triggered_count: int
    created_at: datetime
    last_triggered_at: Optional[datetime]


class PriceResponse(BaseModel):
    """Response schema for current price."""
    symbol: str
    price: float
    currency: str
    change_24h: Optional[float]
    source: PriceSource
    timestamp: datetime


class UserCreate(BaseModel):
    """Request schema for user registration."""
    email: str
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """Response schema for user."""
    id: int
    email: str
    phone: Optional[str]
    created_at: datetime


class TokenResponse(BaseModel):
    """Response schema for JWT token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
