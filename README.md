# raydium_py

Python library to trade on AMM v4, CPMM and CLMM Raydium pools. 

***NOTE: CLMM IS STILL A WORK IN PROGRESS***

solana Version: 0.35.0 | solders Version: 0.21.0

Updated: 12/27/2024


# Instructions

Clone the repo, and add your Private Key (Base58 string) and RPC to the config.py.

**When swapping, you must use the pool id, also known as the pair address. Do not use the mint aka token address.** 

We cannot pass the mint directly because there can be several pools for a single mint.

It is up to the user to fetch the pool ids via the Raydium API or via RPC methods I've included. 


**If you can - please support my work and donate to: 3pPK76GL5ChVFBHND54UfBMtg36Bsh1mzbQPTbcK89PD**


# Contact

My services are for **hire**. 

Contact me if you need help integrating the code into your own project. 

I am not your personal tech support. 

READ THE FAQS BEFORE CONTACTING ME. 

Telegram: @AL_THE_BOT_FATHER


# FAQS

**What format should my private key be in?** 

The private key should be in the base58 string format, not bytes. 

**Why are my transactions being dropped?** 

You get what you pay for. Don't use the main-net RPC, just spend the money for Helius or Quick Node.

**How do I change the fee?** 

Modify the UNIT_BUDGET and UNIT_PRICE in the config.py. 

**Why is this failing for USDC pairs?** 

This code only works for SOL pairs. 

**Why are there "no pool keys found"?** 

IF YOU ARE USING A FREE TIER RPC, THIS REPO WILL NOT WORK FOR YOU. FREE TIER RPCS DO NOT ALLOW GET_ACCOUNT_INFO_PARSED().

**Does this code work on devnet?**

No. 
