"""Base provider interface for price data sources."""
from abc import ABC, abstractmethod
from typing import List
from shared.schemas import PriceEvent


class BasePriceProvider(ABC):
    """Abstract base class for price data providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @abstractmethod
    async def fetch_prices(self) -> List[PriceEvent]:
        """Fetch current prices for all tracked instruments."""
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """Get list of tracked symbols."""
        pass
