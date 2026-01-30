"""Shared configuration management for all services."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class KafkaSettings(BaseSettings):
    """Kafka configuration."""
    bootstrap_servers: str = "localhost:9092"
    price_events_topic: str = "price-events"
    notifications_topic: str = "notifications"
    consumer_group_prefix: str = "price-alert"
    
    class Config:
        env_prefix = "KAFKA_"


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    url: str = "postgresql://alertuser:alertpass@localhost:5432/alertsdb"
    pool_size: int = 5
    max_overflow: int = 10
    
    class Config:
        env_prefix = "DATABASE_"


class RedisSettings(BaseSettings):
    """Redis configuration."""
    url: str = "redis://localhost:6379"
    alert_cache_ttl: int = 300  # 5 minutes
    rate_limit_window: int = 60  # 1 minute
    
    class Config:
        env_prefix = "REDIS_"


class Settings(BaseSettings):
    """Main application settings."""
    log_level: str = "INFO"
    environment: str = "development"
    
    # Nested settings
    kafka: KafkaSettings = KafkaSettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
