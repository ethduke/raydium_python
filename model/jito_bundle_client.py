import requests
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from typing import Dict, Any
from config import config
import random
import base64
import time
import logging
from model.solana_provider import SolanaProvider
from model.solana_transaction_provider import SolanaTransactionProvider

logger = logging.getLogger(__name__)

class HeliusSenderClient:
    """Client for sending transactions via Helius with Jito tips (like the JavaScript example)"""
    
    def __init__(self, enable_confirmation: bool = False):
        self.rpc_url = config.get_solana_rpc_url()
        self.enable_confirmation = enable_confirmation
        
        # Helius Sender endpoints (updated with correct working endpoints)
        self.helius_sender_endpoints = [
            "http://slc-sender.helius-rpc.com/fast",    # Salt Lake City
            "http://ewr-sender.helius-rpc.com/fast",    # Newark (was ny-sender)
            "http://lon-sender.helius-rpc.com/fast",    # London
            "http://fra-sender.helius-rpc.com/fast",    # Frankfurt
            "http://ams-sender.helius-rpc.com/fast",    # Amsterdam (was amsterdam-sender)
            "http://sg-sender.helius-rpc.com/fast",     # Singapore
            "http://tyo-sender.helius-rpc.com/fast"     # Tokyo
        ]
        
        self.session = requests.Session()
        # Initialize client for getting latest blockhash
        self.client = SolanaProvider.get_instance().rpc
        
        # Initialize transaction provider for confirmation if enabled
        if self.enable_confirmation:
            self.transaction_provider = SolanaTransactionProvider()
            logger.info("HeliusSenderClient initialized with transaction confirmation enabled")
        else:
            self.transaction_provider = None
            logger.info("HeliusSenderClient initialized without transaction confirmation")
        
        # Jito tip accounts 
        self.tip_accounts = [
            "4ACfpUFoaSD9bfPdeu6DBt89gB6ENTeHBXCAi87NhDEE",
            "D2L6yPZ2FmmmTKPgzaMKdhu6EWZcTpLy1Vhx8uvZe7NZ", 
            "9bnz4RShgq1hAnLnZbP8kbgBg1kEmcJBYQq3gQbmnSta",
            "5VY91ws6B2hMmBFRsXkoAAdsPHBJwRfBht4DXox3xkwn",
            "2nyhqdwKcJZR2vcqCyrYsaPVdAnFoJjiksCXJ7hfEYgD",
            "2q5pghRs6arqVjRvT5gfgWfWcHWmw1ZuCzphgd5KfWGJ",
            "wyvPkWjVZz1M8fHQnMMCDTQDbkManefNNhweYk5WkcF",
            "3KCKozbAaF75qEU33jtzozcJ29yJuaLJTy2jFdzUY8bT",
            "4vieeGHPYPG2MmyPRcYjdiDmmhN3ww7hsFNap8pVN3Ey",
            "4TQLFNWK8AovT1gFvda5jfw2oJeRMKEmw7aH6MGBJ3or"
        ]

    def get_random_tip_account(self) -> Pubkey:
        """Get a random tip account for load balancing"""
        tip_account_str = random.choice(self.tip_accounts)
        return Pubkey.from_string(tip_account_str)

    def send_with_jito_tips(self, transaction: VersionedTransaction, confirm_transaction: bool = False) -> Dict[str, Any]:
        """Send transaction via Helius with Jito tips (following JavaScript example)"""
        
        try:
            logger.info(f"📡 Sending transaction with Jito tip")
            
            # Serialize transaction
            serialized = bytes(transaction)
            encoded = base64.b64encode(serialized).decode()
            
            payload = {
                "jsonrpc": "2.0",
                "id": str(int(time.time())),
                "method": "sendTransaction", 
                "params": [
                    encoded,
                    {
                        "encoding": "base64",
                        "skipPreflight": True,  # Required for Sender
                        "maxRetries": 0
                    }
                ]
            }
            
            logger.info(f"Transaction size: {len(serialized)} bytes")
            
            # Try sender endpoints in order
            for i, endpoint in enumerate(self.helius_sender_endpoints):
                try:
                    logger.info(f"Trying endpoint {i+1}: {endpoint}")
                    
                    response = self.session.post(
                        endpoint, 
                        json=payload, 
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if "result" in result:
                        signature = result["result"]
                        logger.info(f"✅ Transaction sent successfully via Helius Sender!")
                        logger.info(f"Signature: {signature}")
                        logger.info(f"Endpoint: {endpoint}")
                        
                        response_data = {
                            "signature": signature,
                            "method": "helius_sender",
                            "endpoint": endpoint,
                            "success": True
                        }
                        
                        # Optionally confirm transaction if enabled
                        if confirm_transaction and (self.enable_confirmation or self.transaction_provider):
                            try:
                                logger.info("🔄 Confirming transaction...")
                                signature_obj = Signature.from_string(signature)
                                
                                # Use existing provider or create temporary one
                                tx_provider = self.transaction_provider or SolanaTransactionProvider()
                                confirmed = tx_provider.confirm_transaction(signature_obj)
                                
                                response_data["confirmed"] = confirmed
                                if confirmed:
                                    logger.info("✅ Transaction confirmed successfully!")
                                else:
                                    logger.warning("⚠️ Transaction sent but confirmation failed")
                                    
                            except Exception as e:
                                logger.warning(f"Transaction confirmation failed: {e}")
                                response_data["confirmed"] = False
                                response_data["confirmation_error"] = str(e)
                        
                        return response_data
                    else:
                        logger.warning(f"❌ Endpoint returned error: {result}")
                        continue
                        
                except Exception as e:
                    logger.warning(f"❌ Endpoint failed: {e}")
                    continue
            
            # Comment out fallback for testing ONLY Helius Sender
            logger.error(f"❌ All Helius Sender endpoints failed, no fallback used")
            return {
                "error": "All Helius Sender endpoints failed",
                "success": False
            }
                
        except Exception as e:
            logger.error(f"❌ Helius Sender error: {e}")
            return {"error": str(e), "success": False}
