import json
import time
import logging
from solana.rpc.commitment import Confirmed
from solders.signature import Signature

from model.transaction_provider import TransactionProvider
from model.solana_provider import SolanaProvider

logger = logging.getLogger(__name__)

class SolanaTransactionProvider(TransactionProvider):
    """Solana implementation of TransactionProvider."""
    
    def __init__(self, solana_provider: SolanaProvider = None):
        """Initialize SolanaTransactionProvider.
        
        Args:
            solana_provider (Optional[SolanaProvider]): Solana provider instance.
                If None, uses default provider.
        """
        self._provider = solana_provider or SolanaProvider.get_instance()
        self._client = self._provider.rpc
        logger.info("Initialized SolanaTransactionProvider")
    
    def confirm_transaction(
        self,
        signature: Signature,
        max_retries: int = 20,
        retry_interval: int = 3
    ) -> bool:
        """Confirm a Solana transaction by its signature.
        
        Args:
            signature (Signature): Transaction signature to confirm
            max_retries (int, optional): Maximum number of confirmation attempts. Defaults to 20.
            retry_interval (int, optional): Time between retries in seconds. Defaults to 3.
            
        Returns:
            bool: True if transaction confirmed successfully, False otherwise
        """
        retries = 1
        logger.info(f"Confirming transaction: {signature}")
        
        while retries < max_retries:
            try:
                txn_res = self._client.get_transaction(
                    signature,
                    encoding="json",
                    commitment=Confirmed,
                    max_supported_transaction_version=0
                )
                
                txn_json = json.loads(txn_res.value.transaction.meta.to_json())
                
                if txn_json['err'] is None:
                    logger.info(f"Transaction confirmed after {retries} attempts")
                    return True
                
                logger.warning(f"Transaction not confirmed on attempt {retries}")
                if txn_json['err']:
                    logger.error(f"Transaction failed with error: {txn_json['err']}")
                    return False
            except Exception as e:
                logger.warning(f"Awaiting confirmation (attempt {retries}): {e}")
                retries += 1
                time.sleep(retry_interval)
        
        logger.error(f"Max retries ({max_retries}) reached. Transaction confirmation failed.")
        return False 