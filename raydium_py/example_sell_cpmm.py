from raydium.cpmm import sell

if __name__ == "__main__":
    pair_address = "6AxkZwBNkbUQJtwYSD28hAqLjqfcXfzSyTUZS3rEnvtu"
    percentage = 100
    slippage = 1
    sell(pair_address, percentage, slippage)