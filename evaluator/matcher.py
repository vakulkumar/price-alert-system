"""Alert matching engine with Redis caching."""
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import redis.asyncio as redis
from sqlalchemy.orm import Session

from models import Alert, AlertCondition, User
from shared.schemas import PriceEvent, NotificationEvent, NotificationType as SchemaNotificationType

logger = logging.getLogger(__name__)


class AlertMatcher:
    """Matches price events against user alerts."""
    
    def __init__(self, redis_url: str, session_factory):
        self.redis_url = redis_url
        self.session_factory = session_factory
        self._redis: Optional[redis.Redis] = None
        self._alert_cache: Dict[str, List[dict]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def connect(self):
        """Connect to Redis."""
        self._redis = redis.from_url(self.redis_url)
        logger.info("Connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
    
    async def _get_alerts_for_symbol(self, symbol: str) -> List[dict]:
        """Get all active alerts for a symbol (with caching)."""
        cache_key = f"alerts:{symbol}"
        
        # Try cache first
        if self._redis:
            cached = await self._redis.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # Fetch from database
        session: Session = self.session_factory()
        try:
            alerts = session.query(Alert).filter(
                Alert.symbol == symbol,
                Alert.active == True
            ).all()
            
            # Convert to dicts with user info
            alert_dicts = []
            for alert in alerts:
                user = session.query(User).filter(User.id == alert.user_id).first()
                if user and user.is_active:
                    alert_dicts.append({
                        "id": alert.id,
                        "user_id": alert.user_id,
                        "user_email": user.email,
                        "user_phone": user.phone,
                        "symbol": alert.symbol,
                        "condition": alert.condition.value,
                        "target_price": alert.target_price,
                        "target_price_high": alert.target_price_high,
                        "notification_types": alert.get_notification_types(),
                        "cooldown_minutes": alert.cooldown_minutes,
                        "last_triggered_at": alert.last_triggered_at.isoformat() if alert.last_triggered_at else None
                    })
            
            # Cache results
            if self._redis and alert_dicts:
                await self._redis.setex(
                    cache_key,
                    self._cache_ttl,
                    json.dumps(alert_dicts)
                )
            
            return alert_dicts
            
        finally:
            session.close()
    
    def _check_condition(
        self,
        condition: str,
        target_price: float,
        target_price_high: Optional[float],
        current_price: float,
        previous_price: Optional[float]
    ) -> bool:
        """Check if a price condition is met."""
        
        if condition == AlertCondition.ABOVE.value:
            return current_price >= target_price
        
        elif condition == AlertCondition.BELOW.value:
            return current_price <= target_price
        
        elif condition == AlertCondition.CROSSES.value:
            if previous_price is None:
                return False
            # Check if price crossed the target
            crossed_up = previous_price < target_price <= current_price
            crossed_down = previous_price > target_price >= current_price
            return crossed_up or crossed_down
        
        elif condition == AlertCondition.RANGE.value:
            if target_price_high is None:
                return False
            return target_price <= current_price <= target_price_high
        
        return False
    
    def _can_trigger(self, alert: dict) -> bool:
        """Check if alert can trigger (respects cooldown)."""
        last_triggered = alert.get("last_triggered_at")
        if not last_triggered:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_triggered)
            elapsed = (datetime.utcnow() - last_time).total_seconds()
            cooldown_seconds = alert.get("cooldown_minutes", 60) * 60
            return elapsed >= cooldown_seconds
        except:
            return True
    
    async def match(self, price_event: PriceEvent) -> List[NotificationEvent]:
        """Match a price event against all relevant alerts."""
        notifications = []
        
        # Get alerts for this symbol
        alerts = await self._get_alerts_for_symbol(price_event.symbol)
        
        for alert in alerts:
            # Check cooldown
            if not self._can_trigger(alert):
                continue
            
            # Check condition
            triggered = self._check_condition(
                condition=alert["condition"],
                target_price=alert["target_price"],
                target_price_high=alert.get("target_price_high"),
                current_price=price_event.price,
                previous_price=price_event.previous_price
            )
            
            if triggered:
                # Create notification event
                notification_types = [
                    SchemaNotificationType(t) for t in alert["notification_types"]
                ]
                
                notification = NotificationEvent(
                    alert_id=alert["id"],
                    user_id=alert["user_id"],
                    user_email=alert["user_email"],
                    user_phone=alert.get("user_phone"),
                    symbol=price_event.symbol,
                    condition=alert["condition"],
                    target_price=alert["target_price"],
                    current_price=price_event.price,
                    notification_types=notification_types
                )
                notifications.append(notification)
                
                # Update last triggered time in database
                await self._update_trigger_time(alert["id"])
                
                # Invalidate cache
                if self._redis:
                    await self._redis.delete(f"alerts:{price_event.symbol}")
                
                logger.info(
                    f"Alert triggered: {alert['id']} for {price_event.symbol} "
                    f"({alert['condition']} {alert['target_price']})"
                )
        
        return notifications
    
    async def _update_trigger_time(self, alert_id: int):
        """Update the last triggered time for an alert."""
        session: Session = self.session_factory()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.last_triggered_at = datetime.utcnow()
                alert.triggered_count += 1
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update trigger time: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def invalidate_cache(self, symbol: Optional[str] = None):
        """Invalidate alert cache."""
        if self._redis:
            if symbol:
                await self._redis.delete(f"alerts:{symbol}")
            else:
                # Invalidate all alert caches
                async for key in self._redis.scan_iter("alerts:*"):
                    await self._redis.delete(key)
