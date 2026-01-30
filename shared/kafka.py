"""Shared Kafka utilities for producers and consumers."""
import json
import logging
from typing import Any, Callable, Optional, Type
from datetime import datetime

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def json_serializer(obj: Any) -> bytes:
    """Serialize Python objects to JSON bytes."""
    if isinstance(obj, BaseModel):
        return obj.model_dump_json().encode('utf-8')
    if isinstance(obj, datetime):
        return json.dumps(obj.isoformat()).encode('utf-8')
    return json.dumps(obj).encode('utf-8')


def json_deserializer(data: bytes) -> dict:
    """Deserialize JSON bytes to Python dict."""
    return json.loads(data.decode('utf-8'))


class KafkaProducerWrapper:
    """Async Kafka producer with retry logic."""
    
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None
    
    async def start(self):
        """Start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=json_serializer,
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            retry_backoff_ms=100,
        )
        await self._producer.start()
        logger.info(f"Kafka producer connected to {self.bootstrap_servers}")
    
    async def stop(self):
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send(
        self,
        topic: str,
        value: BaseModel | dict,
        key: Optional[str] = None
    ) -> None:
        """Send a message to a Kafka topic."""
        if not self._producer:
            raise RuntimeError("Producer not started")
        
        try:
            await self._producer.send_and_wait(
                topic=topic,
                value=value,
                key=key
            )
            logger.debug(f"Sent message to {topic}: {key}")
        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            raise


class KafkaConsumerWrapper:
    """Async Kafka consumer with message handling."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        schema_class: Optional[Type[BaseModel]] = None
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.schema_class = schema_class
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
    
    async def start(self):
        """Start the Kafka consumer."""
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=json_deserializer,
            auto_offset_reset='latest',
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info(f"Kafka consumer started for topic {self.topic}")
    
    async def stop(self):
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def consume(
        self,
        handler: Callable[[Any], Any]
    ) -> None:
        """Consume messages and process with handler."""
        if not self._consumer:
            raise RuntimeError("Consumer not started")
        
        try:
            async for message in self._consumer:
                if not self._running:
                    break
                
                try:
                    # Parse message value
                    value = message.value
                    if self.schema_class:
                        value = self.schema_class.model_validate(value)
                    
                    # Process message
                    await handler(value)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Continue processing other messages
                    
        except Exception as e:
            if self._running:
                logger.error(f"Consumer error: {e}")
                raise
