import base64
import os
import logging
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Raydium V4] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Solana imports
from solana.rpc.commitment import Processed
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  # type: ignore
from solders.message import MessageV0  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solders.system_program import (
    CreateAccountWithSeedParams,
    create_account_with_seed,
)
from solders.transaction import VersionedTransaction  # type: ignore

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
from utils.common_utils import confirm_txn, get_token_balance
from utils.pool_utils import (
    AmmV4PoolKeys,
    fetch_amm_v4_pool_keys,
    get_amm_v4_reserves,
    make_amm_v4_swap_instruction,
    get_amm_v4_pair_from_rpc,
)
from config import config
from model.solana_provider import SolanaProvider
from model.raydium_api import RaydiumAPI


class RaydiumV4:
    """
    RaydiumV4 class for handling Raydium V4 AMM operations.
    Provides functionality for buying and selling tokens using Raydium V4 pools.
    """

    def __init__(self, solana_provider: Optional[SolanaProvider] = None):
        """
        Initialize RaydiumV4 instance.
        
        Args:
            solana_provider (Optional[SolanaProvider]): Custom Solana provider instance.
                                                      If None, uses default provider.
        """
        # Initialize providers
        self._provider = solana_provider or SolanaProvider.get_instance()
        self._client = self._provider.rpc
        self._payer = self._provider.payer
        self._api = RaydiumAPI()

        # Constants from config
        self._wsol = config.WSOL
        self._sol_decimal = config.SOL_DECIMAL
        self._account_layout_len = config.ACCOUNT_LAYOUT_LEN
        self._token_program_id = config.TOKEN_PROGRAM_ID
        self._unit_budget = config.get_unit_budget()
        self._unit_price = config.get_unit_price()

    @staticmethod
    def calculate_minimum_amount_out(amount_out: float, slippage: int, decimal: int) -> int:
        """
        Calculate minimum amount out with slippage adjustment.
        
        Args:
            amount_out (float): The estimated output amount
            slippage (int): Slippage percentage
            decimal (int): Decimal places for the output amount
        
        Returns:
            int: Minimum amount out with slippage adjustment
        """
        slippage_adjustment = 1 - (slippage / 100)
        amount_out_with_slippage = amount_out * slippage_adjustment
        return int(amount_out_with_slippage * 10**decimal)

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

    def buy(self, pair_address: str, sol_in: float = 0.01, slippage: int = 5) -> bool:
        """
        Buy tokens using SOL.
        
        Args:
            pair_address (str): Address of the trading pair
            sol_in (float): Amount of SOL to spend
            slippage (int): Maximum acceptable slippage percentage
            
        Returns:
            bool: True if transaction successful, False otherwise
        """
        try:
            logger.info(f"Initiating buy transaction for pair {pair_address} with {sol_in} SOL input and {slippage}% slippage")

            logger.info(f"Fetching AMM V4 pool keys for pair {pair_address}")
            pool_keys: Optional[AmmV4PoolKeys] = fetch_amm_v4_pool_keys(pair_address)
            if pool_keys is None:
                logger.error(f"Failed to fetch pool keys for pair {pair_address}")
                return False
            logger.debug("Successfully retrieved pool keys")

            mint = (
                pool_keys.base_mint if pool_keys.base_mint != self._wsol else pool_keys.quote_mint
            )
            logger.debug(f"Using mint address: {mint}")

            logger.info("Calculating swap amounts and reserves")
            amount_in = int(sol_in * self._sol_decimal)

            base_reserve, quote_reserve, token_decimal = get_amm_v4_reserves(pool_keys)
            amount_out = self.sol_for_tokens(sol_in, base_reserve, quote_reserve)
            logger.info(f"Estimated output amount: {amount_out} tokens (base_reserve: {base_reserve}, quote_reserve: {quote_reserve})")

            minimum_amount_out = self.calculate_minimum_amount_out(amount_out, slippage, token_decimal)
            logger.info(f"Transaction parameters - Input: {amount_in} lamports, Minimum output: {minimum_amount_out} tokens")

            logger.info("Checking for existing token account")
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

            logger.debug("Generating random seed for WSOL account")
            seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
            wsol_token_account = Pubkey.create_with_seed(
                self._payer.pubkey(), seed, self._token_program_id
            )
            balance_needed = Token.get_min_balance_rent_for_exempt_for_account(self._client)
            logger.debug(f"WSOL account address: {wsol_token_account}, required balance: {balance_needed} lamports")

            logger.info("Creating and initializing temporary WSOL account")
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

            logger.info("Creating swap instructions")
            swap_instruction = make_amm_v4_swap_instruction(
                amount_in=amount_in,
                minimum_amount_out=minimum_amount_out,
                token_account_in=wsol_token_account,
                token_account_out=token_account,
                accounts=pool_keys,
                owner=self._payer.pubkey(),
            )

            logger.info("Preparing to close WSOL account after swap")
            close_wsol_account_instruction = close_account(
                CloseAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    dest=self._payer.pubkey(),
                    owner=self._payer.pubkey(),
                )
            )

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

            logger.info("Compiling transaction message")
            compiled_message = MessageV0.try_compile(
                self._payer.pubkey(),
                instructions,
                [],
                self._client.get_latest_blockhash().value.blockhash,
            )

            logger.info("Sending transaction")
            txn_sig = self._client.send_transaction(
                txn=VersionedTransaction(compiled_message, [self._payer]),
                opts=TxOpts(skip_preflight=True),
            ).value
            logger.info(f"Transaction Signature: {txn_sig}")

            logger.info("Confirming transaction")
            confirmed = confirm_txn(txn_sig)

            logger.info(f"Transaction confirmed: {confirmed}")
            return confirmed

        except Exception as e:
            logger.error(f"Error occurred during transaction: {str(e)}", exc_info=True)
            return False

    def buy_by_token(self, token_mint_address: str, sol_in: float = 0.01, slippage: int = 5) -> bool:
        """
        Buy tokens using SOL by providing just the token mint address.
        
        Args:
            token_mint_address (str): Mint address of the token to buy
            sol_in (float): Amount of SOL to spend
            slippage (int): Maximum acceptable slippage percentage
            
        Returns:
            bool: True if transaction successful, False otherwise
        """
        try:
            logger.info(f"Looking up pair address for token mint {token_mint_address}")
            pair_addresses = get_amm_v4_pair_from_rpc(token_mint_address)
            
            if not pair_addresses or len(pair_addresses) == 0:
                logger.error(f"No trading pair found for token mint {token_mint_address}")
                return False
                
            # Use the first pair address found
            pair_address = pair_addresses[0]
            logger.info(f"Found pair address: {pair_address}")
            
            # Call the regular buy method with the found pair address
            return self.buy(pair_address, sol_in, slippage)
            
        except Exception as e:
            logger.error(f"Error buying token by mint address: {e}")
            return False

    def sell(self, pair_address: str, percentage: int = 100, slippage: int = 5) -> bool:
        """
        Sell tokens for SOL.
        
        Args:
            pair_address (str): Address of the trading pair
            percentage (int): Percentage of tokens to sell (1-100)
            slippage (int): Maximum acceptable slippage percentage
            
        Returns:
            bool: True if transaction successful, False otherwise
        """
        try:
            logger.info(f"Initiating sell transaction for pair {pair_address} - Selling {percentage}% with {slippage}% slippage")
            
            if not (1 <= percentage <= 100):
                logger.error(f"Invalid percentage value: {percentage}. Must be between 1 and 100")
                return False

            logger.info(f"Fetching AMM V4 pool keys for pair {pair_address}")
            pool_keys: Optional[AmmV4PoolKeys] = fetch_amm_v4_pool_keys(pair_address)
            if pool_keys is None:
                logger.error(f"Failed to fetch pool keys for pair {pair_address}")
                return False
            logger.debug("Successfully retrieved pool keys")

            mint = (
                pool_keys.base_mint if pool_keys.base_mint != self._wsol else pool_keys.quote_mint
            )
            logger.debug(f"Using mint address: {mint}")

            logger.info("Retrieving current token balance")
            token_balance = get_token_balance(str(mint))
            logger.info(f"Current token balance: {token_balance}")

            if token_balance == 0 or token_balance is None:
                logger.error("Insufficient token balance for sell transaction")
                return False

            token_balance = token_balance * (percentage / 100)
            logger.info(f"Adjusted token balance for {percentage}% sell: {token_balance}")

            logger.info("Calculating swap amounts and reserves")
            base_reserve, quote_reserve, token_decimal = get_amm_v4_reserves(pool_keys)
            amount_out = self.tokens_for_sol(token_balance, base_reserve, quote_reserve)
            logger.info(f"Estimated SOL output: {amount_out} (base_reserve: {base_reserve}, quote_reserve: {quote_reserve})")

            minimum_amount_out = self.calculate_minimum_amount_out(amount_out, slippage, self._sol_decimal)
            amount_in = int(token_balance * 10**token_decimal)
            logger.info(f"Transaction parameters - Input: {amount_in} tokens, Minimum output: {minimum_amount_out} lamports")
            
            token_account = get_associated_token_address(self._payer.pubkey(), mint)
            logger.debug(f"Using token account: {token_account}")

            logger.debug("Generating random seed for WSOL account")
            seed = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8")
            wsol_token_account = Pubkey.create_with_seed(
                self._payer.pubkey(), seed, self._token_program_id
            )
            balance_needed = Token.get_min_balance_rent_for_exempt_for_account(self._client)
            logger.debug(f"WSOL account address: {wsol_token_account}, required balance: {balance_needed} lamports")

            logger.info("Creating temporary WSOL account")
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

            logger.info("Creating swap instructions")
            swap_instruction = make_amm_v4_swap_instruction(
                amount_in=amount_in,
                minimum_amount_out=minimum_amount_out,
                token_account_in=token_account,
                token_account_out=wsol_token_account,
                accounts=pool_keys,
                owner=self._payer.pubkey(),
            )

            logger.info("Preparing to close WSOL account after swap")
            close_wsol_account_instruction = close_account(
                CloseAccountParams(
                    program_id=self._token_program_id,
                    account=wsol_token_account,
                    dest=self._payer.pubkey(),
                    owner=self._payer.pubkey(),
                )
            )

            instructions = [
                set_compute_unit_limit(self._unit_budget),
                set_compute_unit_price(self._unit_price),
                create_wsol_account_instruction,
                init_wsol_account_instruction,
                swap_instruction,
                close_wsol_account_instruction,
            ]

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

            logger.info("Compiling transaction message")
            compiled_message = MessageV0.try_compile(
                self._payer.pubkey(),
                instructions,
                [],
                self._client.get_latest_blockhash().value.blockhash,
            )

            logger.info("Sending transaction")
            txn_sig = self._client.send_transaction(
                txn=VersionedTransaction(compiled_message, [self._payer]),
                opts=TxOpts(skip_preflight=True),
            ).value
            logger.info(f"Transaction Signature: {txn_sig}")

            logger.info("Confirming transaction")
            confirmed = confirm_txn(txn_sig)

            logger.info(f"Transaction confirmed: {confirmed}")
            return confirmed

        except Exception as e:
            logger.error(f"Error occurred during transaction: {str(e)}", exc_info=True)
            return False

    def sell_by_token(self, token_mint_address: str, percentage: int = 100, slippage: int = 5) -> bool:
        """
        Sell tokens for SOL by providing just the token mint address.
        
        Args:
            token_mint_address (str): Mint address of the token to sell
            percentage (int): Percentage of tokens to sell (1-100)
            slippage (int): Maximum acceptable slippage percentage
            
        Returns:
            bool: True if transaction successful, False otherwise
        """
        try:
            logger.info(f"Looking up pair address for token mint {token_mint_address}")
            pair_addresses = get_amm_v4_pair_from_rpc(token_mint_address)
            
            if not pair_addresses or len(pair_addresses) == 0:
                logger.error(f"No trading pair found for token mint {token_mint_address}")
                return False
                
            # Use the first pair address found
            pair_address = pair_addresses[0]
            logger.info(f"Found pair address: {pair_address}")
            
            # Call the regular sell method with the found pair address
            return self.sell(pair_address, percentage, slippage)
            
        except Exception as e:
            logger.error(f"Error selling token by mint address: {e}")
            return False
