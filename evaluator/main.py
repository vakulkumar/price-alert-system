"""Evaluator Service - Matches prices against user alerts."""
import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Response

# Add shared module to path
sys.path.insert(0, '/app')
from shared import get_settings, PriceEvent, KafkaConsumerWrapper, KafkaProducerWrapper
from shared import get_metrics, get_metrics_content_type
from shared.metrics import PRICES_EVALUATED, ALERTS_TRIGGERED, ALERT_MATCH_LATENCY, ACTIVE_ALERTS, SERVICE_INFO

from models import init_db, get_session_factory, Alert
from matcher import AlertMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
settings = get_settings()
kafka_consumer: KafkaConsumerWrapper = None
kafka_producer: KafkaProducerWrapper = None
matcher: AlertMatcher = None
consumer_task: asyncio.Task = None


async def process_price_event(price_event: PriceEvent):
    """Process a price event and trigger matching alerts."""
    global matcher, kafka_producer
    
    import time
    start_time = time.time()
    
    # Update metrics
    PRICES_EVALUATED.labels(symbol=price_event.symbol).inc()
    
    # Find matching alerts
    notifications = await matcher.match(price_event)
    
    # Publish notifications to Kafka
    for notification in notifications:
        await kafka_producer.send(
            topic=settings.kafka.notifications_topic,
            value=notification,
            key=str(notification.user_id)
        )
        ALERTS_TRIGGERED.labels(condition=notification.condition).inc()
    
    # Record latency
    ALERT_MATCH_LATENCY.observe(time.time() - start_time)
    
    if notifications:
        logger.info(f"Triggered {len(notifications)} alerts for {price_event.symbol} @ {price_event.price}")


async def consume_prices():
    """Background task to consume price events."""
    global kafka_consumer
    
    try:
        await kafka_consumer.consume(process_price_event)
    except Exception as e:
        logger.error(f"Consumer error: {e}")


async def update_active_alerts_metric():
    """Periodically update the active alerts gauge."""
    session_factory = get_session_factory()
    while True:
        try:
            session = session_factory()
            count = session.query(Alert).filter(Alert.active == True).count()
            ACTIVE_ALERTS.set(count)
            session.close()
        except Exception as e:
            logger.error(f"Failed to update alerts metric: {e}")
        
        await asyncio.sleep(30)  # Update every 30 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka_consumer, kafka_producer, matcher, consumer_task
    
    # Set service info
    SERVICE_INFO.info({
        'name': 'evaluator',
        'version': '1.0.0',
        'environment': settings.environment
    })
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize alert matcher with Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    matcher = AlertMatcher(redis_url, get_session_factory())
    await matcher.connect()
    
    # Initialize Kafka producer (for notifications)
    kafka_producer = KafkaProducerWrapper(settings.kafka.bootstrap_servers)
    await kafka_producer.start()
    
    # Initialize Kafka consumer (for price events)
    kafka_consumer = KafkaConsumerWrapper(
        bootstrap_servers=settings.kafka.bootstrap_servers,
        topic=settings.kafka.price_events_topic,
        group_id=f"{settings.kafka.consumer_group_prefix}-evaluator",
        schema_class=PriceEvent
    )
    await kafka_consumer.start()
    
    # Start consumer task
    consumer_task = asyncio.create_task(consume_prices())
    
    # Start metrics updater
    metrics_task = asyncio.create_task(update_active_alerts_metric())
    
    logger.info("Evaluator service started")
    
    yield
    
    # Cleanup
    consumer_task.cancel()
    metrics_task.cancel()
    await kafka_consumer.stop()
    await kafka_producer.stop()
    await matcher.disconnect()
    logger.info("Evaluator service stopped")


# Create FastAPI app
app = FastAPI(
    title="Alert Evaluator Service",
    description="Evaluates prices against user alerts",
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


@app.post("/cache/invalidate")
async def invalidate_cache(symbol: str = None):
    """Invalidate alert cache (called when alerts are modified)."""
    await matcher.invalidate_cache(symbol)
    return {"status": "ok", "symbol": symbol}


@app.get("/stats")
async def get_stats():
    """Get evaluator statistics."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        active_alerts = session.query(Alert).filter(Alert.active == True).count()
        total_alerts = session.query(Alert).count()
        
        return {
            "active_alerts": active_alerts,
            "total_alerts": total_alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
