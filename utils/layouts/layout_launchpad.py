from construct import Int64ul, Int8ul, Bytes, Struct
from dataclasses import dataclass
from solders.pubkey import Pubkey

AUTH_SEED        = b"vault_auth_seed"
POOL_SEED        = b"pool"
POOL_VAULT_SEED  = b"pool_vault"
EVENT_AUTH_SEED  = b"__event_authority"

LAUNCHPAD_POOL_LAYOUT = Struct(
    "padding"          / Bytes(8),
    "epoch"            / Int64ul,
    "bump"             / Int8ul,
    "status"           / Int8ul,
    "dec_a"            / Int8ul,
    "dec_b"            / Int8ul,
    "migrate_type"     / Int8ul,

    "supply"           / Int64ul,
    "total_sell_a"     / Int64ul,
    "virtual_a"        / Int64ul,
    "virtual_b"        / Int64ul,
    "real_a"           / Int64ul,
    "real_b"           / Int64ul,
    "total_fund_b"     / Int64ul,
    "protocol_fee"     / Int64ul,
    "platform_fee"     / Int64ul,
    "migrate_fee"      / Int64ul,
    Bytes(5 * 8),  # vesting schedule

    "config_id"        / Bytes(32),
    "platform_id"      / Bytes(32),
    "mint_a"           / Bytes(32),
    "mint_b"           / Bytes(32),
    "vault_a"          / Bytes(32),
    "vault_b"          / Bytes(32),
    Bytes(32),     # creator
)

LAUNCHPAD_STATUS_LAYOUT = Struct(
    "padding"          / Bytes(8),
    "epoch"            / Int64ul,
    "bump"             / Int8ul,
    "status"           / Int8ul,
)
