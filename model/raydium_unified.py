import base64
import os
import logging
from typing import Optional, List, Union, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Raydium Unified] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Solana imports
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.instruction import Instruction
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)
from solders.transaction import VersionedTransaction

# SPL Token imports
from spl.token.client import Token
from spl.token.instructions import (
    CloseAccountParams,
    InitializeAccountParams,
    close_account,
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
)

# Local imports
from model.solana_provider import SolanaProvider
from model.solana_transaction_provider import SolanaTransactionProvider
from model.solana_token_provider import SolanaTokenProvider
from utils.pool_utils import (
    AmmV4PoolKeys,
    CpmmPoolKeys,
    DIRECTION,
    fetch_amm_v4_pool_keys,
    fetch_cpmm_pool_keys,
    get_amm_v4_reserves,
    get_cpmm_reserves,
    make_amm_v4_swap_instruction,
    make_cpmm_swap_instruction,
    get_amm_v4_pair_from_rpc,
    get_cpmm_pair_address_from_rpc,
)
from config import config


class PoolType(Enum):
    """Pool type enumeration"""
    AMM_V4 = "amm_v4"
    CPMM = "cpmm"


class RaydiumUnified:
    """
    Unified Raydium trading class that auto-detects pool types and provides
    a single interface for both AMM V4 and CPMM pools.
    """

    def __init__(self, solana_provider: Optional[SolanaProvider] = None):
        """
        Initialize RaydiumUnified instance.
        
        Args:
            solana_provider (Optional[SolanaProvider]): Custom Solana provider instance.
                                                      If None, uses default provider.
        """
        # Initialize providers
        self._provider = solana_provider or SolanaProvider.get_instance()
        self._client = self._provider.rpc
        self._payer = self._provider.payer
        
        # Initialize service providers
        self._transaction_provider = SolanaTransactionProvider(self._provider)
        self._token_provider = SolanaTokenProvider(self._provider)

        # Constants from config
        self._wsol = config.WSOL
        self._sol_decimal = config.SOL_DECIMAL
        self._account_layout_len = config.ACCOUNT_LAYOUT_LEN
        self._token_program_id = config.TOKEN_PROGRAM_ID
        self._unit_budget = config.get_unit_budget()
        self._unit_price = config.get_unit_price()
        
        logger.info(f"Initialized RaydiumUnified with payer: {self._payer.pubkey()}")

    def detect_pool_type_and_address(self, token_mint: str) -> Tuple[Optional[PoolType], Optional[str]]:
        """
        Auto-detect pool type and get pair address for a given token mint.
        
        Args:
            token_mint (str): Token mint address to find pools for
            
        Returns:
            Tuple[Optional[PoolType], Optional[str]]: Pool type and pair address, or (None, None) if not found
        """
        logger.info(f"Auto-detecting pool type for token mint: {token_mint}")
        
        # Try AMM V4 first
        try:
            v4_pairs = get_amm_v4_pair_from_rpc(token_mint)
            if v4_pairs and len(v4_pairs) > 0:
                pair_address = v4_pairs[0]
                logger.info(f"Found AMM V4 pool: {pair_address}")
                return PoolType.AMM_V4, pair_address
        except Exception as e:
            logger.debug(f"AMM V4 lookup failed: {e}")

        # Try CPMM
        try:
            cpmm_pairs = get_cpmm_pair_address_from_rpc(token_mint)
            if cpmm_pairs and len(cpmm_pairs) > 0:
                pair_address = cpmm_pairs[0]
                logger.info(f"Found CPMM pool: {pair_address}")
                return PoolType.CPMM, pair_address
        except Exception as e:
            logger.debug(f"CPMM lookup failed: {e}")

        logger.error(f"No compatible pools found for token mint: {token_mint}")
        return None, None

    def get_pool_keys(self, pool_type: PoolType, pair_address: str) -> Union[AmmV4PoolKeys, CpmmPoolKeys, None]:
        """
        Get pool keys based on pool type.
        
        Args:
            pool_type (PoolType): Type of pool
            pair_address (str): Pool pair address
            
        Returns:
            Union[AmmV4PoolKeys, CpmmPoolKeys, None]: Pool keys or None if failed
        """
        try:
            if pool_type == PoolType.AMM_V4:
                return fetch_amm_v4_pool_keys(pair_address)
            elif pool_type == PoolType.CPMM:
                return fetch_cpmm_pool_keys(pair_address)
            else:
                logger.error(f"Unsupported pool type: {pool_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to fetch pool keys for {pool_type.value}: {e}")
            return None

    def get_reserves_and_decimals(self, pool_type: PoolType, pool_keys: Union[AmmV4PoolKeys, CpmmPoolKeys]) -> Tuple[float, float, int]:
        """
        Get reserves and token decimals based on pool type.
        
        Args:
            pool_type (PoolType): Type of pool
            pool_keys: Pool keys (either AmmV4PoolKeys or CpmmPoolKeys)
            
        Returns:
            Tuple[float, float, int]: base_reserve, quote_reserve, token_decimal
        """
        try:
            if pool_type == PoolType.AMM_V4:
                return get_amm_v4_reserves(pool_keys)
            elif pool_type == PoolType.CPMM:
                return get_cpmm_reserves(pool_keys)
            else:
                logger.error(f"Unsupported pool type: {pool_type}")
                return None, None, None
        except Exception as e:
            logger.error(f"Failed to get reserves for {pool_type.value}: {e}")
            return None, None, None

    def make_swap_instruction(
        self,
        pool_type: PoolType,
        pool_keys: Union[AmmV4PoolKeys, CpmmPoolKeys],
        amount_in: int,
        minimum_amount_out: int,
        token_account_in: Pubkey,
        token_account_out: Pubkey,
        action: DIRECTION = None
    ) -> Instruction:
        """
        Create swap instruction based on pool type.
        
        Args:
            pool_type (PoolType): Type of pool
            pool_keys: Pool keys
            amount_in (int): Input amount
            minimum_amount_out (int): Minimum output amount
            token_account_in (Pubkey): Input token account
            token_account_out (Pubkey): Output token account
            action (DIRECTION): Buy or sell direction (required for CPMM)
            
        Returns:
            Instruction: Swap instruction
        """
        try:
            if pool_type == PoolType.AMM_V4:
                return make_amm_v4_swap_instruction(
                    amount_in=amount_in,
                    minimum_amount_out=minimum_amount_out,
                    token_account_in=token_account_in,
                    token_account_out=token_account_out,
                    accounts=pool_keys,
                    owner=self._payer.pubkey(),
                )
            elif pool_type == PoolType.CPMM:
                if action is None:
                    raise ValueError("Action (DIRECTION) is required for CPMM swaps")
                return make_cpmm_swap_instruction(
                    amount_in=amount_in,
                    minimum_amount_out=minimum_amount_out,
                    token_account_in=token_account_in,
                    token_account_out=token_account_out,
                    accounts=pool_keys,
                    owner=self._payer.pubkey(),
                    action=action,
                )
            else:
                logger.error(f"Unsupported pool type: {pool_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to create swap instruction for {pool_type.value}: {e}")
            return None

    def get_target_mint(self, pool_type: PoolType, pool_keys: Union[AmmV4PoolKeys, CpmmPoolKeys]) -> Pubkey:
        """
        Get the target mint address (non-WSOL mint) from pool keys.
        
        Args:
            pool_type (PoolType): Type of pool
            pool_keys: Pool keys
            
        Returns:
            Pubkey: Target mint address
        """
        if pool_type == PoolType.AMM_V4:
            return pool_keys.base_mint if pool_keys.base_mint != self._wsol else pool_keys.quote_mint
        elif pool_type == PoolType.CPMM:
            return pool_keys.token_1_mint if pool_keys.token_0_mint == self._wsol else pool_keys.token_0_mint

    @staticmethod
    def calculate_minimum_amount_out(amount_out: float, slippage: int, decimal: int) -> int:
        """
        Calculate minimum amount out with slippage adjustment.
        
        Args:
            amount_out (float): The estimated output amount
            slippage (int): Slippage percentage
            decimal (int): Decimal places for the output amount (or the decimal multiplier itself)
        
        Returns:
            int: Minimum amount out with slippage adjustment
        """
        logger.info(f"Calculating minimum amount out with slippage {slippage}%")
        
        slippage_adjustment = 1 - (slippage / 100)
        amount_out_with_slippage = amount_out * slippage_adjustment
        
        # Handle both decimal places (e.g., 9) and multipliers (e.g., 1000000000)
        if decimal > 100:  # It's a multiplier
            result = int(amount_out_with_slippage * decimal)
        else:  # It's decimal places
            result = int(amount_out_with_slippage * (10 ** decimal))
        
        logger.info(f"Final minimum amount out: {result}")
        return result

    @staticmethod
    def sol_for_tokens(sol_amount: float, base_vault_balance: float, quote_vault_balance: float, swap_fee: float = 0.25) -> float:
        """
        Calculate the number of tokens received for a given SOL amount.
        
        Args:
            sol_amount (float): Amount of SOL to swap
            base_vault_balance (float): Current base vault balance
            quote_vault_balance (float): Current quote vault balance
            swap_fee (float): Swap fee percentage
            
        Returns:
            float: Expected amount of tokens to receive
        """
        effective_sol_used = sol_amount - (sol_amount * (swap_fee / 100))
        constant_product = base_vault_balance * quote_vault_balance
        updated_base_vault_balance = constant_product / (quote_vault_balance + effective_sol_used)
        tokens_received = base_vault_balance - updated_base_vault_balance
        return round(tokens_received, 9)

    @staticmethod
    def tokens_for_sol(token_amount: float, base_vault_balance: float, quote_vault_balance: float, swap_fee: float = 0.25) -> float:
        """
        Calculate the amount of SOL received for a given token amount.
        
        Args:
            token_amount (float): Amount of tokens to swap
            base_vault_balance (float): Current base vault balance
            quote_vault_balance (float): Current quote vault balance
            swap_fee (float): Swap fee percentage
            
        Returns:
            float: Expected amount of SOL to receive
        """
        effective_tokens_sold = token_amount * (1 - (swap_fee / 100))
        constant_product = base_vault_balance * quote_vault_balance
        updated_quote_vault_balance = constant_product / (base_vault_balance + effective_tokens_sold)
        sol_received = quote_vault_balance - updated_quote_vault_balance
        return round(sol_received, 9)

    def create_versioned_swap_transaction(self, instructions: List[Instruction]) -> VersionedTransaction:
        """
        Create a versioned transaction for a swap operation.
        
        Args:
            instructions (List[Instruction]): List of instructions to include in the transaction
        """
        try:
            logger.info("Compiling transaction message")
            compiled_message = MessageV0.try_compile(
                self._payer.pubkey(),
                instructions,
                [],
                self._client.get_latest_blockhash().value.blockhash,
            )
            return VersionedTransaction(compiled_message, [self._payer])
        except Exception as e:
            logger.error(f"Error occurred during transaction creation: {str(e)}", exc_info=True)
            return None

    def execute_versioned_transaction(self, versioned_transaction: VersionedTransaction) -> bool:
        """
        Execute a versioned transaction.
        
        Args:
            versioned_transaction (VersionedTransaction): The versioned transaction to execute
            
        Returns:
            bool: True if transaction successful, False otherwise
        """
        try:
            if not versioned_transaction:
                logger.error("No transaction provided for execution")
                return False
                
            logger.info("Sending versioned transaction")
            txn_sig = self._client.send_transaction(
                txn=versioned_transaction,
                opts=TxOpts(skip_preflight=True),
            ).value
            logger.info(f"Transaction Signature: {txn_sig}")

            logger.info("Confirming transaction using SolanaTransactionProvider")
            confirmed = self._transaction_provider.confirm_transaction(txn_sig)
            logger.info(f"Transaction confirmed: {confirmed}")
            return confirmed
        except Exception as e:
            logger.error(f"Error executing versioned transaction: {e}")
            return False

    def buy_by_token(self, token_mint: str, sol_in: float = 0.01, slippage: int = 5) -> bool:
        """
        Buy tokens using SOL by providing just the token mint address.
        Auto-detects pool type and executes appropriate swap.
        
        Args:
            token_mint (str): Mint address of the token to buy
            sol_in (float): Amount of SOL to spend
            slippage (int): Maximum acceptable slippage percentage
            
        Returns:
            bool: True if transaction successful, False otherwise
        """
        try:
            logger.info(f"Initiating unified buy for token {token_mint} with {sol_in} SOL and {slippage}% slippage")

            # Auto-detect pool type and get pair address
            pool_type, pair_address = self.detect_pool_type_and_address(token_mint)
            if not pool_type or not pair_address:
                logger.error(f"No compatible pool found for token {token_mint}")
                return False

            # Get pool keys
            pool_keys = self.get_pool_keys(pool_type, pair_address)
            if not pool_keys:
                logger.error(f"Failed to fetch pool keys for {pool_type.value}")
                return False

            # Get target mint address
            mint = self.get_target_mint(pool_type, pool_keys)
            logger.debug(f"Using mint address: {mint}")

            # Calculate amounts
            amount_in = int(sol_in * self._sol_decimal)
            base_reserve, quote_reserve, token_decimal = self.get_reserves_and_decimals(pool_type, pool_keys)
            
            if base_reserve is None or quote_reserve is None or token_decimal is None:
                logger.error("Failed to get reserves and decimals")
                return False

            amount_out = self.sol_for_tokens(sol_in, base_reserve, quote_reserve)
            minimum_amount_out = self.calculate_minimum_amount_out(amount_out, slippage, token_decimal)
            
            logger.info(f"Transaction parameters - Input: {amount_in} lamports, Minimum output: {minimum_amount_out} tokens")

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

            # Create temporary WSOL account
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

            # Create swap instruction
            swap_instruction = self.make_swap_instruction(
                pool_type=pool_type,
                pool_keys=pool_keys,
                amount_in=amount_in,
                minimum_amount_out=minimum_amount_out,
                token_account_in=wsol_token_account,
                token_account_out=token_account,
                action=DIRECTION.BUY if pool_type == PoolType.CPMM else None
            )

            if not swap_instruction:
                logger.error("Failed to create swap instruction")
                return False

            # Close WSOL account instruction
            close_wsol_account_instruction = close_account(
                CloseAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    dest=self._payer.pubkey(),
                    owner=self._payer.pubkey(),
                )
            )

            # Build instruction list
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

            # Execute transaction
            versioned_transaction = self.create_versioned_swap_transaction(instructions)
            return self.execute_versioned_transaction(versioned_transaction)

        except Exception as e:
            logger.error(f"Error during buy transaction: {e}", exc_info=True)
            return False

    def sell_by_token(self, token_mint: str, percentage: int = 100, slippage: int = 5) -> bool:
        """
        Sell tokens for SOL by providing just the token mint address.
        Auto-detects pool type and executes appropriate swap.
        
        Args:
            token_mint (str): Mint address of the token to sell
            percentage (int): Percentage of tokens to sell (1-100)
            slippage (int): Maximum acceptable slippage percentage
            
        Returns:
            bool: True if transaction successful, False otherwise
        """
        try:
            logger.info(f"Initiating unified sell for token {token_mint} - {percentage}% with {slippage}% slippage")

            if not (1 <= percentage <= 100):
                logger.error(f"Invalid percentage value: {percentage}. Must be between 1 and 100")
                return False

            # Auto-detect pool type and get pair address
            pool_type, pair_address = self.detect_pool_type_and_address(token_mint)
            if not pool_type or not pair_address:
                logger.error(f"No compatible pool found for token {token_mint}")
                return False

            # Get pool keys
            pool_keys = self.get_pool_keys(pool_type, pair_address)
            if not pool_keys:
                logger.error(f"Failed to fetch pool keys for {pool_type.value}")
                return False

            # Get target mint address
            mint = self.get_target_mint(pool_type, pool_keys)
            logger.debug(f"Using mint address: {mint}")

            # Get token balance
            token_balance = self._token_provider.get_token_balance(mint)
            logger.info(f"Current token balance: {token_balance}")

            if token_balance == 0 or token_balance is None:
                logger.error("Insufficient token balance for sell transaction")
                return False

            token_balance = token_balance * (percentage / 100)
            logger.info(f"Adjusted token balance for {percentage}% sell: {token_balance}")

            # Calculate amounts
            base_reserve, quote_reserve, token_decimal = self.get_reserves_and_decimals(pool_type, pool_keys)
            
            if base_reserve is None or quote_reserve is None or token_decimal is None:
                logger.error("Failed to get reserves and decimals")
                return False

            amount_out = self.tokens_for_sol(token_balance, base_reserve, quote_reserve)
            minimum_amount_out = self.calculate_minimum_amount_out(amount_out, slippage, self._sol_decimal)
            amount_in = int(token_balance * 10**token_decimal)
            
            logger.info(f"Transaction parameters - Input: {amount_in} tokens, Minimum output: {minimum_amount_out} lamports")

            # Get token account
            token_account = get_associated_token_address(self._payer.pubkey(), mint)

            # Create temporary WSOL account
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

            # Create swap instruction
            swap_instruction = self.make_swap_instruction(
                pool_type=pool_type,
                pool_keys=pool_keys,
                amount_in=amount_in,
                minimum_amount_out=minimum_amount_out,
                token_account_in=token_account,
                token_account_out=wsol_token_account,
                action=DIRECTION.SELL if pool_type == PoolType.CPMM else None
            )

            if not swap_instruction:
                logger.error("Failed to create swap instruction")
                return False

            # Close WSOL account instruction
            close_wsol_account_instruction = close_account(
                CloseAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    dest=self._payer.pubkey(),
                    owner=self._payer.pubkey(),
                )
            )

            # Build instruction list
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
                logger.info("Preparing to close token account after swap")
                close_token_account_instruction = close_account(
                    CloseAccountParams(
                        program_id=self._token_program_id,
                        account=token_account,
                        dest=self._payer.pubkey(),
                        owner=self._payer.pubkey(),
                    )
                )
                instructions.append(close_token_account_instruction)

            # Execute transaction
            versioned_transaction = self.create_versioned_swap_transaction(instructions)
            return self.execute_versioned_transaction(versioned_transaction)

        except Exception as e:
            logger.error(f"Error during sell transaction: {e}", exc_info=True)
            return False 