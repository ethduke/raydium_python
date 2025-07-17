import os
import base64
import struct
import logging
from typing import Optional, List

from solana.rpc.types import TokenAccountOpts, TxOpts
from solana.rpc.commitment import Processed
from solders.pubkey import Pubkey
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
    initialize_account,
    InitializeAccountParams,
    CloseAccountParams, close_account
)
from solders.system_program import CreateAccountWithSeedParams, create_account_with_seed
from solders.instruction import Instruction, AccountMeta

from ..providers.solana_provider import SolanaProvider
from ..providers.solana_transaction_provider import SolanaTransactionProvider
from ..providers.solana_token_provider import SolanaTokenProvider

from utils.pool_utils_launchpad import (
    find_launchpad_pool_by_mint,
    fetch_launchpad_pool_keys,
    calculate_launchpad_constant_product_swap,
    calculate_launchpad_constant_product_sell
)
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Raydium Launchpad] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

RENT_EXEMPT     = config.RENT_EXEMPT
ACCOUNT_SIZE    = config.ACCOUNT_LAYOUT_LEN
SOL_DECIMALS    = config.SOL_DECIMAL
COMPUTE_UNITS   = config.COMPUTE_UNITS
TOKEN_PROGRAM   = config.TOKEN_PROGRAM_ID

BUY_EXACT_IN_DISCRIM = bytes([250, 234, 13, 123, 213, 156, 19, 236])
SELL_EXACT_IN_DISCRIM = bytes([149, 39, 222, 155, 211, 124, 152, 26])

class RaydiumLaunchpad:
    def __init__(self, solana_provider: Optional[SolanaProvider] = None):
        self._provider = solana_provider or SolanaProvider.get_instance()
        self._client = self._provider.rpc
        self._payer = self._provider.payer
        self._transaction_provider = SolanaTransactionProvider(self._provider)
        self._token_provider = SolanaTokenProvider(self._provider)
        self._sol_decimal = config.SOL_DECIMAL
        self._account_layout_len = config.ACCOUNT_LAYOUT_LEN
        self._token_program_id = config.TOKEN_PROGRAM_ID
        self._unit_budget = config.get_unit_budget()
        self._unit_price = config.get_unit_price()
        logger.info(f"Initialized RaydiumLaunchpad with payer: {self._payer.pubkey()}")

    def create_versioned_swap_transaction(self, instructions: List[Instruction]) -> VersionedTransaction:
        """Create a versioned transaction for a swap operation."""
        try:
            logger.info("Compiling transaction message")
            blockhash = self._client.get_latest_blockhash().value.blockhash
            compiled_message = MessageV0.try_compile(
                self._payer.pubkey(),
                instructions,
                [],
                blockhash,
            )
            return VersionedTransaction(compiled_message, [self._payer])
        except Exception as e:
            logger.error(f"Error occurred during transaction creation: {str(e)}", exc_info=True)
            return None

    def execute_versioned_transaction(self, versioned_transaction: VersionedTransaction) -> bool:
        """Execute a versioned transaction."""
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

    async def buy_by_token(self, token_mint: str, sol_in: float = 0.01, slippage: int = 5) -> bool:
        try:
            logger.info(f"Initiating launchpad buy for token {token_mint} with {sol_in} SOL and {slippage}% slippage")
            pool_id = await find_launchpad_pool_by_mint(token_mint)
            if not pool_id:
                logger.error(f"No launchpad pool found for token {token_mint}")
                return False
            keys = await fetch_launchpad_pool_keys(pool_id)
            if not keys:
                logger.error("Failed to fetch pool keys for launchpad pool")
                return False
            if keys.status == 2:
                logger.error("Pool is migrated")
                return False
            amount_in = int(sol_in * self._sol_decimal)
            expected = calculate_launchpad_constant_product_swap(keys, sol_in)
            min_out = int(expected * (1 - slippage / 100) * 10 ** keys.decimals_a)
            logger.info(f"Transaction parameters - Input: {amount_in} lamports, Minimum output: {min_out} tokens")
            out_mint = Pubkey.from_string(token_mint)
            resp = self._client.get_token_accounts_by_owner(
                self._payer.pubkey(), TokenAccountOpts(mint=out_mint), Processed
            )
            if resp.value:
                user_ata = resp.value[0].pubkey
                create_ata_ix = None
            else:
                user_ata = get_associated_token_address(self._payer.pubkey(), out_mint)
                create_ata_ix = create_associated_token_account(
                    self._payer.pubkey(), self._payer.pubkey(), out_mint
                )
            seed = base64.urlsafe_b64encode(os.urandom(12)).decode()
            temp_wsol = Pubkey.create_with_seed(self._payer.pubkey(), seed, TOKEN_PROGRAM)
            create_w_ix = create_account_with_seed(CreateAccountWithSeedParams(
                from_pubkey=self._payer.pubkey(),
                to_pubkey=temp_wsol,
                base=self._payer.pubkey(),
                seed=seed,
                lamports=RENT_EXEMPT + amount_in,
                space=ACCOUNT_SIZE,
                owner=TOKEN_PROGRAM,
            ))
            init_w_ix = initialize_account(
                InitializeAccountParams(
                    program_id=TOKEN_PROGRAM,
                    account=temp_wsol,
                    mint=Pubkey.from_string("So11111111111111111111111111111111111111112"),
                    owner=self._payer.pubkey(),
                )
            )
            metas = [
                AccountMeta(self._payer.pubkey(), True, False),
                AccountMeta(keys.authority, False, False),
                AccountMeta(keys.config_id, False, False),
                AccountMeta(keys.platform_id, False, False),
                AccountMeta(keys.pool_id, False, True),
                AccountMeta(user_ata, False, True),
                AccountMeta(temp_wsol, False, True),
                AccountMeta(keys.vault_a, False, True),
                AccountMeta(keys.vault_b, False, True),
                AccountMeta(keys.mint_a, False, False),
                AccountMeta(keys.mint_b, False, False),
                AccountMeta(TOKEN_PROGRAM, False, False),
                AccountMeta(TOKEN_PROGRAM, False, False),
                AccountMeta(keys.event_auth, False, False),
                AccountMeta(keys.program_id, False, False),
            ]
            data = (
                BUY_EXACT_IN_DISCRIM
                + struct.pack("<Q", amount_in)
                + struct.pack("<Q", min_out)
                + struct.pack("<Q", 0)
            )
            swap_ix = Instruction(keys.program_id, data, metas)
            instructions = [
                set_compute_unit_limit(self._unit_budget),
                set_compute_unit_price(self._unit_price),
                create_w_ix, init_w_ix,
            ]
            if create_ata_ix:
                instructions.append(create_ata_ix)
            instructions.append(swap_ix)
            instructions.append(close_account(CloseAccountParams(
                program_id=TOKEN_PROGRAM,
                account=temp_wsol,
                dest=self._payer.pubkey(),
                owner=self._payer.pubkey(),
            )))
            versioned_transaction = self.create_versioned_swap_transaction(instructions)
            return self.execute_versioned_transaction(versioned_transaction)
        except Exception as e:
            logger.error(f"Error during buy transaction: {e}", exc_info=True)
            return False

    async def sell_by_token(self, token_mint: str, percentage: int = 100, slippage: int = 5) -> bool:
        try:
            logger.info(f"Initiating launchpad sell for token {token_mint} - {percentage}% with {slippage}% slippage")
            if not (1 <= percentage <= 100):
                logger.error(f"Invalid percentage value: {percentage}. Must be between 1 and 100")
                return False
            pool_id = await find_launchpad_pool_by_mint(token_mint)
            if not pool_id:
                logger.error(f"No launchpad pool found for token {token_mint}")
                return False
            keys = await fetch_launchpad_pool_keys(pool_id)
            if not keys:
                logger.error("Failed to fetch pool keys for launchpad pool")
                return False
            if keys.status == 2:
                logger.error("Pool is migrated")
                return False
            token_pk = Pubkey.from_string(token_mint)
            bal_resp = self._client.get_token_accounts_by_owner_json_parsed(
                self._payer.pubkey(), TokenAccountOpts(mint=token_pk), Processed
            )
            if not bal_resp.value:
                logger.error("No token balance to sell")
                return False
            token_balance = float(bal_resp.value[0].account.data.parsed["info"]["tokenAmount"]["uiAmount"] or 0)
            user_ata = bal_resp.value[0].pubkey
            if token_balance <= 0:
                logger.error("Insufficient token balance")
                return False
            sell_amount = token_balance * (percentage / 100)
            if sell_amount <= 0:
                logger.error("Sell amount too small")
                return False
            expected_sol = calculate_launchpad_constant_product_sell(keys, sell_amount)
            min_sol_out = int(expected_sol * (1 - slippage / 100) * SOL_DECIMALS)
            token_amount_raw = int(sell_amount * 10 ** keys.decimals_a)
            logger.info(f"Transaction parameters - Input: {token_amount_raw} tokens, Minimum output: {min_sol_out} lamports")
            seed = base64.urlsafe_b64encode(os.urandom(12)).decode()
            temp_wsol = Pubkey.create_with_seed(self._payer.pubkey(), seed, TOKEN_PROGRAM)
            create_w_ix = create_account_with_seed(CreateAccountWithSeedParams(
                from_pubkey=self._payer.pubkey(),
                to_pubkey=temp_wsol,
                base=self._payer.pubkey(),
                seed=seed,
                lamports=RENT_EXEMPT,
                space=ACCOUNT_SIZE,
                owner=TOKEN_PROGRAM,
            ))
            init_w_ix = initialize_account(
                InitializeAccountParams(
                    program_id=TOKEN_PROGRAM,
                    account=temp_wsol,
                    mint=Pubkey.from_string("So11111111111111111111111111111111111111112"),
                    owner=self._payer.pubkey(),
                )
            )
            metas = [
                AccountMeta(self._payer.pubkey(), True, False),
                AccountMeta(keys.authority, False, False),
                AccountMeta(keys.config_id, False, False),
                AccountMeta(keys.platform_id, False, False),
                AccountMeta(keys.pool_id, False, True),
                AccountMeta(user_ata, False, True),
                AccountMeta(temp_wsol, False, True),
                AccountMeta(keys.vault_a, False, True),
                AccountMeta(keys.vault_b, False, True),
                AccountMeta(keys.mint_a, False, False),
                AccountMeta(keys.mint_b, False, False),
                AccountMeta(TOKEN_PROGRAM, False, False),
                AccountMeta(TOKEN_PROGRAM, False, False),
                AccountMeta(keys.event_auth, False, False),
                AccountMeta(keys.program_id, False, False),
            ]
            data = (
                SELL_EXACT_IN_DISCRIM
                + struct.pack("<Q", token_amount_raw)
                + struct.pack("<Q", min_sol_out)
                + struct.pack("<Q", 0)
            )
            sell_ix = Instruction(keys.program_id, data, metas)
            instructions = [
                set_compute_unit_limit(self._unit_budget),
                set_compute_unit_price(self._unit_price),
                create_w_ix, init_w_ix,
                sell_ix,
                close_account(CloseAccountParams(
                    program_id=TOKEN_PROGRAM,
                    account=temp_wsol,
                    dest=self._payer.pubkey(),
                    owner=self._payer.pubkey(),
                ))
            ]
            if percentage == 100:
                logger.info("Preparing to close token account after swap")
                close_token_account_instruction = close_account(
                    CloseAccountParams(
                        program_id=TOKEN_PROGRAM,
                        account=user_ata,
                        dest=self._payer.pubkey(),
                        owner=self._payer.pubkey(),
                    )
                )
                instructions.append(close_token_account_instruction)
            versioned_transaction = self.create_versioned_swap_transaction(instructions)
            return self.execute_versioned_transaction(versioned_transaction)
        except Exception as e:
            logger.error(f"Error during sell transaction: {e}", exc_info=True)
            return False