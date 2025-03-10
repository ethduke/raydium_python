from abc import ABC, abstractmethod
from typing import Optional
from solders.pubkey import Pubkey

class TokenProvider(ABC):
    """Abstract base class for token-related operations."""
    
    @abstractmethod
    def get_token_balance(self, mint: str | Pubkey) -> Optional[float]:
        """Get token balance for a specific mint.
        
        Args:
            mint (str | Pubkey): Token mint address as string or Pubkey
            
        Returns:
            Optional[float]: Token balance if found, None otherwise
        """
        pass 