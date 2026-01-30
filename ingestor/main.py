"""Ingestor Service - Fetches real-time prices from multiple sources."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Response
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Add shared module to path
sys.path.insert(0, '/app')
from shared import get_settings, PriceEvent, KafkaProducerWrapper, get_metrics, get_metrics_content_type
from shared.metrics import PRICES_FETCHED, FETCH_ERRORS, KAFKA_MESSAGES_SENT, SERVICE_INFO

from providers.coingecko import CoinGeckoProvider
from providers.yahoo import YahooFinanceProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
settings = get_settings()
kafka_producer: KafkaProducerWrapper = None
scheduler: AsyncIOScheduler = None
providers = []


async def fetch_and_publish_prices():
    """Fetch prices from all providers and publish to Kafka."""
    global kafka_producer, providers
    
    for provider in providers:
        try:
            prices = await provider.fetch_prices()
            
            for price_event in prices:
                # Publish to Kafka
                await kafka_producer.send(
                    topic=settings.kafka.price_events_topic,
                    value=price_event,
                    key=price_event.symbol
                )
                
                # Update metrics
                PRICES_FETCHED.labels(
                    source=price_event.source.value,
                    symbol=price_event.symbol
                ).inc()
                
            KAFKA_MESSAGES_SENT.labels(
                topic=settings.kafka.price_events_topic
            ).inc(len(prices))
            
            logger.info(f"Published {len(prices)} prices from {provider.name}")
            
        except Exception as e:
            logger.error(f"Error fetching from {provider.name}: {e}")
            FETCH_ERRORS.labels(source=provider.name).inc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka_producer, scheduler, providers
    
    # Set service info
    SERVICE_INFO.info({
        'name': 'ingestor',
        'version': '1.0.0',
        'environment': settings.environment
    })
    
    # Initialize Kafka producer
    kafka_producer = KafkaProducerWrapper(settings.kafka.bootstrap_servers)
    await kafka_producer.start()
    
    # Initialize providers
    providers = [
        CoinGeckoProvider(),
        YahooFinanceProvider(),
    ]
    
    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        fetch_and_publish_prices,
        'interval',
        seconds=5,
        id='price_fetch',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Price fetcher started (every 5 seconds)")
    
    # Fetch immediately on startup
    await fetch_and_publish_prices()
    
    yield
    
    # Cleanup
    scheduler.shutdown()
    await kafka_producer.stop()
    logger.info("Ingestor service stopped")


# Create FastAPI app
app = FastAPI(
    title="Price Ingestor Service",
    description="Fetches real-time prices and publishes to Kafka",
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


@app.get("/instruments")
async def list_instruments():
    """List all tracked instruments."""
    instruments = []
    for provider in providers:
        instruments.extend([
            {"symbol": sym, "source": provider.name}
            for sym in provider.get_symbols()
        ])
    return {"instruments": instruments, "count": len(instruments)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
