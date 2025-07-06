from model.raydium_v4 import RaydiumV4
from model.jito_bundle_client import JitoBundleClient
from solana.transaction import Transaction
from typing import Dict, Any
from solana.transaction import Transaction, VersionedTransaction
import base64
import time

class JitoEnhancedRaydiumV4(RaydiumV4):
    """Enhanced Raydium client with Jito bundle support"""
    
    def __init__(self, use_jito: bool = False):
        super().__init__()
        self.use_jito = use_jito
        self.jito_client = JitoBundleClient()
        
    
    def _serialize_transaction(self, transaction) -> str:
        """Serialize transaction for bundle submission (supports both Transaction and VersionedTransaction)"""
        try:
            
            if isinstance(transaction, VersionedTransaction):
                # Serialize versioned transaction
                serialized = transaction.serialize()
            elif isinstance(transaction, Transaction):
                # Serialize legacy transaction
                serialized = transaction.serialize()
            else:
                raise ValueError(f"Unsupported transaction type: {type(transaction)}")
            
            # Encode to base64
            encoded = base64.b64encode(serialized).decode('utf-8')
            return encoded
        except Exception as e:
            print(f"Transaction serialization error: {e}")
            return None
    
    def buy_with_jito(self, 
                     pair_address: str, 
                     sol_in: float, 
                     slippage: int = 5,
                     tip_amount: int = 10000,  # 0.00001 SOL tip
                     max_retries: int = 3) -> Dict[str, Any]:
        """
        Buy tokens with Jito bundle for priority execution using versioned transactions
        
        Args:
            pair_address: Raydium pair address
            sol_in: Amount of SOL to spend
            slippage: Slippage tolerance (%)
            tip_amount: Tip amount in lamports for priority
            max_retries: Maximum retry attempts
        """
        if not self.use_jito or not self.jito_client:
            print("Jito not enabled, using regular buy")
            return self.buy(pair_address, sol_in, slippage)
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"Creating buy transaction with Jito tip: {tip_amount} lamports")
            
            # Create the main swap transaction (versioned)
            swap_transaction = self._create_buy_transaction(pair_address, sol_in, slippage)
            
            # Create tip transaction (versioned)
            tip_transaction = self._create_tip_transaction_versioned(tip_amount)
            
            logger.info("Serializing transactions for bundle")
            
            # Serialize transactions
            swap_tx_serialized = self._serialize_transaction(swap_transaction)
            tip_tx_serialized = self._serialize_transaction(tip_transaction)
            
            if not swap_tx_serialized or not tip_tx_serialized:
                raise Exception("Failed to serialize transactions")
            
            logger.info("Submitting bundle to Jito")
            
            # Submit bundle
            bundle_transactions = [swap_tx_serialized, tip_tx_serialized]
            bundle_result = self.jito_client.send_bundle(bundle_transactions)
            
            if "error" in bundle_result:
                print(f"Bundle submission failed: {bundle_result['error']}")
                return {"success": False, "error": bundle_result['error']}
            
            bundle_id = bundle_result.get("result")
            logger.info(f"Bundle submitted with ID: {bundle_id}")
            
            # Monitor bundle status
            return self._monitor_bundle_execution(bundle_id, max_retries)
            
        except Exception as e:
            print(f"Jito buy error: {e}")
            return {"success": False, "error": str(e)}
    
    def sell_with_jito(self,
                      pair_address: str,
                      percentage: int,
                      slippage: int = 5,
                      tip_amount: int = 10000,
                      max_retries: int = 3) -> Dict[str, Any]:
        """
        Sell tokens with Jito bundle for priority execution
        
        Args:
            pair_address: Raydium pair address
            percentage: Percentage of tokens to sell
            slippage: Slippage tolerance (%)
            tip_amount: Tip amount in lamports for priority
            max_retries: Maximum retry attempts
        """
        if not self.use_jito or not self.jito_client:
            print("Jito not enabled, using regular sell")
            return self.sell(pair_address, percentage, slippage)
        
        try:
            # Create the main swap transaction (modify this based on your existing sell logic)
            swap_transaction = self._create_sell_transaction(pair_address, percentage, slippage)
            
            # Create tip transaction
            tip_transaction = self.jito_client.create_tip_transaction(
                payer=self.payer,
                tip_amount=tip_amount
            )
            
            # Get recent blockhash
            recent_blockhash = self.client.get_recent_blockhash()["result"]["value"]["blockhash"]
            
            # Sign transactions
            swap_transaction.recent_blockhash = recent_blockhash
            tip_transaction.recent_blockhash = recent_blockhash
            
            swap_transaction.sign(self.payer)
            tip_transaction.sign(self.payer)
            
            # Serialize transactions
            swap_tx_serialized = self._serialize_transaction(swap_transaction)
            tip_tx_serialized = self._serialize_transaction(tip_transaction)
            
            if not swap_tx_serialized or not tip_tx_serialized:
                raise Exception("Failed to serialize transactions")
            
            # Submit bundle
            bundle_transactions = [swap_tx_serialized, tip_tx_serialized]
            bundle_result = self.jito_client.send_bundle(bundle_transactions)
            
            if "error" in bundle_result:
                print(f"Bundle submission failed: {bundle_result['error']}")
                return {"success": False, "error": bundle_result['error']}
            
            bundle_id = bundle_result.get("result")
            print(f"Bundle submitted with ID: {bundle_id}")
            
            # Monitor bundle status
            return self._monitor_bundle_execution(bundle_id, max_retries)
            
        except Exception as e:
            print(f"Jito sell error: {e}")
            return {"success": False, "error": str(e)}

    
    def _monitor_bundle_execution(self, bundle_id: str, max_retries: int) -> Dict[str, Any]:
        """Monitor bundle execution status"""
        for attempt in range(max_retries):
            try:
                time.sleep(2)  # Wait before checking status
                status_result = self.jito_client.get_bundle_status(bundle_id)
                
                if "error" in status_result:
                    print(f"Bundle status check failed: {status_result['error']}")
                    continue
                
                bundle_statuses = status_result.get("result", {}).get("value", [])
                if bundle_statuses:
                    status = bundle_statuses[0]
                    if status.get("confirmation_status") == "confirmed":
                        print(f"Bundle {bundle_id} confirmed successfully!")
                        return {
                            "success": True,
                            "bundle_id": bundle_id,
                            "status": status,
                            "transactions": status.get("transactions", [])
                        }
                    elif status.get("err"):
                        print(f"Bundle {bundle_id} failed: {status.get('err')}")
                        return {
                            "success": False,
                            "bundle_id": bundle_id,
                            "error": status.get("err")
                        }
                
                print(f"Bundle {bundle_id} still processing... (attempt {attempt + 1}/{max_retries})")
                
            except Exception as e:
                print(f"Bundle monitoring error: {e}")
                continue
        
        return {
            "success": False,
            "bundle_id": bundle_id,
            "error": "Bundle execution timeout"
        }
    
    def _create_buy_transaction(self, pair_address: str, sol_in: float, slippage: int) -> Transaction:
        """Create buy transaction - implement this based on your existing buy logic"""
        # This should contain your existing buy transaction creation logic
        # You'll need to modify your existing buy() method to return a Transaction object
        # instead of immediately sending it
        pass
    
    def _create_sell_transaction(self, pair_address: str, percentage: int, slippage: int) -> Transaction:
        """Create sell transaction - implement this based on your existing sell logic"""
        # This should contain your existing sell transaction creation logic
        # You'll need to modify your existing sell() method to return a Transaction object
        # instead of immediately sending it
        pass
