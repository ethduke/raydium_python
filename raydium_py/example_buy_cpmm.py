from raydium.cpmm import buy

if __name__ == "__main__":
    pair_address = "CpoYFgaNA6MJRuJSGeXu9mPdghmtwd5RvYesgej4Zofj" # PURPE/SOL
    sol_in = .25
    slippage = 5
    buy(pair_address, sol_in, slippage)