from raydium.clmm import sell

if __name__ == "__main__":
    pair_address = "B4Vwozy1FGtp8SELXSXydWSzavPUGnJ77DURV2k4MhUV" # PENGU/SOL
    percentage = 100
    # no slippage on clmm
    sell(pair_address, percentage)