from raydium.amm_v4 import sell

if __name__ == "__main__":
    pair_address = "FRhB8L7Y9Qq41qZXYLtC2nw8An1RJfLLxRF2x9RwLLMo"
    percentage = 100
    slippage = 1
    sell(pair_address, percentage, slippage)