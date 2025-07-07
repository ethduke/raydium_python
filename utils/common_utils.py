import json
import time
import logging
from solana.rpc.commitment import Confirmed, Processed
from solana.rpc.types import TokenAccountOpts
from solders.signature import Signature #type: ignore
from solders.pubkey import Pubkey  # type: ignore
from model.solana_provider import SolanaProvider

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Solana provider
solana_provider = SolanaProvider.get_instance()
client = solana_provider.rpc
payer_keypair = solana_provider.payer

logger.info("Successfully initialized Solana provider")
logger.info(f"Successfully initialized payer keypair: {payer_keypair.pubkey()}")

def get_token_balance(mint_str: str) -> float | None:
    try:
        if not payer_keypair:
            logger.error("Cannot get token balance: payer_keypair is not initialized")
            return None
            
        mint = Pubkey.from_string(mint_str)
        logger.info(f"Getting token balance for mint: {mint_str}")
        
        response = client.get_token_accounts_by_owner_json_parsed(
            payer_keypair.pubkey(),
            TokenAccountOpts(mint=mint),
            commitment=Processed
        )

        if response.value:
            accounts = response.value
            if accounts:
                token_amount = accounts[0].account.data.parsed['info']['tokenAmount']['uiAmount']
                if token_amount:
                    logger.info(f"Token balance: {token_amount}")
                    return float(token_amount)
        
        logger.warning(f"No token balance found for mint: {mint_str}")
        return None
    except Exception as e:
        logger.error(f"Error getting token balance: {e}")
        return None

def confirm_txn(txn_sig: Signature, max_retries: int = 20, retry_interval: int = 3) -> bool:
    retries = 1
    
    logger.info(f"Confirming transaction: {txn_sig}")
    
    while retries < max_retries:
        try:
            txn_res = client.get_transaction(
                txn_sig, 
                encoding="json", 
                commitment=Confirmed, 
                max_supported_transaction_version=0)
            
            txn_json = json.loads(txn_res.value.transaction.meta.to_json())
            
            if txn_json['err'] is None:
                logger.info(f"Transaction confirmed after {retries} attempts")
                print("Transaction confirmed... try count:", retries)
                return True
            
            logger.warning(f"Transaction not confirmed on attempt {retries}")
            print("Error: Transaction not confirmed. Retrying...")
            if txn_json['err']:
                logger.error(f"Transaction failed with error: {txn_json['err']}")
                print("Transaction failed.")
                return False
        except Exception as e:
            logger.warning(f"Awaiting confirmation (attempt {retries}): {e}")
            print("Awaiting confirmation... try count:", retries)
            retries += 1
            time.sleep(retry_interval)
    
    logger.error(f"Max retries ({max_retries}) reached. Transaction confirmation failed.")
    print("Max retries reached. Transaction confirmation failed.")
    return False
