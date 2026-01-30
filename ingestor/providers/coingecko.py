"""CoinGecko provider for cryptocurrency prices."""
import logging
import time
from typing import List, Dict, Optional

import httpx

from shared.schemas import PriceEvent, PriceSource
from shared.metrics import FETCH_LATENCY
from .base import BasePriceProvider

logger = logging.getLogger(__name__)

# Top 30 cryptocurrencies by market cap
CRYPTO_IDS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "tether": "USDT",
    "binancecoin": "BNB",
    "solana": "SOL",
    "ripple": "XRP",
    "usd-coin": "USDC",
    "cardano": "ADA",
    "avalanche-2": "AVAX",
    "dogecoin": "DOGE",
    "polkadot": "DOT",
    "tron": "TRX",
    "chainlink": "LINK",
    "polygon": "MATIC",
    "near": "NEAR",
    "litecoin": "LTC",
    "shiba-inu": "SHIB",
    "bitcoin-cash": "BCH",
    "uniswap": "UNI",
    "stellar": "XLM",
    "cosmos": "ATOM",
    "monero": "XMR",
    "ethereum-classic": "ETC",
    "filecoin": "FIL",
    "internet-computer": "ICP",
    "hedera-hashgraph": "HBAR",
    "aptos": "APT",
    "lido-dao": "LDO",
    "arbitrum": "ARB",
    "vechain": "VET",
}


class CoinGeckoProvider(BasePriceProvider):
    """Fetches cryptocurrency prices from CoinGecko API."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        self._previous_prices: Dict[str, float] = {}
    
    @property
    def name(self) -> str:
        return "coingecko"
    
    def get_symbols(self) -> List[str]:
        return list(CRYPTO_IDS.values())
    
    async def fetch_prices(self) -> List[PriceEvent]:
        """Fetch current prices for all tracked cryptocurrencies."""
        start_time = time.time()
        
        try:
            # Fetch prices in one API call
            ids = ",".join(CRYPTO_IDS.keys())
            response = await self._client.get(
                f"{self.BASE_URL}/simple/price",
                params={
                    "ids": ids,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Convert to PriceEvents
            events = []
            for coin_id, symbol in CRYPTO_IDS.items():
                if coin_id in data:
                    price = data[coin_id].get("usd", 0)
                    previous_price = self._previous_prices.get(symbol)
                    
                    event = PriceEvent(
                        symbol=symbol,
                        price=price,
                        previous_price=previous_price,
                        currency="USD",
                        source=PriceSource.COINGECKO
                    )
                    events.append(event)
                    
                    # Store for next iteration
                    self._previous_prices[symbol] = price
            
            # Record latency
            FETCH_LATENCY.labels(source=self.name).observe(time.time() - start_time)
            
            return events
            
        except Exception as e:
            logger.error(f"CoinGecko API error: {e}")
            FETCH_LATENCY.labels(source=self.name).observe(time.time() - start_time)
            raise
