"""
Tests for the RaydiumV4 class
"""
import unittest
from unittest.mock import patch, MagicMock

from model.raydium_v4 import RaydiumV4

class TestRaydiumV4(unittest.TestCase):
    """Test cases for RaydiumV4 class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.raydium = RaydiumV4()
    
    @patch('raydium_api.model.raydium_v4.get_amm_v4_pair_from_rpc')
    @patch('raydium_api.model.raydium_v4.RaydiumV4.buy')
    def test_buy_by_token(self, mock_buy, mock_get_pairs):
        """Test buying tokens by token address"""
        # Mock data
        token_mint = "FAKE_TOKEN_MINT_ADDRESS"
        mock_pair_address = "FAKE_PAIR_ADDRESS"
        mock_get_pairs.return_value = [mock_pair_address]
        mock_buy.return_value = True
        
        # Call the method
        result = self.raydium.buy_by_token(token_mint, sol_in=0.1, slippage=1)
        
        # Assertions
        mock_get_pairs.assert_called_once_with(token_mint)
        mock_buy.assert_called_once_with(mock_pair_address, sol_in=0.1, slippage=1)
        self.assertTrue(result)
    
    @patch('raydium_api.model.raydium_v4.get_amm_v4_pair_from_rpc')
    def test_buy_by_token_no_pair_found(self, mock_get_pairs):
        """Test buying tokens by token address when no pair is found"""
        # Mock data
        mock_get_pairs.return_value = []
        
        # Call the method
        result = self.raydium.buy_by_token("FAKE_TOKEN_MINT", sol_in=0.1, slippage=1)
        
        # Assertions
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()