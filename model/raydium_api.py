import requests
from typing import Dict
import logging

from model.api_provider import APIProvider
from config import config

# Configure logging
logger = logging.getLogger(__name__)

class RaydiumAPI(APIProvider):
    """Raydium API implementation."""
    
    def __init__(self):
        """Initialize RaydiumAPI with configuration."""
        self.config = config
        self.base_url = self.config.get("programs.raydium.api_v3_pools_info_url")
        logger.info(f"Initialized RaydiumAPI with base URL: {self.base_url}")
    
    def get_pool_info_by_id(self, pool_id: str) -> Dict:
        """Get pool information by pool ID.
        
        Args:
            pool_id (str): The pool ID to query
            
        Returns:
            Dict: Pool information or error message
        """
        IDS = "ids"
        url = f"{self.base_url}{IDS}"
        params = {IDS: pool_id}
        
        try:
            logger.info(f"Fetching pool info for ID: {pool_id}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch pool info: {e}"
            logger.error(error_msg)
            return {"error": error_msg}
    
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
            Dict: Pool information or error message
        """
        url = f"{self.base_url}mint"
        params = {
            "mint1": mint,
            "poolType": pool_type,
            "poolSortField": sort_field,
            "sortType": sort_type,
            "pageSize": page_size,
            "page": page
        }
        
        try:
            logger.info(f"Fetching pool info for mint: {mint}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch pool info: {e}"
            logger.error(error_msg)
            return {"error": error_msg} 