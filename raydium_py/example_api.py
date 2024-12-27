from utils.api import get_pool_info_by_id, get_pool_info_by_mint

def main():
    pool_id = "5phQt8oA1fwKDq1pLJ2E2swozfs7dgDH78iLuoUjAYhM"
    pool_info = get_pool_info_by_id(pool_id)

    if 'data' in pool_info and pool_info['data']:
        pool = pool_info['data'][0]
        print(f"Pool Info for: {pool_id}")
        print(f" - Pool ID: {pool.get('id', 'N/A')}")
        print(f" - Mint A Address: {pool['mintA'].get('address', 'N/A')}")
        print(f" - Mint B Address: {pool['mintB'].get('address', 'N/A')}")
    else:
        print("No data found for the given pool ID.")

    print("------------------------------------")

    mint = "5DQSDg6SGkbsbykq4mQstpcL4d5raEHc6rY7LgBwpump"
    pool_info = get_pool_info_by_mint(mint)

    if 'data' in pool_info and 'data' in pool_info['data']:
        print(f"Pools for Mint: {mint}")
        for pool in pool_info['data']['data']:
            print(f" - Type: {pool.get('type', 'N/A')} | Pool ID: {pool.get('id', 'N/A')}")
    else:
        print(f"No pools found for the mint address: {mint}")

if __name__ == "__main__":
    main()
