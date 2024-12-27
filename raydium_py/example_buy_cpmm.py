from raydium.cpmm import buy

if __name__ == "__main__":
    pair_address = "6AxkZwBNkbUQJtwYSD28hAqLjqfcXfzSyTUZS3rEnvtu"
    sol_in = 0.1
    slippage = 1
    buy(pair_address, sol_in, slippage)