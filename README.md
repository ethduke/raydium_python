# Raydium Python API

A comprehensive Python client for interacting with the Raydium DEX on Solana blockchain, featuring automatic pool detection (Raydium CPMM or Raydium v4), Jito integration.

## Features

- **Auto Pool Detection**: Automatically chooses between AMM V4 and CPMM pools
- **MEV Protection**: Jito integration with bundled tips for priority execution
- **Unified Interface**: Single API for all pool types
- **High Performance**: Helius RPC endpoints for reliable execution
- **Flexible Trading**: Support for both SOL/Token swaps by pair address or token mint

## Installation

```bash
# Clone the repository
git clone https://github.com/ethduke/raydium_python.git
cd raydium_python

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root
2. Add your Helius API key and account private key:
```
HELIUS_API_KEY=your_helius_api_key
ACC_PRIVATE_KEY=your_private_key
```

## Quick Start

### Unified API with Jito Integration (Recommended)

The unified API automatically detects the best pool type and provides MEV protection through Jito bundling:

```python
from model import RaydiumUnifiedJito

# Initialize the unified trader with MEV protection
trader = RaydiumUnifiedJito()

# Example token: BONK
token_mint_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"

# Auto-detect pool type and get pair address
pool_type, pair_address = trader.detect_pool_type_and_address(token_mint_address)
print(f"Detected {pool_type.value} pool: {pair_address}")

# Buy tokens with MEV protection (0.01 SOL, 5% slippage, 0.001 SOL tip)
buy_result = trader.buy_with_jito(
    token_mint=token_mint_address,
    sol_in=0.01,        # Amount of SOL to spend
    slippage=5,         # 5% slippage tolerance
    tip_amount=1000000  # 0.001 SOL tip for MEV protection
)

print(f"Buy transaction: {buy_result}")

# Sell 50% of tokens with MEV protection
sell_result = trader.sell_with_jito(
    token_mint=token_mint_address,
    percentage=50,      # Sell 50% of tokens
    slippage=5,         # 5% slippage tolerance
    tip_amount=1000000  # 0.001 SOL tip for MEV protection
)

print(f"Sell transaction: {sell_result}")
```

### Unified API without Jito (Basic)

For standard trading without MEV protection:

```python
from model import RaydiumUnified

# Initialize the unified trader
trader = RaydiumUnified()

# Buy tokens (automatically detects pool type)
buy_result = trader.buy_by_token(
    token_mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    sol_in=0.01,
    slippage=5
)

# Sell tokens
sell_result = trader.sell_by_token(
    token_mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    percentage=100,
    slippage=5
)
```

## Pool Auto-Detection

The unified API automatically detects and chooses between different pool types:

1. **AMM V4 Pools**: Traditional Raydium automated market maker pools
2. **CPMM Pools**: Concentrated liquidity pools for better capital efficiency

```python
from model import RaydiumUnifiedJito

trader = RaydiumUnifiedJito()

# The system automatically:
# 1. Searches for AMM V4 pools first
# 2. Falls back to CPMM pools if V4 not available
# 3. Returns the pool type and address for the best available option

pool_type, pair_address = trader.detect_pool_type_and_address("TOKEN_MINT_HERE")

if pool_type:
    print(f"Found {pool_type.value} pool at {pair_address}")
    # Proceed with trading using the detected pool
else:
    print("No compatible pools found for this token")
```

## MEV Protection with Jito

The Jito integration provides MEV protection through:

- **Bundled Transactions**: Tips are bundled with your swap for priority execution
- **Multiple Endpoints**: Automatic failover across Helius Sender endpoints
- **Random Tip Accounts**: Load balancing across Jito tip addresses
- **Confirmation Tracking**: Optional transaction confirmation

```python
# Customize tip amount for different priority levels
high_priority_tip = 5000000    # 0.005 SOL - high priority
normal_tip = 1000000          # 0.001 SOL - normal priority
low_tip = 100000              # 0.0001 SOL - low priority

# Execute trade with custom tip
result = trader.buy_with_jito(
    token_mint="YOUR_TOKEN_MINT",
    sol_in=0.1,
    slippage=5,
    tip_amount=high_priority_tip  # Higher tip = higher priority
)
```

## Error Handling

All trading methods return comprehensive result objects:

```python
result = trader.buy_with_jito("TOKEN_MINT", 0.01, 5, 1000000)

if result.get("success"):
    print(f"✅ Transaction successful: {result['signature']}")
    print(f"📊 Method used: {result['method']}")
    if result.get("confirmed"):
        print("✅ Transaction confirmed on-chain")
else:
    print(f"❌ Transaction failed: {result.get('error', 'Unknown error')}")
```

## Trading Parameters

- **sol_in**: Amount of SOL to spend (float, e.g., 0.01 = 0.01 SOL)
- **percentage**: Percentage of tokens to sell (int, 1-100)
- **slippage**: Slippage tolerance (int, percentage, e.g., 5 = 5%)
- **tip_amount**: Jito tip in lamports (int, e.g., 1000000 = 0.001 SOL)

## API Reference

### RaydiumUnifiedJito

- `buy_with_jito(token_mint, sol_in, slippage, tip_amount)` - Buy tokens with with Jito tip
- `sell_with_jito(token_mint, percentage, slippage, tip_amount)` - Sell tokens with Jito tip
- `detect_pool_type_and_address(token_mint)` - Auto-detect best pool 

## License

GPL License 
