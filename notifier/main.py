"""Notifier Service - Sends email/SMS notifications for triggered alerts."""
import asyncio
import logging
import sys
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, Response
import redis.asyncio as redis

# Add shared module to path
sys.path.insert(0, '/app')
from shared import get_settings, NotificationEvent, KafkaConsumerWrapper, NotificationType
from shared import get_metrics, get_metrics_content_type
from shared.metrics import NOTIFICATIONS_SENT, NOTIFICATION_LATENCY, SERVICE_INFO

from handlers import EmailHandler, SMSHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
settings = get_settings()
kafka_consumer: KafkaConsumerWrapper = None
email_handler: EmailHandler = None
sms_handler: SMSHandler = None
redis_client: redis.Redis = None
consumer_task: asyncio.Task = None

# Rate limiting: max notifications per user per minute
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10


async def check_rate_limit(user_id: int) -> bool:
    """Check if user has exceeded rate limit."""
    global redis_client
    
    if not redis_client:
        return True
    
    key = f"rate_limit:{user_id}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, RATE_LIMIT_WINDOW)
        
        if count > RATE_LIMIT_MAX:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True  # Allow on error


async def process_notification(notification: NotificationEvent):
    """Process a notification event and send to appropriate channels."""
    global email_handler, sms_handler
    
    # Check rate limit
    if not await check_rate_limit(notification.user_id):
        logger.info(f"Skipping notification due to rate limit: {notification.alert_id}")
        return
    
    for notification_type in notification.notification_types:
        start_time = time.time()
        success = False
        
        try:
            if notification_type == NotificationType.EMAIL:
                success = await email_handler.send(notification)
            elif notification_type == NotificationType.SMS:
                success = await sms_handler.send(notification)
            
            # Update metrics
            status = "success" if success else "failed"
            NOTIFICATIONS_SENT.labels(
                type=notification_type.value,
                status=status
            ).inc()
            
            NOTIFICATION_LATENCY.labels(
                type=notification_type.value
            ).observe(time.time() - start_time)
            
        except Exception as e:
            logger.error(f"Error sending {notification_type.value}: {e}")
            NOTIFICATIONS_SENT.labels(
                type=notification_type.value,
                status="error"
            ).inc()


async def consume_notifications():
    """Background task to consume notification events."""
    global kafka_consumer
    
    try:
        await kafka_consumer.consume(process_notification)
    except Exception as e:
        logger.error(f"Consumer error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka_consumer, email_handler, sms_handler, redis_client, consumer_task
    
    # Set service info
    SERVICE_INFO.info({
        'name': 'notifier',
        'version': '1.0.0',
        'environment': settings.environment
    })
    
    # Initialize Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url)
    
    # Initialize handlers
    email_handler = EmailHandler()
    sms_handler = SMSHandler()
    
    # Initialize Kafka consumer
    kafka_consumer = KafkaConsumerWrapper(
        bootstrap_servers=settings.kafka.bootstrap_servers,
        topic=settings.kafka.notifications_topic,
        group_id=f"{settings.kafka.consumer_group_prefix}-notifier",
        schema_class=NotificationEvent
    )
    await kafka_consumer.start()
    
    # Start consumer task
    consumer_task = asyncio.create_task(consume_notifications())
    
    logger.info("Notifier service started")
    
    yield
    
    # Cleanup
    consumer_task.cancel()
    await kafka_consumer.stop()
    await redis_client.close()
    logger.info("Notifier service stopped")


# Create FastAPI app
app = FastAPI(
    title="Notification Service",
    description="Sends email/SMS notifications for triggered alerts",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


@app.get("/stats")
async def get_stats():
    """Get notifier statistics."""
    return {
        "email_configured": bool(email_handler.smtp_user),
        "sms_configured": bool(sms_handler._client),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
