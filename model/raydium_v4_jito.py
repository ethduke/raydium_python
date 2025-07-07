from model.raydium_v4 import RaydiumV4
from model.jito_bundle_client import HeliusSenderClient
from model.solana_transaction_provider import SolanaTransactionProvider
from model.solana_token_provider import SolanaTokenProvider
from typing import Dict, Any, List, Optional
from solders.transaction import VersionedTransaction
from solders.system_program import transfer, TransferParams
from solders.message import MessageV0
from solders.instruction import Instruction
from solders.signature import Signature
import logging

logger = logging.getLogger(__name__)

class HeliusEnhancedRaydiumV4(RaydiumV4):
    """Enhanced Raydium client with Helius Sender and Jito tips (following JavaScript example)"""
    
    def __init__(self):
        super().__init__()
        self.helius_client = HeliusSenderClient()
        self.transaction_provider = SolanaTransactionProvider(self._provider)
        self.token_provider = SolanaTokenProvider(self._provider)
        logger.info("Initialized HeliusEnhancedRaydiumV4 with provider services")
        
    def create_transaction_with_jito_tip(self, instructions: List[Instruction], tip_amount: int = 1000000) -> VersionedTransaction:
        """Create a versioned transaction with Jito tip included (like JavaScript example)"""
        try:
            # Get random tip account
            tip_account = self.helius_client.get_random_tip_account()
            
            # Create tip instruction
            tip_instruction = transfer(
                TransferParams(
                    from_pubkey=self._payer.pubkey(),
                    to_pubkey=tip_account,
                    lamports=tip_amount
                )
            )
            
            print(f"   Adding Jito tip: {tip_amount} lamports to {tip_account}")
            
            # Combine all instructions (compute budget + swap + tip)
            all_instructions = instructions + [tip_instruction]
            
            # Get latest blockhash
            latest_blockhash_response = self.helius_client.client.get_latest_blockhash()
            latest_blockhash = latest_blockhash_response.value.blockhash
            
            # Compile the message using MessageV0
            compiled_message = MessageV0.try_compile(
                payer=self._payer.pubkey(),
                instructions=all_instructions,
                address_lookup_table_accounts=[],
                recent_blockhash=latest_blockhash,
            )
            
            # Create and sign versioned transaction
            versioned_transaction = VersionedTransaction(compiled_message, [self._payer])
            return versioned_transaction
            
        except Exception as e:
            print(f"Error creating transaction with Jito tip: {e}")
            return None

    def _process_transaction_result(
        self, 
        result: Dict[str, Any], 
        token_mint_address: str, 
        tip_amount: int,
        operation_type: str = "transaction",
        initial_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Process transaction result with confirmation and balance checking.
        
        Args:
            result: Result from Helius sender
            token_mint_address: Token mint address for balance checking
            tip_amount: Tip amount in lamports
            operation_type: Type of operation ("buy", "sell", "transaction")
            initial_balance: Initial balance for sell operations
            
        Returns:
            Dict[str, Any]: Processed result with confirmation and balance info
        """
        if result.get("success"):
            signature = result["signature"]
            logger.info(f"✅ Bundled {operation_type} transaction sent successfully! Signature: {signature}")
            
            # Confirm transaction using SolanaTransactionProvider
            logger.info("🔄 Confirming transaction...")
            signature_obj = Signature.from_string(signature)
            confirmed = self.transaction_provider.confirm_transaction(signature_obj)
            
            if confirmed:
                logger.info(f"✅ Transaction confirmed successfully!")
                
                # Check final token balance using SolanaTokenProvider
                try:
                    final_balance = self.token_provider.get_token_balance(token_mint_address)
                    logger.info(f"📊 Final token balance: {final_balance}")
                except Exception as e:
                    logger.warning(f"Could not fetch final balance: {e}")
                    final_balance = None
                
                success_result = {
                    "success": True,
                    "signature": signature,
                    "method": "helius_sender_bundled_with_jito_tips",
                    "tip_amount": tip_amount,
                    "confirmed": True,
                    "final_balance": final_balance
                }
                
                # Add initial balance for sell operations
                if initial_balance is not None:
                    success_result["initial_balance"] = initial_balance
                
                return success_result
            else:
                logger.error(f"❌ Transaction failed to confirm")
                return {
                    "success": False,
                    "error": "Transaction sent but failed to confirm",
                    "signature": signature,
                    "method": "helius_sender_bundled"
                }
        else:
            logger.error(f"❌ Bundled {operation_type} transaction failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "method": "helius_sender_bundled"
            }

    def buy_with_helius_sender(self,
                              token_mint_address: str,
                              sol_in: float,
                              slippage: int = 5,
                              tip_amount: int = 1000000) -> Dict[str, Any]:
        """
        Buy tokens using Helius Sender with bundled Jito tip (following JavaScript example)
        
        Args:
            token_mint_address: Token mint address
            sol_in: Amount of SOL to spend
            slippage: Slippage tolerance (%)
            tip_amount: Tip amount in lamports for priority (default: 0.001 SOL)
        """
        try:
            logger.info(f"🚀 Buying with bundled Helius Sender + Jito tip: {sol_in} SOL (tip: {tip_amount} lamports)")
            
            # Get pair address
            pair_address = self.get_pair_address(token_mint_address)
            logger.info(f"Creating buy instructions for pair: {pair_address}")
            
            # Get buy instructions from the modified create_buy_transaction method
            buy_instructions = self.create_buy_transaction(pair_address, sol_in, slippage)
            if not buy_instructions:
                return {"success": False, "error": "Failed to create buy instructions"}
            
            logger.info(f"Created {len(buy_instructions)} buy instructions")
            
            # Create bundled transaction with Jito tip 
            bundled_transaction = self.create_transaction_with_jito_tip(buy_instructions, tip_amount)
            if not bundled_transaction:
                return {"success": False, "error": "Failed to create bundled transaction"}
            
            # Send the bundled transaction via Helius Sender
            logger.info("📤 Sending bundled transaction...")
            result = self.helius_client.send_with_jito_tips(
                transaction=bundled_transaction,
                payer=self._payer
            )
            
            # Process result using shared method
            return self._process_transaction_result(
                result=result,
                token_mint_address=token_mint_address,
                tip_amount=tip_amount,
                operation_type="buy"
            )
                
        except Exception as e:
            logger.error(f"Error in buy_with_helius_sender: {e}")
            return {"success": False, "error": str(e)}
    
    def sell_with_helius_sender(self,
                               token_mint_address: str,
                               percentage: int,
                               slippage: int = 5,
                               tip_amount: int = 1000000) -> Dict[str, Any]:
        """
        Sell tokens using Helius Sender with bundled Jito tip (following JavaScript example)
        
        Args:
            token_mint_address: Token mint address
            percentage: Percentage of tokens to sell
            slippage: Slippage tolerance (%)
            tip_amount: Tip amount in lamports for priority (default: 0.001 SOL)
        """
        try:
            logger.info(f"🚀 Selling with bundled Helius Sender + Jito tip: {percentage}% (tip: {tip_amount} lamports)")
            
            # Check initial token balance using SolanaTokenProvider
            initial_balance = self.token_provider.get_token_balance(token_mint_address)
            if not initial_balance or initial_balance <= 0:
                logger.error(f"❌ Insufficient token balance: {initial_balance}")
                return {"success": False, "error": f"Insufficient token balance: {initial_balance}"}
            
            logger.info(f"📊 Initial token balance: {initial_balance}")
            
            # Get pair address
            pair_address = self.get_pair_address(token_mint_address)
            logger.info(f"Creating sell instructions for pair: {pair_address}")
            
            # Get sell instructions from the modified create_sell_transaction method
            sell_instructions = self.create_sell_transaction(pair_address, percentage, slippage)
            if not sell_instructions:
                return {"success": False, "error": "Failed to create sell instructions"}
            
            logger.info(f"Created {len(sell_instructions)} sell instructions")
            
            # Create bundled transaction with Jito tip 
            bundled_transaction = self.create_transaction_with_jito_tip(sell_instructions, tip_amount)
            if not bundled_transaction:
                return {"success": False, "error": "Failed to create bundled transaction"}
            
            # Send the bundled transaction via Helius Sender
            logger.info("📤 Sending bundled transaction...")
            result = self.helius_client.send_with_jito_tips(
                transaction=bundled_transaction,
                payer=self._payer
            )
            
            # Process result using shared method
            return self._process_transaction_result(
                result=result,
                token_mint_address=token_mint_address,
                tip_amount=tip_amount,
                operation_type="sell",
                initial_balance=initial_balance
            )
                
        except Exception as e:
            logger.error(f"Error in sell_with_helius_sender: {e}")
            return {"success": False, "error": str(e)}
