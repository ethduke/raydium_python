from solana.rpc.api import Client
from solders.keypair import Keypair 
from solders.pubkey import Pubkey
import os
import logging
import yaml
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for the application"""
    
    def __init__(self):
        self._config = {}
        self._load_env()
        self._load_yaml()
        self._validate_config()

    def _load_env(self):
        """Load environment variables"""
        load_dotenv(override=True)
        
        # Required environment variables
        required_vars = [
            'HELIUS_API_KEY',
            'ACC_PRIVATE_KEY'
        ]
        
        # Validate and load required variables
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                raise ValueError(f"Missing required environment variable: {var}")
            
        # Load environment-specific configuration
        self._config['env'] = {
            'helius': {
                'api_key': os.getenv('HELIUS_API_KEY'),
                'ws_url': f"wss://atlas-mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}",
                'rpc_url': f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}",
                'staked_rpc_url': f"https://staked.helius-rpc.com?api-key={os.getenv('HELIUS_API_KEY')}"
            },
            'acc_private_key': os.getenv('ACC_PRIVATE_KEY')
        }

    def _load_yaml(self):
        """Load YAML configuration"""
        config_path = Path(__file__).parent / 'config.yaml'
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path) as f:
            self._config.update(yaml.safe_load(f))
            
    def _validate_config(self):
        """Validate configuration"""
        required_keys = ['helius', 'solana', 'programs', 'tokens', 'constants']
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"Missing required configuration key: {key}")
                
        # Validate Helius configuration
        helius_config = self._config.get('helius', {})
        if 'rpc_url' not in helius_config:
            raise ValueError("Missing Helius RPC URL configuration")
            
        # Validate Solana configuration
        solana_config = self._config.get('solana', {})
        if 'unit_budget' not in solana_config or 'unit_price' not in solana_config:
            raise ValueError("Missing Solana unit budget or price configuration")
            
        # No need to set private key again as it's already in env section

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value
    
    def get_payer_keypair(self) -> Keypair:
        """Get wallet keypair"""
        try:
            private_key = self._config['env']['acc_private_key'].strip()
            print(f"Private key length: {len(private_key)}")
            print(f"First few characters: {private_key[:10]}...")
            print(f"Is base64-like? {all(c in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/=' for c in private_key)}")
            
            if private_key.startswith('[') and private_key.endswith(']'):
                key_array = [int(x.strip()) for x in private_key[1:-1].split(',')]
                keypair = Keypair.from_bytes(bytes(key_array))
            else:
                # Try decoding from base64 first if it looks like base64
                if all(c in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/=' for c in private_key):
                    import base64
                    try:
                        decoded = base64.b64decode(private_key)
                        keypair = Keypair.from_bytes(decoded)
                    except:
                        # If base64 fails, try base58
                        keypair = Keypair.from_base58_string(private_key)
                else:
                    keypair = Keypair.from_base58_string(private_key)
                    
            logger.info(f"Successfully loaded payer keypair with public key: {keypair.pubkey()}")
            return keypair
        except Exception as e:
            logger.error(f"Failed to load payer keypair: {e}")
            raise
    
    def get_solana_rpc_client(self) -> Client:
        """Get RPC client"""
        return Client(self._config['env']['helius']['rpc_url'])

    def get_unit_budget(self) -> int:
        """Get unit budget"""
        return self._config['solana']['unit_budget']

    def get_unit_price(self) -> int:
        """Get unit price"""
        return self._config['solana']['unit_price']

    # Constants getters
    @property
    def RAYDIUM_AMM_V4(self) -> Pubkey:
        """Get Raydium AMM V4 program ID"""
        return Pubkey.from_string(self._config['programs']['raydium']['amm_v4'])
    
    @property
    def DEFAULT_QUOTE_MINT(self) -> str:
        """Get default quote mint address"""
        return self._config['tokens']['default_quote_mint']
    
    @property
    def TOKEN_PROGRAM_ID(self) -> Pubkey:
        """Get token program ID"""
        return Pubkey.from_string(self._config['programs']['token']['program_id'])
    
    @property
    def TOKEN_2022_PROGRAM_ID(self) -> Pubkey:
        """Get token 2022 program ID"""
        return Pubkey.from_string(self._config['programs']['token']['program_id_2022'])
    
    @property
    def MEMO_PROGRAM_V2(self) -> Pubkey:
        """Get memo program v2 ID"""
        return Pubkey.from_string(self._config['programs']['memo']['v2'])
    
    @property
    def ACCOUNT_LAYOUT_LEN(self) -> int:
        """Get account layout length"""
        return self._config['constants']['account_layout_len']
    
    @property
    def WSOL(self) -> Pubkey:
        """Get WSOL address"""
        return Pubkey.from_string(self._config['tokens']['wsol']['address'])
    
    @property
    def SOL_DECIMAL(self) -> int:
        """Get SOL decimal"""
        return self._config['tokens']['wsol']['decimal']

    @property
    def RAY_AUTHORITY_V4(self) -> Pubkey:
        """Get Raydium Authority V4 address"""
        return Pubkey.from_string(self._config['programs']['raydium']['ray_authority_v4'])
    
    @property
    def OPENBOOK_PROGRAM_ID(self) -> Pubkey:
        """Get OpenBook program ID"""
        return Pubkey.from_string(self._config['programs']['openbook']['program_id'])

# Create a singleton instance
config = Config()
