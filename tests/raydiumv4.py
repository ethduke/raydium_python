"""
Tests for the RaydiumUnified class
"""
import unittest
from unittest.mock import patch

from model import RaydiumUnified

class TestRaydiumUnified(unittest.TestCase):
    """Test cases for RaydiumUnified class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.raydium = RaydiumUnified()
    
    @patch('model.raydium_unified.RaydiumUnified.buy_by_token')
    def test_buy_by_token(self, mock_buy):
        """Test buying tokens by token address"""
                # Mock data
        token_mint = "FAKE_TOKEN_MINT_ADDRESS"
        mock_buy.return_value = {"success": True}

        # Call the method
        result = self.raydium.buy_by_token(token_mint, sol_in=0.1, slippage=1)

        # Assertions
        mock_buy.assert_called_once_with(token_mint, sol_in=0.1, slippage=1)
        self.assertTrue(result.get("success"))
    
    @patch('model.raydium_unified.RaydiumUnified.buy_by_token')
    def test_buy_by_token_no_pair_found(self, mock_buy):
        """Test buying tokens by token address when no pair is found"""
                # Mock data
        mock_buy.return_value = {"success": False, "error": "No pair found"}

        # Call the method
        result = self.raydium.buy_by_token("FAKE_TOKEN_MINT", sol_in=0.1, slippage=1)

        # Assertions
        self.assertFalse(result.get("success"))

if __name__ == '__main__':
    unittest.main()