import logging
from typing import Dict, Any, List, Optional
from solders.transaction import VersionedTransaction
from solders.system_program import transfer, TransferParams
from solders.message import MessageV0
from solders.instruction import Instruction
from solders.signature import Signature
import base64
import os

# Solana imports
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.pubkey import Pubkey
from solders.system_program import CreateAccountWithSeedParams, create_account_with_seed
from spl.token.client import Token
from spl.token.instructions import (
    CloseAccountParams, InitializeAccountParams, close_account,
    create_associated_token_account, get_associated_token_address, initialize_account
)
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts

# Local imports
from model.raydium_unified import RaydiumUnified, PoolType
from model.jito_bundle_client import HeliusSenderClient
from model.solana_transaction_provider import SolanaTransactionProvider
from model.solana_token_provider import SolanaTokenProvider
from utils.pool_utils import DIRECTION

logger = logging.getLogger(__name__)

class RaydiumUnifiedJito(RaydiumUnified):
    """
    Unified Raydium trading class with Jito integration for MEV protection.
    
    Combines:
    - Automatic pool type detection (AMM V4 vs CPMM)
    - Helius Sender for reliable transaction delivery
    - Jito tips for MEV protection and priority execution
    """

    def __init__(self, solana_provider=None):
        """
        Initialize RaydiumUnifiedJito instance.
        
        Args:
            solana_provider: Optional custom Solana provider instance
        """
        super().__init__(solana_provider)
        
        # Initialize Jito and Helius components
        self.helius_client = HeliusSenderClient()
        self.transaction_provider = SolanaTransactionProvider(self._provider)
        self.token_provider = SolanaTokenProvider(self._provider)
        
        logger.info("Initialized RaydiumUnifiedJito with MEV protection and auto pool detection")

    def create_transaction_with_jito_tip(
        self, 
        instructions: List[Instruction], 
        tip_amount: int = 1000000
    ) -> VersionedTransaction:
        """
        Create a versioned transaction with Jito tip included for MEV protection.
        
        Args:
            instructions (List[Instruction]): Transaction instructions
            tip_amount (int): Tip amount in lamports (default: 0.001 SOL)
            
        Returns:
            VersionedTransaction: Transaction with bundled Jito tip
        """
        try:
            # Get random tip account for MEV protection
            tip_account = self.helius_client.get_random_tip_account()
            
            # Create tip instruction
            tip_instruction = transfer(
                TransferParams(
                    from_pubkey=self._payer.pubkey(),
                    to_pubkey=tip_account,
                    lamports=tip_amount
                )
            )
            
            logger.info(f"Adding Jito tip: {tip_amount} lamports to {tip_account}")
            
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
            logger.error(f"Error creating transaction with Jito tip: {e}")
            return None

    def create_buy_instructions(self, token_mint: str, sol_in: float = 0.01, slippage: int = 5) -> List[Instruction]:
        """
        Create buy instructions using parent class helper methods.
        
        Args:
            token_mint (str): Token mint address
            sol_in (float): Amount of SOL to spend
            slippage (int): Slippage tolerance (%)
            
        Returns:
            List[Instruction]: Buy instructions or None if failed
        """
        try:
            logger.info(f"Creating buy instructions for {sol_in} SOL with {slippage}% slippage")
            
            # Auto-detect pool type and get pair address using parent method
            pool_type, pair_address = self.detect_pool_type_and_address(token_mint)
            if not pool_type or not pair_address:
                logger.error(f"No compatible pool found for token {token_mint}")
                return None
            
            logger.info(f"Detected {pool_type.value} pool: {pair_address}")
            
            # Get pool keys using parent method
            pool_keys = self.get_pool_keys(pool_type, pair_address)
            if not pool_keys:
                logger.error("Failed to fetch pool keys")
                return None
            
            # Get target mint using parent method
            mint = self.get_target_mint(pool_type, pool_keys)
            
            # Calculate amounts using parent method
            amount_in = int(sol_in * self._sol_decimal)
            base_reserve, quote_reserve, token_decimal = self.get_reserves_and_decimals(pool_type, pool_keys)
            amount_out = self.sol_for_tokens(sol_in, base_reserve, quote_reserve)
            minimum_amount_out = self.calculate_minimum_amount_out(amount_out, slippage, token_decimal)
            
            logger.info(f"Input: {amount_in} lamports, Minimum output: {minimum_amount_out} tokens")
            
            # Check for existing token account
            token_account_check = self._client.get_token_accounts_by_owner(
                self._payer.pubkey(), TokenAccountOpts(mint), Processed
            )
            if token_account_check.value:
                token_account = token_account_check.value[0].pubkey
                create_token_account_instruction = None
                logger.debug(f"Found existing token account: {token_account}")
            else:
                token_account = get_associated_token_address(self._payer.pubkey(), mint)
                create_token_account_instruction = create_associated_token_account(
                    self._payer.pubkey(), self._payer.pubkey(), mint
                )
                logger.info(f"Creating new associated token account: {token_account}")
            
            # Create WSOL account
            seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
            wsol_token_account = Pubkey.create_with_seed(
                self._payer.pubkey(), seed, self._token_program_id
            )
            balance_needed = Token.get_min_balance_rent_for_exempt_for_account(self._client)
            
            create_wsol_account_instruction = create_account_with_seed(
                CreateAccountWithSeedParams(
                    from_pubkey=self._payer.pubkey(),
                    to_pubkey=wsol_token_account,
                    base=self._payer.pubkey(),
                    seed=seed,
                    lamports=int(balance_needed + amount_in),
                    space=self._account_layout_len,
                    owner=self._token_program_id,
                )
            )
            
            init_wsol_account_instruction = initialize_account(
                InitializeAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    mint=self._wsol,
                    owner=self._payer.pubkey(),
                )
            )
            
            # Create swap instruction using parent method
            swap_instruction = self.make_swap_instruction(
                pool_type=pool_type,
                pool_keys=pool_keys,
                amount_in=amount_in,
                minimum_amount_out=minimum_amount_out,
                token_account_in=wsol_token_account,
                token_account_out=token_account,
                action=DIRECTION.BUY if pool_type == PoolType.CPMM else None
            )
            
            close_wsol_account_instruction = close_account(
                CloseAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    dest=self._payer.pubkey(),
                    owner=self._payer.pubkey(),
                )
            )
            
            # Build instructions list
            instructions = [
                set_compute_unit_limit(self._unit_budget),
                set_compute_unit_price(self._unit_price),
                create_wsol_account_instruction,
                init_wsol_account_instruction,
            ]
            
            if create_token_account_instruction:
                instructions.append(create_token_account_instruction)
            
            instructions.append(swap_instruction)
            instructions.append(close_wsol_account_instruction)
            
            return instructions
            
        except Exception as e:
            logger.error(f"Error creating buy instructions: {e}")
            return None

    def create_sell_instructions(self, token_mint: str, percentage: int = 100, slippage: int = 5) -> List[Instruction]:
        """
        Create sell instructions using parent class helper methods.
        
        Args:
            token_mint (str): Token mint address
            percentage (int): Percentage of tokens to sell (1-100)
            slippage (int): Slippage tolerance (%)
            
        Returns:
            List[Instruction]: Sell instructions or None if failed
        """
        try:
            logger.info(f"Creating sell instructions for {percentage}% with {slippage}% slippage")
            
            if not (1 <= percentage <= 100):
                logger.error(f"Invalid percentage value: {percentage}. Must be between 1 and 100")
                return None
            
            # Auto-detect pool type and get pair address using parent method
            pool_type, pair_address = self.detect_pool_type_and_address(token_mint)
            if not pool_type or not pair_address:
                logger.error(f"No compatible pool found for token {token_mint}")
                return None
            
            logger.info(f"Detected {pool_type.value} pool: {pair_address}")
            
            # Get pool keys using parent method
            pool_keys = self.get_pool_keys(pool_type, pair_address)
            if not pool_keys:
                logger.error("Failed to fetch pool keys")
                return None
            
            # Get target mint using parent method
            mint = self.get_target_mint(pool_type, pool_keys)
            
            # Get token balance using token provider
            token_balance = self.token_provider.get_token_balance(mint)
            if token_balance == 0 or token_balance is None:
                logger.error("Insufficient token balance for sell transaction")
                return None
            
            token_balance = token_balance * (percentage / 100)
            logger.info(f"Adjusted token balance for {percentage}% sell: {token_balance}")
            
            # Calculate amounts using parent method
            base_reserve, quote_reserve, token_decimal = self.get_reserves_and_decimals(pool_type, pool_keys)
            amount_out = self.tokens_for_sol(token_balance, base_reserve, quote_reserve)
            minimum_amount_out = self.calculate_minimum_amount_out(amount_out, slippage, self._sol_decimal)
            amount_in = int(token_balance * 10**token_decimal)
            
            logger.info(f"Input: {amount_in} tokens, Minimum output: {minimum_amount_out} lamports")
            
            token_account = get_associated_token_address(self._payer.pubkey(), mint)
            
            # Create WSOL account
            seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
            wsol_token_account = Pubkey.create_with_seed(
                self._payer.pubkey(), seed, self._token_program_id
            )
            balance_needed = Token.get_min_balance_rent_for_exempt_for_account(self._client)
            
            create_wsol_account_instruction = create_account_with_seed(
                CreateAccountWithSeedParams(
                    from_pubkey=self._payer.pubkey(),
                    to_pubkey=wsol_token_account,
                    base=self._payer.pubkey(),
                    seed=seed,
                    lamports=int(balance_needed),
                    space=self._account_layout_len,
                    owner=self._token_program_id,
                )
            )
            
            init_wsol_account_instruction = initialize_account(
                InitializeAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    mint=self._wsol,
                    owner=self._payer.pubkey(),
                )
            )
            
            # Create swap instruction using parent method
            swap_instruction = self.make_swap_instruction(
                pool_type=pool_type,
                pool_keys=pool_keys,
                amount_in=amount_in,
                minimum_amount_out=minimum_amount_out,
                token_account_in=token_account,
                token_account_out=wsol_token_account,
                action=DIRECTION.SELL if pool_type == PoolType.CPMM else None
            )
            
            close_wsol_account_instruction = close_account(
                CloseAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    dest=self._payer.pubkey(),
                    owner=self._payer.pubkey(),
                )
            )
            
            # Build instructions list
            instructions = [
                set_compute_unit_limit(self._unit_budget),
                set_compute_unit_price(self._unit_price),
                create_wsol_account_instruction,
                init_wsol_account_instruction,
                swap_instruction,
                close_wsol_account_instruction,
            ]
            
            # Close token account if selling 100%
            if percentage == 100:
                close_token_account_instruction = close_account(
                    CloseAccountParams(
                        program_id=self._token_program_id,
                        account=token_account,
                        dest=self._payer.pubkey(),
                        owner=self._payer.pubkey(),
                    )
                )
                instructions.append(close_token_account_instruction)
            
            return instructions
            
        except Exception as e:
            logger.error(f"Error creating sell instructions: {e}")
            return None

    def _process_jito_transaction_result(
        self, 
        result: Dict[str, Any], 
        token_mint_address: str, 
        tip_amount: int,
        operation_type: str = "transaction",
        initial_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Process Jito transaction result with confirmation and balance checking.
        
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
                    "method": "unified_helius_sender_bundled_with_jito_tips",
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
                    "method": "unified_helius_sender_bundled"
                }
        else:
            logger.error(f"❌ Bundled {operation_type} transaction failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "method": "unified_helius_sender_bundled"
            }

    def buy_with_jito(
        self,
        token_mint: str,
        sol_in: float = 0.01,
        slippage: int = 5,
        tip_amount: int = 1000000
    ) -> Dict[str, Any]:
        """
        Buy tokens with automatic pool detection and Jito MEV protection.
        
        Args:
            token_mint (str): Token mint address
            sol_in (float): Amount of SOL to spend
            slippage (int): Slippage tolerance (%)
            tip_amount (int): Tip amount in lamports for priority (default: 0.001 SOL)
            
        Returns:
            Dict[str, Any]: Transaction result with confirmation and balance info
        """
        try:
            logger.info(f"🚀 Unified buy with Jito MEV protection: {sol_in} SOL (tip: {tip_amount} lamports)")
            
            # Get buy instructions using helper method
            buy_instructions = self.create_buy_instructions(token_mint, sol_in, slippage)
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
                transaction=bundled_transaction
            )
            
            # Process result using shared method
            return self._process_jito_transaction_result(
                result=result,
                token_mint_address=token_mint,
                tip_amount=tip_amount,
                operation_type="buy"
            )
                
        except Exception as e:
            logger.error(f"Error in buy_with_jito: {e}")
            return {"success": False, "error": str(e)}

    def sell_with_jito(
        self,
        token_mint: str,
        percentage: int = 100,
        slippage: int = 5,
        tip_amount: int = 1000000
    ) -> Dict[str, Any]:
        """
        Sell tokens with automatic pool detection and Jito MEV protection.
        
        Args:
            token_mint (str): Token mint address
            percentage (int): Percentage of tokens to sell (1-100)
            slippage (int): Slippage tolerance (%)
            tip_amount (int): Tip amount in lamports for priority (default: 0.001 SOL)
            
        Returns:
            Dict[str, Any]: Transaction result with confirmation and balance info
        """
        try:
            logger.info(f"🚀 Unified sell with Jito MEV protection: {percentage}% (tip: {tip_amount} lamports)")
            
            # Check initial token balance using token provider
            initial_balance = self.token_provider.get_token_balance(token_mint)
            if not initial_balance or initial_balance <= 0:
                logger.error(f"❌ Insufficient token balance: {initial_balance}")
                return {"success": False, "error": f"Insufficient token balance: {initial_balance}"}
            
            logger.info(f"📊 Initial token balance: {initial_balance}")
            
            # Get sell instructions using helper method
            sell_instructions = self.create_sell_instructions(token_mint, percentage, slippage)
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
                transaction=bundled_transaction
            )
            
            # Process result using shared method
            return self._process_jito_transaction_result(
                result=result,
                token_mint_address=token_mint,
                tip_amount=tip_amount,
                operation_type="sell",
                initial_balance=initial_balance
            )
                
        except Exception as e:
            logger.error(f"Error in sell_with_jito: {e}")
            return {"success": False, "error": str(e)} 