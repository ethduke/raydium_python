from abc import ABC, abstractmethod
from typing import Dict, Optional

class APIProvider(ABC):
    """Abstract base class for API providers."""
    
    @abstractmethod
    def get_pool_info_by_id(self, pool_id: str) -> Dict:
        """Get pool information by pool ID.
        
        Args:
            pool_id (str): The pool ID to query
            
        Returns:
            Dict: Pool information
        """
        pass
    
    @abstractmethod
    def get_pool_info_by_mint(
        self, 
        mint: str, 
        pool_type: str = "all",
        sort_field: str = "default",
        sort_type: str = "desc",
        page_size: int = 100,
        page: int = 1
    ) -> Dict:
        """Get pool information by mint address.
        
        Args:
            mint (str): The mint address to query
            pool_type (str, optional): Type of pool. Defaults to "all".
            sort_field (str, optional): Field to sort by. Defaults to "default".
            sort_type (str, optional): Sort direction. Defaults to "desc".
            page_size (int, optional): Number of results per page. Defaults to 100.
            page (int, optional): Page number. Defaults to 1.
            
        Returns:
            Dict: Pool information
        """
        pass 