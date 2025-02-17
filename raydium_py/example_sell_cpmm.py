from raydium.cpmm import sell

if __name__ == "__main__":
    pair_address = "CpoYFgaNA6MJRuJSGeXu9mPdghmtwd5RvYesgej4Zofj" # PURPE/SOL
    percentage = 100
    slippage = 5
    sell(pair_address, percentage, slippage)