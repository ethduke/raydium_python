from dataclasses import dataclass
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed, Processed
from solana.rpc.types import MemcmpOpts, DataSliceOpts
from utils.layouts.layout_launchpad import LAUNCHPAD_POOL_LAYOUT, LAUNCHPAD_STATUS_LAYOUT
from typing import Optional, Tuple
from config import config
from model.providers.solana_provider import SolanaProvider

AUTH_SEED        = b"vault_auth_seed"
POOL_SEED        = b"pool"
POOL_VAULT_SEED  = b"pool_vault"
EVENT_AUTH_SEED  = b"__event_authority"

@dataclass
class LaunchpadPoolKeys:
    program_id: Pubkey
    pool_id: Pubkey
    authority: Pubkey
    event_auth: Pubkey
    status: int
    config_id: Pubkey
    platform_id: Pubkey
    mint_a: Pubkey
    mint_b: Pubkey
    decimals_a: int
    decimals_b: int
    virtual_a: int
    virtual_b: int
    real_a: int
    real_b: int
    vault_a: Pubkey
    vault_b: Pubkey

async def find_launchpad_pool_by_mint(mint: str) -> Optional[str]:
    """Find launchpad pool by token mint address."""
    rpc = SolanaProvider.get_instance().rpc
    mint_pk = Pubkey.from_string(mint)
    MINT_A_OFFSET = 205
    MINT_B_OFFSET = 237
    slice_opt = DataSliceOpts(offset=0, length=MINT_B_OFFSET + 32)
    for off in (MINT_A_OFFSET, MINT_B_OFFSET):
        resp = rpc.get_program_accounts(
            config.RAYDIUM_LAUNCHPAD,
            commitment=Confirmed,
            encoding="base64",
            data_slice=slice_opt,
            filters=[MemcmpOpts(offset=off, bytes=str(mint_pk))]
        )
        if resp.value:
            return str(resp.value[0].pubkey)
    return None

async def check_launchpad_migrated(pool_id: str | Pubkey) -> bool:
    """Check if launchpad pool has migrated."""
    rpc = SolanaProvider.get_instance().rpc
    pool_pk = pool_id if isinstance(pool_id, Pubkey) else Pubkey.from_string(pool_id)
    try:
        acc = rpc.get_account_info_json_parsed(pool_pk, commitment=Processed)
        raw = LAUNCHPAD_STATUS_LAYOUT.parse(acc.value.data)
        return raw.status == 2
    except Exception:
        return False

async def fetch_launchpad_pool_keys(pool_id: str | Pubkey) -> Optional[LaunchpadPoolKeys]:
    """Fetch launchpad pool keys."""
    rpc = SolanaProvider.get_instance().rpc
    pool_pk = pool_id if isinstance(pool_id, Pubkey) else Pubkey.from_string(pool_id)
    try:
        acc = rpc.get_account_info_json_parsed(pool_pk, commitment=Processed)
        raw = LAUNCHPAD_POOL_LAYOUT.parse(acc.value.data)
        auth, _ = Pubkey.find_program_address([AUTH_SEED], config.RAYDIUM_LAUNCHPAD)
        evt_auth, _ = Pubkey.find_program_address([EVENT_AUTH_SEED], config.RAYDIUM_LAUNCHPAD)
        return LaunchpadPoolKeys(
            program_id=config.RAYDIUM_LAUNCHPAD,
            pool_id=pool_pk,
            authority=auth,
            event_auth=evt_auth,
            config_id=Pubkey.from_bytes(raw.config_id),
            platform_id=Pubkey.from_bytes(raw.platform_id),
            mint_a=Pubkey.from_bytes(raw.mint_a),
            mint_b=Pubkey.from_bytes(raw.mint_b),
            decimals_a=raw.dec_a,
            decimals_b=raw.dec_b,
            virtual_a=raw.virtual_a,
            virtual_b=raw.virtual_b,
            vault_a=Pubkey.from_bytes(raw.vault_a),
            vault_b=Pubkey.from_bytes(raw.vault_b),
            real_a=raw.real_a,
            real_b=raw.real_b,
            status=raw.status,
        )
    except Exception as e:
        print(f"[Launchpad] pool decode failed: {e}")
        return None

async def get_launchpad_pool_reserves(keys: LaunchpadPoolKeys) -> Tuple[float, float]:
    """Get launchpad pool reserves as (reserve_a, reserve_b) in decimal."""
    rpc = SolanaProvider.get_instance().rpc
    try:
        infos = rpc.get_multiple_accounts_json_parsed(
            [keys.vault_a, keys.vault_b], commitment=Processed
        )
        ui_a = infos.value[0].data.parsed["info"]["tokenAmount"]["uiAmount"]
        ui_b = infos.value[1].data.parsed["info"]["tokenAmount"]["uiAmount"]
        return float(ui_a or 0), float(ui_b or 0)
    except Exception as e:
        print(f"[Launchpad] Error fetching vault reserves: {e}")
        return 0.0, 0.0

def calculate_launchpad_pool_price(keys: LaunchpadPoolKeys, curve_type: int = 0) -> float:
    """Calculate launchpad pool price for a given curve type."""
    virtual_a_decimal = keys.virtual_a / (10 ** keys.decimals_a)
    virtual_b_decimal = keys.virtual_b / (10 ** keys.decimals_b)
    real_a_decimal = keys.real_a / (10 ** keys.decimals_a)
    real_b_decimal = keys.real_b / (10 ** keys.decimals_b)
    decimal_adjustment = 10 ** (keys.decimals_a - keys.decimals_b)
    if curve_type == 0:
        numerator = virtual_b_decimal + real_b_decimal
        denominator = virtual_a_decimal - real_a_decimal
        if denominator <= 0:
            return 0.0
        return (numerator / denominator) * decimal_adjustment
    elif curve_type == 1:
        if virtual_a_decimal <= 0:
            return 0.0
        return (virtual_b_decimal / virtual_a_decimal) * decimal_adjustment
    elif curve_type == 2:
        Q64 = 2 ** 64
        return (keys.virtual_a * keys.real_a / Q64) * decimal_adjustment
    else:
        raise ValueError(f"Unknown curve type: {curve_type}")

def calculate_launchpad_constant_product_swap(keys: LaunchpadPoolKeys, sol_amount_decimal: float) -> float:
    """Calculate token output for constant product curve."""
    virtual_a_decimal = keys.virtual_a / (10 ** keys.decimals_a)
    virtual_b_decimal = keys.virtual_b / (10 ** keys.decimals_b)
    real_a_decimal = keys.real_a / (10 ** keys.decimals_a)
    real_b_decimal = keys.real_b / (10 ** keys.decimals_b)
    input_reserve = virtual_b_decimal + real_b_decimal
    output_reserve = virtual_a_decimal - real_a_decimal
    if input_reserve <= 0 or output_reserve <= 0:
        return 0.0
    effective_input = sol_amount_decimal * 0.99
    numerator = effective_input * output_reserve
    denominator = input_reserve + effective_input
    return numerator / denominator

def calculate_launchpad_constant_product_sell(keys: LaunchpadPoolKeys, token_amount_decimal: float) -> float:
    """Calculate SOL output for selling tokens (constant product curve)."""
    virtual_a_decimal = keys.virtual_a / (10 ** keys.decimals_a)
    virtual_b_decimal = keys.virtual_b / (10 ** keys.decimals_b)
    real_a_decimal = keys.real_a / (10 ** keys.decimals_a)
    real_b_decimal = keys.real_b / (10 ** keys.decimals_b)
    input_reserve = virtual_a_decimal - real_a_decimal
    output_reserve = virtual_b_decimal + real_b_decimal
    if input_reserve <= 0 or output_reserve <= 0:
        return 0.0
    effective_input = token_amount_decimal * 0.99
    numerator = effective_input * output_reserve
    denominator = input_reserve + effective_input
    return numerator / denominator
