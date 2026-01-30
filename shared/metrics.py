"""Prometheus metrics helpers for all services."""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time


# ============================================
# Ingestor Metrics
# ============================================

PRICES_FETCHED = Counter(
    'ingestor_prices_fetched_total',
    'Total number of prices fetched',
    ['source', 'symbol']
)

FETCH_ERRORS = Counter(
    'ingestor_fetch_errors_total',
    'Total number of fetch errors',
    ['source']
)

FETCH_LATENCY = Histogram(
    'ingestor_fetch_latency_seconds',
    'Time to fetch prices from source',
    ['source'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

KAFKA_MESSAGES_SENT = Counter(
    'ingestor_kafka_messages_sent_total',
    'Total Kafka messages sent',
    ['topic']
)


# ============================================
# Evaluator Metrics
# ============================================

PRICES_EVALUATED = Counter(
    'evaluator_prices_evaluated_total',
    'Total number of prices evaluated',
    ['symbol']
)

ALERTS_TRIGGERED = Counter(
    'evaluator_alerts_triggered_total',
    'Total number of alerts triggered',
    ['condition']
)

ALERT_MATCH_LATENCY = Histogram(
    'evaluator_match_latency_seconds',
    'Time to match alerts against a price',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

ACTIVE_ALERTS = Gauge(
    'evaluator_active_alerts',
    'Number of active alerts in the system'
)


# ============================================
# Notifier Metrics
# ============================================

NOTIFICATIONS_SENT = Counter(
    'notifier_notifications_sent_total',
    'Total notifications sent',
    ['type', 'status']
)

NOTIFICATION_LATENCY = Histogram(
    'notifier_send_latency_seconds',
    'Time to send notifications',
    ['type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)


# ============================================
# Gateway Metrics
# ============================================

HTTP_REQUESTS = Counter(
    'gateway_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

HTTP_LATENCY = Histogram(
    'gateway_http_latency_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

ACTIVE_WEBSOCKETS = Gauge(
    'gateway_active_websockets',
    'Number of active WebSocket connections'
)


# ============================================
# Shared Metrics
# ============================================

KAFKA_CONSUMER_LAG = Gauge(
    'kafka_consumer_lag',
    'Kafka consumer lag',
    ['topic', 'partition', 'group']
)

SERVICE_INFO = Info(
    'service',
    'Service information'
)


def track_latency(histogram: Histogram, labels: dict = None):
    """Decorator to track function execution latency."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                if labels:
                    histogram.labels(**labels).observe(duration)
                else:
                    histogram.observe(duration)
        return wrapper
    return decorator


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST
