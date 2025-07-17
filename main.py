"""
Example script demonstrating how to use the Raydium API with Helius Sender and bundled Jito tips
"""

import asyncio
import time

from model.raydium.raydium_trader import RaydiumTrader # type: ignore

async def main():
    """
    Demonstrate smart pool detection and trading
    """
    print("\n" + "=" * 70)
    print("🧠 SMART POOL DETECTION & TRADING")
    print("=" * 70)
    
    # Initialize smart detector
    raydium_trader = RaydiumTrader()
    
    # Single test token - Launchpad token
    token_mint = "4SJPkYbQhWxa5vGjDce91wg2xzada3C2h6FhZHgfbonk"
    
    print(f"\n{'='*20} TESTING TOKEN {'='*20}")
    
    # Detect all pool types
    pool_results = await raydium_trader.detect_all_pool_types(token_mint)
    
    # Display summary
    print(f"\n📋 Pool Summary for {token_mint}:")
    for pool_type, data in pool_results.items():
        if pool_type != 'recommendation' and data:
            print(f"   • {data['type']}: {data['address']}")
    
    # Execute smart trade with real buy/sell
    print(f"\n🚀 Executing Smart Trade")
    print("=" * 40)
    
    # Buy tokens
    buy_result = await raydium_trader.execute_smart_trade(token_mint, 0.15, 5)
    print(f"Buy result: {buy_result}")
    
    if buy_result.get('success'):
        print("✅ Buy successful!")
        
        # Wait a moment for transaction to settle
        time.sleep(3)
        
        # Sell 50% of tokens
        sell_result = await raydium_trader.execute_smart_trade(token_mint, 0.001, 5, sell_percentage=50)
        print(f"Sell result: {sell_result}")
    else:
        print("❌ Buy failed, skipping sell test")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())