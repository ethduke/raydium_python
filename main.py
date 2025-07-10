"""
Example script demonstrating how to use the Raydium API with Helius Sender and bundled Jito tips
"""

from model import RaydiumUnifiedJito

def main():
    """
    Demonstrate the ultimate solution: Unified Jito trading
    """
    print("\n" + "=" * 70)
    print("🛡️ ULTIMATE: Unified Jito Trading (Auto Detection + MEV Protection)")
    print("=" * 70)
    
    # Initialize the ultimate trader
    trader = RaydiumUnifiedJito()
    
    # Same token as above (BONK)
    token_mint_address = "9E1TrvTBSwfJvHSzgyZJCipQC3v1abPN76panRg2bonk"
    
    print(f"Token: {token_mint_address} (BONK)")
    print("\n🔍 Step 1: Auto-detecting pool type")
    
    # Demonstrate pool detection
    pool_type, pair_address = trader.detect_pool_type_and_address(token_mint_address)
    
    if pool_type and pair_address:
        print(f"✅ Pool Type: {pool_type.value}")
        print(f"✅ Pair Address: {pair_address}")
    else:
        print("❌ No compatible pool found")
        return
    
    result = trader.buy_with_jito(token_mint_address, 0.01, 5, 1000000)
    print(result)


if __name__ == "__main__":
    main()