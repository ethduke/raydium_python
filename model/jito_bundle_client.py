import requests
from solana.transaction import Transaction
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transfer import TransferParams, transfer
from typing import List, Dict, Any
from config import config

class JitoBundleClient:
    """Client for submitting Jito bundles via Helius"""
    
    def __init__(self):
        self.rpc_url = config.get_solana_rpc_client()
        self.session = requests.Session()
        
        # Jito tip accounts
        self.tip_accounts = [
            "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
            "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe", 
            "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
            "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
            "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
            "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
            "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
            "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"
        ]
    
    def get_random_tip_account(self) -> PublicKey:
        """Get a random tip account for load balancing"""
        import random
        tip_account_str = random.choice(self.tip_accounts)
        return PublicKey(tip_account_str)
    
    def create_tip_transaction(self, payer: Keypair, tip_amount: int) -> Transaction:
        """Create a tip transaction to prioritize bundle"""
        tip_account = self.get_random_tip_account()
        tip_instruction = transfer(
            TransferParams(
                from_pubkey=payer.public_key,
                to_pubkey=tip_account,
                lamports=tip_amount
            )
        )
        
        transaction = Transaction()
        transaction.add(tip_instruction)
        return transaction
    
    def send_bundle(self, transactions: List[str]) -> Dict[str, Any]:
        """Send a bundle of transactions to Jito via Helius"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendBundle",
            "params": {
                "transactions": transactions
            }
        }
        
        try:
            response = self.session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Bundle submission error: {e}")
            return {"error": str(e)}
    
    def get_bundle_status(self, bundle_id: str) -> Dict[str, Any]:
        """Check the status of a submitted bundle"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBundleStatuses",
            "params": [[bundle_id]]
        }
        
        try:
            response = self.session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Bundle status error: {e}")
            return {"error": str(e)}
