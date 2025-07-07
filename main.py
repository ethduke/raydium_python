"""
Example script demonstrating how to use the Raydium API with Helius Sender and bundled Jito tips
"""

from model.raydium_v4_jito import HeliusEnhancedRaydiumV4

def main():
    # Initialize the Raydium client with Helius Sender and Jito support
    raydium = HeliusEnhancedRaydiumV4()
    
    # Replace with a popular token that has a Raydium pair (BONK)
    token_mint_address = "3mNHDX54Y8FXfGAbchwpGQ6Yh16X8nvk3x8Mukjasend"  # BONK token
    
    print(f"🚀 Testing Bundled Helius Sender with Jito Tips")
    print(f"Token: {token_mint_address} (BONK)")
    print("=" * 60)
    
    # Example 1: Buy with bundled Jito tip 
    print("\n💰 Testing Buy with Bundled Jito Tip")
    print("-" * 40)
    
    result = raydium.buy_with_helius_sender(
        token_mint_address=token_mint_address,
        sol_in=0.001,  # Small amount for testing
        slippage=15,
        tip_amount=1000000  # 0.001 SOL tip bundled into transaction
    )
    
    if result["success"]:
        print(f"✅ Buy transaction successful!")
        print(f"   Signature: {result['signature']}")
        print(f"   Method: {result['method']}")
        print(f"   Confirmed: {result.get('confirmed', 'Unknown')}")
        print(f"   Final Balance: {result.get('final_balance', 'Unknown')}")
        print(f"   Tip Amount: {result['tip_amount']} lamports")
    else:
        print(f"❌ Buy transaction failed: {result.get('error')}")
    
    # Skip the other tests for now to focus on one successful transaction
    print("\n" + "=" * 60)
    print("🎯 Enhanced Transaction Features:")
    print("  ✅ Professional provider architecture")
    print("  ✅ Transaction confirmation with SolanaTransactionProvider")
    print("  ✅ Token balance checking with SolanaTokenProvider")
    print("  ✅ Enhanced error handling and logging")
    print("  ✅ Structured result reporting")

if __name__ == "__main__":
    main()