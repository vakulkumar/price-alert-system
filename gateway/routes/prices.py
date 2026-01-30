"""Price routes with WebSocket for real-time streaming."""
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import redis.asyncio as redis

from shared.metrics import ACTIVE_WEBSOCKETS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prices", tags=["Prices"])


# Schemas
class PriceData(BaseModel):
    symbol: str
    price: float
    currency: str
    source: str
    timestamp: datetime


# In-memory price cache (updated by Kafka consumer in main.py)
price_cache: Dict[str, dict] = {}

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


# All available symbols
AVAILABLE_SYMBOLS = {
    # Crypto
    "BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "USDC", "ADA", "AVAX", "DOGE",
    "DOT", "TRX", "LINK", "MATIC", "NEAR", "LTC", "SHIB", "BCH", "UNI", "XLM",
    "ATOM", "XMR", "ETC", "FIL", "ICP", "HBAR", "APT", "LDO", "ARB", "VET",
    # Stocks & Indices
    "NIFTY50", "SENSEX", "BANKNIFTY", "SP500", "DOWJONES", "NASDAQ",
    "GOLD", "SILVER", "CRUDE_OIL", "NATURAL_GAS",
    "APPLE", "MICROSOFT", "GOOGLE", "AMAZON", "NVIDIA", "META", "TESLA",
    "RELIANCE", "TCS", "INFOSYS", "HDFCBANK", "ICICIBANK", "HINDUNILVR", "ITC", "BHARTIARTL"
}


def update_price_cache(symbol: str, price_data: dict):
    """Update the price cache (called from Kafka consumer)."""
    global price_cache
    price_cache[symbol] = price_data


async def broadcast_price(price_data: dict):
    """Broadcast price update to all WebSocket connections."""
    if not active_connections:
        return
    
    message = json.dumps(price_data)
    disconnected = set()
    
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.add(connection)
    
    # Clean up disconnected clients
    active_connections.difference_update(disconnected)
    ACTIVE_WEBSOCKETS.set(len(active_connections))


@router.get("/")
async def list_prices(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols to filter")
):
    """Get current prices for all or specific symbols."""
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        prices = {
            s: price_cache.get(s)
            for s in symbol_list
            if s in price_cache
        }
    else:
        prices = dict(price_cache)
    
    return {
        "prices": prices,
        "count": len(prices),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/symbols")
async def list_symbols():
    """List all available symbols."""
    return {
        "symbols": sorted(AVAILABLE_SYMBOLS),
        "count": len(AVAILABLE_SYMBOLS)
    }


@router.get("/{symbol}")
async def get_price(symbol: str):
    """Get current price for a specific symbol."""
    symbol = symbol.upper()
    
    if symbol not in AVAILABLE_SYMBOLS:
        return {"error": f"Unknown symbol: {symbol}"}
    
    price_data = price_cache.get(symbol)
    
    if not price_data:
        return {
            "symbol": symbol,
            "price": None,
            "message": "Price not yet available"
        }
    
    return price_data


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price streaming."""
    await websocket.accept()
    active_connections.add(websocket)
    ACTIVE_WEBSOCKETS.set(len(active_connections))
    
    logger.info(f"WebSocket connected. Active: {len(active_connections)}")
    
    try:
        # Send current prices immediately
        if price_cache:
            await websocket.send_json({
                "type": "snapshot",
                "prices": price_cache,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong, subscription changes)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle subscription messages
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    finally:
        active_connections.discard(websocket)
        ACTIVE_WEBSOCKETS.set(len(active_connections))
