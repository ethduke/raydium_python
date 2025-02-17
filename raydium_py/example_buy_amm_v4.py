from raydium.amm_v4 import buy

if __name__ == "__main__":
    pair_address = "FRhB8L7Y9Qq41qZXYLtC2nw8An1RJfLLxRF2x9RwLLMo" # POPCAT/SOL
    sol_in = .25
    slippage = 5
    buy(pair_address, sol_in, slippage)