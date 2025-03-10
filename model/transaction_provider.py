from abc import ABC, abstractmethod
from typing import Optional
from solders.signature import Signature

class TransactionProvider(ABC):
    """Abstract base class for transaction-related operations."""
    
    @abstractmethod
    def confirm_transaction(
        self,
        signature: Signature,
        max_retries: int = 20,
        retry_interval: int = 3
    ) -> bool:
        """Confirm a transaction by its signature.
        
        Args:
            signature (Signature): Transaction signature to confirm
            max_retries (int, optional): Maximum number of confirmation attempts. Defaults to 20.
            retry_interval (int, optional): Time between retries in seconds. Defaults to 3.
            
        Returns:
            bool: True if transaction confirmed successfully, False otherwise
        """
        pass 