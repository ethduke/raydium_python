import logging
from typing import Optional
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey

from model.token_provider import TokenProvider
from model.solana_provider import SolanaProvider

logger = logging.getLogger(__name__)

class SolanaTokenProvider(TokenProvider):
    """Solana implementation of TokenProvider."""
    
    def __init__(self, solana_provider: Optional[SolanaProvider] = None):
        """Initialize SolanaTokenProvider.
        
        Args:
            solana_provider (Optional[SolanaProvider]): Solana provider instance.
                If None, uses default provider.
        """
        self._provider = solana_provider or SolanaProvider.get_instance()
        self._client = self._provider.rpc
        self._payer = self._provider.payer
        logger.info(f"Initialized SolanaTokenProvider with payer: {self._payer.pubkey()}")
    
    def get_token_balance(self, mint: str | Pubkey) -> Optional[float]:
        """Get token balance for a specific mint.
        
        Args:
            mint (str | Pubkey): Token mint address as string or Pubkey
            
        Returns:
            Optional[float]: Token balance if found, None otherwise
        """
        try:
            if not self._payer:
                logger.error("Cannot get token balance: payer_keypair is not initialized")
                return None
            
            mint_pubkey = mint if isinstance(mint, Pubkey) else Pubkey.from_string(mint)
            logger.info(f"Getting token balance for mint: {mint_pubkey}")
            
            response = self._client.get_token_accounts_by_owner_json_parsed(
                self._payer.pubkey(),
                TokenAccountOpts(mint=mint_pubkey),
                commitment=Processed
            )

            if response.value:
                accounts = response.value
                if accounts:
                    token_amount = accounts[0].account.data.parsed['info']['tokenAmount']['uiAmount']
                    if token_amount:
                        logger.info(f"Token balance: {token_amount}")
                        return float(token_amount)
            
            logger.warning(f"No token balance found for mint: {mint_pubkey}")
            return None
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return None 