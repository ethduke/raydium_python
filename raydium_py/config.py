from solana.rpc.api import Client
from solders.keypair import Keypair #type: ignore

PRIV_KEY = ""
RPC = "https://mainnet.helius-rpc.com/?api-key="
UNIT_BUDGET =  150_000
UNIT_PRICE =  1_000_000
client = Client(RPC)
payer_keypair = Keypair.from_base58_string(PRIV_KEY)