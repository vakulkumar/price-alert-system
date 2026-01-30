"""Alert CRUD routes."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from models import Alert, AlertCondition, User
from routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# Schemas
class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    condition: AlertCondition
    target_price: float = Field(..., gt=0)
    target_price_high: Optional[float] = Field(None, gt=0)
    notification_types: str = Field(default="email", description="Comma-separated: email,sms")
    cooldown_minutes: int = Field(default=60, ge=1)


class AlertUpdate(BaseModel):
    target_price: Optional[float] = Field(None, gt=0)
    target_price_high: Optional[float] = None
    notification_types: Optional[str] = None
    cooldown_minutes: Optional[int] = Field(None, ge=1)
    active: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    symbol: str
    condition: AlertCondition
    target_price: float
    target_price_high: Optional[float]
    notification_types: str
    cooldown_minutes: int
    active: bool
    triggered_count: int
    created_at: datetime
    last_triggered_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Routes
@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's alerts with optional filters."""
    query = db.query(Alert).filter(Alert.user_id == current_user.id)
    
    if symbol:
        query = query.filter(Alert.symbol == symbol.upper())
    if active is not None:
        query = query.filter(Alert.active == active)
    
    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    return alerts


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new price alert."""
    # Validate range condition
    if alert_data.condition == AlertCondition.RANGE and not alert_data.target_price_high:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_price_high is required for range alerts"
        )
    
    alert = Alert(
        user_id=current_user.id,
        symbol=alert_data.symbol.upper(),
        condition=alert_data.condition,
        target_price=alert_data.target_price,
        target_price_high=alert_data.target_price_high,
        notification_types=alert_data.notification_types,
        cooldown_minutes=alert_data.cooldown_minutes
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Alert created: {alert.id} ({alert.symbol} {alert.condition.value} {alert.target_price})")
    return alert


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update fields
    update_data = alert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Alert updated: {alert.id}")
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    db.delete(alert)
    db.commit()
    
    logger.info(f"Alert deleted: {alert_id}")


@router.post("/{alert_id}/toggle", response_model=AlertResponse)
async def toggle_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle alert active status."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.active = not alert.active
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Alert toggled: {alert.id} -> active={alert.active}")
    return alert
