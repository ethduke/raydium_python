#!/usr/bin/env python3
"""
Example script demonstrating how to use the Raydium API
"""

from model.raydium_v4 import RaydiumV4

def main():
    # Initialize the Raydium client
    raydium = RaydiumV4()
    
    # Replace with a real token mint address COCORO
    token_mint_address = "5SJ7tGwtTaB27xNnZoayvieVHr68d6ARZ8MT64Knpump"
    
    # Example 1: Query information about a token
    print(f"Looking up trading pairs for token: {token_mint_address}")
    
    # Example 2: Buy a token using its mint address
    # Uncomment the line below and replace the token_mint_address to execute a real trade
    #success = raydium.buy_by_token(token_mint_address, 
    #                               sol_in=0.001, 
    #                               slippage=1)
    
    #print(f"Buy transaction successful: {success}")
    
    # Example 3: Sell a token using its mint address
    # Uncomment the line below and replace the token_mint_address to execute a real trade
    success = raydium.sell_by_token(token_mint_address, 
                                    percentage=50, 
                                    slippage=1)
    print(f"Sell transaction successful: {success}")

if __name__ == "__main__":
    main()