# Raydium API

A Python client for interacting with the Raydium DEX on Solana blockchain.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/raydium_python.git
cd raydium_python

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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

```python
from model.raydium_v4 import RaydiumV4

# Initialize the client
client = RaydiumV4()

# Buy tokens with SOL using pair address
buy_result = client.buy(
    pair_address="58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",  # SOL/USDC pair
    sol_in=0.1,      # Amount of SOL to spend
    slippage=5       # 5% slippage
)

# Buy tokens with SOL using token mint address
buy_by_token_result = client.buy_by_token(
    token_mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    sol_in=0.1,      # Amount of SOL to spend
    slippage=5       # 5% slippage
)

# Sell tokens for SOL using pair address
sell_result = client.sell(
    pair_address="58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",  # SOL/USDC pair
    percentage=100,  # Sell 100% of tokens
    slippage=5       # 5% slippage
)

# Sell tokens for SOL using token mint address
sell_by_token_result = client.sell_by_token(
    token_mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    percentage=50,   # Sell 50% of tokens
    slippage=5       # 5% slippage
)
```

## Features

- SOL/Token swaps (buy and sell operations)
- Support for trading by pair address or token mint address
- Customizable slippage protection
- Real-time price calculations
- Built on Solana's fast and low-cost blockchain

## License

MIT License 