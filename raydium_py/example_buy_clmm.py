from raydium.clmm import buy

if __name__ == "__main__":
    pair_address = "B4Vwozy1FGtp8SELXSXydWSzavPUGnJ77DURV2k4MhUV" # PENGU/SOL
    sol_in = .25
    # no slippage on clmm
    buy(pair_address, sol_in)
