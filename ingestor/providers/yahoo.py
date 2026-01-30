"""Yahoo Finance provider for stocks, indices, and commodities."""
import logging
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from shared.schemas import PriceEvent, PriceSource
from shared.metrics import FETCH_LATENCY
from .base import BasePriceProvider

logger = logging.getLogger(__name__)

# 25 popular stocks, indices, and commodities
YAHOO_SYMBOLS = {
    # Indian Indices
    "^NSEI": "NIFTY50",
    "^BSESN": "SENSEX",
    "^NSEBANK": "BANKNIFTY",
    
    # US Indices
    "^GSPC": "SP500",
    "^DJI": "DOWJONES",
    "^IXIC": "NASDAQ",
    
    # Commodities
    "GC=F": "GOLD",
    "SI=F": "SILVER",
    "CL=F": "CRUDE_OIL",
    "NG=F": "NATURAL_GAS",
    
    # Major US Stocks
    "AAPL": "APPLE",
    "MSFT": "MICROSOFT",
    "GOOGL": "GOOGLE",
    "AMZN": "AMAZON",
    "NVDA": "NVIDIA",
    "META": "META",
    "TSLA": "TESLA",
    
    # Indian Stocks (NSE)
    "RELIANCE.NS": "RELIANCE",
    "TCS.NS": "TCS",
    "INFY.NS": "INFOSYS",
    "HDFCBANK.NS": "HDFCBANK",
    "ICICIBANK.NS": "ICICIBANK",
    "HINDUNILVR.NS": "HINDUNILVR",
    "ITC.NS": "ITC",
    "BHARTIARTL.NS": "BHARTIARTL",
}


class YahooFinanceProvider(BasePriceProvider):
    """Fetches stock/index prices from Yahoo Finance."""
    
    def __init__(self):
        self._previous_prices: Dict[str, float] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    @property
    def name(self) -> str:
        return "yahoo"
    
    def get_symbols(self) -> List[str]:
        return list(YAHOO_SYMBOLS.values())
    
    def _fetch_sync(self, symbols: List[str]) -> Dict:
        """Synchronous fetch using yfinance."""
        try:
            tickers = yf.Tickers(" ".join(symbols))
            results = {}
            
            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        info = ticker.fast_info
                        results[symbol] = {
                            "price": info.get("lastPrice") or info.get("regularMarketPrice", 0),
                            "currency": info.get("currency", "USD")
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol}: {e}")
                    
            return results
        except Exception as e:
            logger.error(f"Yahoo Finance batch fetch error: {e}")
            return {}
    
    async def fetch_prices(self) -> List[PriceEvent]:
        """Fetch current prices for all tracked instruments."""
        import asyncio
        
        start_time = time.time()
        
        try:
            # Run sync yfinance in thread pool
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                self._executor,
                self._fetch_sync,
                list(YAHOO_SYMBOLS.keys())
            )
            
            # Convert to PriceEvents
            events = []
            for yahoo_symbol, display_symbol in YAHOO_SYMBOLS.items():
                if yahoo_symbol in data:
                    price_data = data[yahoo_symbol]
                    price = price_data.get("price", 0)
                    
                    if price and price > 0:
                        previous_price = self._previous_prices.get(display_symbol)
                        
                        event = PriceEvent(
                            symbol=display_symbol,
                            price=price,
                            previous_price=previous_price,
                            currency=price_data.get("currency", "USD"),
                            source=PriceSource.YAHOO
                        )
                        events.append(event)
                        
                        # Store for next iteration
                        self._previous_prices[display_symbol] = price
            
            # Record latency
            FETCH_LATENCY.labels(source=self.name).observe(time.time() - start_time)
            
            logger.info(f"Fetched {len(events)} prices from Yahoo Finance")
            return events
            
        except Exception as e:
            logger.error(f"Yahoo Finance error: {e}")
            FETCH_LATENCY.labels(source=self.name).observe(time.time() - start_time)
            raise
