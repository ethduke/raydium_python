from .raydium_unified_jito import RaydiumUnifiedJito
from .raydium_launchpad import RaydiumLaunchpad
from utils.pool_utils import get_amm_v4_pair_from_rpc, get_cpmm_pair_address_from_rpc
from utils.pool_utils_launchpad import find_launchpad_pool_by_mint, fetch_launchpad_pool_keys

class RaydiumTrader:
    """Smart pool detection system that checks all available pool types"""
    
    def __init__(self):
        self.raydium_unified = RaydiumUnifiedJito()
        self.raydium_launchpad = RaydiumLaunchpad()
    
    async def detect_all_pool_types(self, token_mint: str):
        """
        Detect all available pool types for a given token mint.
        
        Args:
            token_mint (str): Token mint address to check
            
        Returns:
            dict: Dictionary containing all found pool types and their details
        """
        print(f"\n🔍 Smart Pool Detection for: {token_mint}")
        print("=" * 60)
        
        pool_results = {
            'amm_v4': None,
            'cpmm': None,
            'launchpad': None,
            'recommendation': None
        }
        
        # Check AMM V4 pools
        print("📊 Checking AMM V4 pools...")
        try:
            v4_pairs = get_amm_v4_pair_from_rpc(token_mint)
            if v4_pairs and len(v4_pairs) > 0:
                pool_results['amm_v4'] = {
                    'address': v4_pairs[0],
                    'type': 'AMM V4',
                    'description': 'Traditional Raydium AMM pool'
                }
                print(f"✅ Found AMM V4 pool: {v4_pairs[0]}")
            else:
                print("❌ No AMM V4 pools found")
        except Exception as e:
            print(f"❌ Error checking AMM V4: {e}")
        
        # Check CPMM pools
        print("\n📊 Checking CPMM pools...")
        try:
            cpmm_pairs = get_cpmm_pair_address_from_rpc(token_mint)
            if cpmm_pairs and len(cpmm_pairs) > 0:
                pool_results['cpmm'] = {
                    'address': cpmm_pairs[0],
                    'type': 'CPMM',
                    'description': 'Concentrated liquidity pool'
                }
                print(f"✅ Found CPMM pool: {cpmm_pairs[0]}")
            else:
                print("❌ No CPMM pools found")
        except Exception as e:
            print(f"❌ Error checking CPMM: {e}")
        
        # Check Launchpad pools
        print("\n📊 Checking Launchpad pools...")
        try:
            launchpad_pool_id = await find_launchpad_pool_by_mint(token_mint)
            if launchpad_pool_id:
                pool_keys = await fetch_launchpad_pool_keys(launchpad_pool_id)
                if pool_keys:
                    pool_results['launchpad'] = {
                        'address': launchpad_pool_id,
                        'type': 'Launchpad',
                        'description': 'Raydium Launchpad pool',
                        'status': pool_keys.status,
                        'migrated': pool_keys.status == 2
                    }
                    print(f"✅ Found Launchpad pool: {launchpad_pool_id}")
                    print(f"   Status: {pool_keys.status} ({'Migrated' if pool_keys.status == 2 else 'Active'})")
                else:
                    print("❌ Failed to fetch launchpad pool keys")
            else:
                print("❌ No Launchpad pools found")
        except Exception as e:
            print(f"❌ Error checking Launchpad: {e}")
        
        # Determine recommendation
        pool_results['recommendation'] = self._get_recommendation(pool_results)
        
        return pool_results
    
    def _get_recommendation(self, pool_results):
        """
        Determine the best pool type to use based on availability and characteristics.
        
        Args:
            pool_results (dict): Results from pool detection
            
        Returns:
            dict: Recommendation with pool type and reasoning
        """
        available_pools = []
        
        if pool_results['amm_v4']:
            available_pools.append(('amm_v4', 'AMM V4', 'Traditional AMM with good liquidity'))
        
        if pool_results['cpmm']:
            available_pools.append(('cpmm', 'CPMM', 'Concentrated liquidity for better efficiency'))
        
        if pool_results['launchpad'] and not pool_results['launchpad']['migrated']:
            available_pools.append(('launchpad', 'Launchpad', 'New token launch pool'))
        
        if not available_pools:
            return {
                'type': None,
                'reason': 'No compatible pools found for this token'
            }
        
        # Priority order: Launchpad (if active) > CPMM > AMM V4
        if any(pool[0] == 'launchpad' for pool in available_pools):
            return {
                'type': 'launchpad',
                'reason': 'Active launchpad pool found - best for new tokens',
                'address': pool_results['launchpad']['address']
            }
        elif any(pool[0] == 'cpmm' for pool in available_pools):
            return {
                'type': 'cpmm',
                'reason': 'CPMM pool found - better capital efficiency',
                'address': pool_results['cpmm']['address']
            }
        else:
            return {
                'type': 'amm_v4',
                'reason': 'AMM V4 pool found - traditional trading',
                'address': pool_results['amm_v4']['address']
            }
    
    async def execute_smart_trade(self, token_mint: str, sol_amount: float = 0.01, slippage: int = 5, sell_percentage: int = None):
        """
        Execute a trade using the best available pool type.
        
        Args:
            token_mint (str): Token mint address
            sol_amount (float): Amount of SOL to spend (for buy) or percentage (for sell)
            slippage (int): Slippage tolerance percentage
            sell_percentage (int): If provided, sell this percentage of tokens instead of buying
            
        Returns:
            dict: Trade result
        """
        print(f"\n🚀 Executing Smart Trade")
        print("=" * 40)
        
        # Detect all pool types
        pool_results = await self.detect_all_pool_types(token_mint)
        
        # Display recommendation
        recommendation = pool_results['recommendation']
        print(f"\n💡 Recommendation: {recommendation['type'].upper() if recommendation['type'] else 'None'}")
        print(f"   Reason: {recommendation['reason']}")
        
        if not recommendation['type']:
            return {'success': False, 'error': 'No compatible pools found'}
        
        # Execute trade based on recommendation
        try:
            if recommendation['type'] == 'launchpad':
                if sell_percentage:
                    print(f"\n🔄 Executing Launchpad sell ({sell_percentage}%)...")
                    result = await self.raydium_launchpad.sell_by_token(
                        token_mint=token_mint,
                        percentage=sell_percentage,
                        slippage=slippage
                    )
                else:
                    print(f"\n🔄 Executing Launchpad buy...")
                    result = await self.raydium_launchpad.buy_by_token(
                        token_mint=token_mint,
                        sol_in=sol_amount,
                        slippage=slippage
                    )
                return {'success': result, 'pool_type': 'launchpad'}
            
            elif recommendation['type'] in ['amm_v4', 'cpmm']:
                if sell_percentage:
                    print(f"\n🔄 Executing {recommendation['type'].upper()} sell ({sell_percentage}%)...")
                    result = self.raydium_unified.sell_by_token(
                        token_mint=token_mint,
                        percentage=sell_percentage,
                        slippage=slippage
                    )
                else:
                    print(f"\n🔄 Executing {recommendation['type'].upper()} buy...")
                    result = self.raydium_unified.buy_by_token(
                        token_mint=token_mint,
                        sol_in=sol_amount,
                        slippage=slippage
                    )
                return {'success': result, 'pool_type': recommendation['type']}
            
        except Exception as e:
            return {'success': False, 'error': f'Trade execution failed: {e}'}

