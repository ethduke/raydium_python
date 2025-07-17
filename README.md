# Raydium Python API

A Python client for executing trades on the Raydium DEX on Solana, featuring automatic pool detection (Raydium CPMM, Raydium v4, or Raydium Launchpad), Jito integration, and smart pool selection.

## Features

- **Smart Pool Detection**: Automatically detects and chooses between AMM V4, CPMM, and Launchpad pools
- **Raydium Launchpad Support**: Full support for Raydium Launchpad pools for new token launches
- **MEV Protection**: Jito integration with bundled tips for priority execution
- **Unified Interface**: Single API for all pool types
- **High Performance**: Helius RPC endpoints for reliable execution
- **Flexible Trading**: Support for both SOL/Token swaps by pair address or token mint
- **Intelligent Pool Selection**: Smart algorithm that prioritizes the best pool type for each token

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

### Smart Pool Detection and Trading (Recommended)

```python
from model import RaydiumTrader

trader = RaydiumTrader()

# Execute smart trade (automatically chooses best pool)
buy_result = await trader.execute_smart_trade(
    token_mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    sol_amount=0.01,
    slippage=5
)

# Sell tokens using smart pool detection
sell_result = await trader.execute_smart_trade(
    token_mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    sol_amount=0.01,
    slippage=5,
    sell_percentage=50
)
```

### Unified API with Jito Integration

```python
from model import RaydiumUnifiedJito

trader = RaydiumUnifiedJito()

# Buy tokens with MEV protection
buy_result = trader.buy_with_jito(
    token_mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    sol_in=0.01,
    slippage=5,
    tip_amount=1000000
)

# Sell tokens with MEV protection
sell_result = trader.sell_with_jito(
    token_mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    percentage=50,
    slippage=5,
    tip_amount=1000000
)
```

### Unified API without Jito (Basic)

```python
from model import RaydiumUnified

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

The API automatically detects and chooses between:

1. **AMM V4 Pools**: Traditional Raydium automated market maker pools
2. **CPMM Pools**: Concentrated liquidity pools for better capital efficiency  
3. **Launchpad Pools**: Raydium Launchpad pools for new token launches

### Smart Pool Selection

```python
from model import RaydiumTrader

trader = RaydiumTrader()

# Detect all pool types
pool_results = await trader.detect_all_pool_types("TOKEN_MINT_HERE")

# Get recommendation
recommendation = pool_results['recommendation']
print(f"Recommended: {recommendation['type'].upper()}")
print(f"Reason: {recommendation['reason']}")
```

## Raydium Launchpad Support

```python
from model import RaydiumLaunchpad

launchpad_trader = RaydiumLaunchpad()

# Buy tokens on launchpad
buy_result = await launchpad_trader.buy_by_token(
    token_mint="NEW_TOKEN_MINT",
    sol_in=0.01,
    slippage=5
)

# Sell tokens on launchpad
sell_result = await launchpad_trader.sell_by_token(
    token_mint="NEW_TOKEN_MINT",
    percentage=100,
    slippage=5
)
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

### RaydiumTrader (Smart Pool Detection)
- `detect_all_pool_types(token_mint)` - Detect all available pool types
- `execute_smart_trade(token_mint, sol_amount, slippage, sell_percentage)` - Execute trade with smart pool selection

### RaydiumLaunchpad
- `buy_by_token(token_mint, sol_in, slippage)` - Buy tokens on launchpad
- `sell_by_token(token_mint, percentage, slippage)` - Sell tokens on launchpad

### RaydiumUnifiedJito
- `buy_with_jito(token_mint, sol_in, slippage, tip_amount)` - Buy tokens with Jito tip
- `sell_with_jito(token_mint, percentage, slippage, tip_amount)` - Sell tokens with Jito tip
- `detect_pool_type_and_address(token_mint)` - Auto-detect best pool

## License

GPL License 
