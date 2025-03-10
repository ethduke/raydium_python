from solana.rpc.api import Client as SolanaClient
from solders.keypair import Keypair
from config import Config

class SolanaProvider:
    """
    SolanaProvider class that encapsulates Solana RPC client functionality.
    Follows the singleton pattern to ensure only one instance exists.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of the SolanaProvider class.
        
        Returns:
            SolanaProvider: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Initialize the SolanaProvider with configuration from Config class.
        This should not be called directly - use get_instance() instead.
        """
        config = Config()
        self._client = config.get_solana_rpc_client()
        self._payer = config.get_payer_keypair()
    
    @property
    def rpc(self):
        """
        Get the Solana RPC client.
        
        Returns:
            SolanaClient: The Solana RPC client
        """
        return self._client
    
    @property
    def payer(self):
        """
        Get the payer keypair.
        
        Returns:
            Keypair: The payer keypair
        """
        return self._payer 