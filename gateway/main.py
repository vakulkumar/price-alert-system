"""API Gateway - User-facing REST API and WebSocket for price alerts."""
import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# Add shared module to path
sys.path.insert(0, '/app')
from shared import get_settings, PriceEvent, KafkaConsumerWrapper, get_metrics, get_metrics_content_type
from shared.metrics import HTTP_REQUESTS, HTTP_LATENCY, SERVICE_INFO

from db import init_db
from routes import auth_router, alerts_router, prices_router, update_price_cache, broadcast_price

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
settings = get_settings()
kafka_consumer: KafkaConsumerWrapper = None
consumer_task: asyncio.Task = None


async def process_price_for_gateway(price_event: PriceEvent):
    """Process price event for gateway - update cache and broadcast."""
    price_data = {
        "symbol": price_event.symbol,
        "price": price_event.price,
        "currency": price_event.currency,
        "source": price_event.source.value,
        "timestamp": price_event.timestamp.isoformat()
    }
    
    # Update cache
    update_price_cache(price_event.symbol, price_data)
    
    # Broadcast to WebSocket clients
    await broadcast_price(price_data)


async def consume_prices():
    """Background task to consume price events for real-time updates."""
    global kafka_consumer
    
    try:
        await kafka_consumer.consume(process_price_for_gateway)
    except Exception as e:
        logger.error(f"Consumer error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka_consumer, consumer_task
    
    # Set service info
    SERVICE_INFO.info({
        'name': 'gateway',
        'version': '1.0.0',
        'environment': settings.environment
    })
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize Kafka consumer for price streaming
    kafka_consumer = KafkaConsumerWrapper(
        bootstrap_servers=settings.kafka.bootstrap_servers,
        topic=settings.kafka.price_events_topic,
        group_id=f"{settings.kafka.consumer_group_prefix}-gateway",
        schema_class=PriceEvent
    )
    await kafka_consumer.start()
    
    # Start consumer task
    consumer_task = asyncio.create_task(consume_prices())
    
    logger.info("API Gateway started")
    
    yield
    
    # Cleanup
    consumer_task.cancel()
    await kafka_consumer.stop()
    logger.info("API Gateway stopped")


# Create FastAPI app
app = FastAPI(
    title="Price Alert API",
    description="Real-time price alerts for crypto, stocks, and commodities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(prices_router)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Price Alert API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
