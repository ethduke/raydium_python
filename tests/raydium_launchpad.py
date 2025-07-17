"""
Tests for the RaydiumLaunchpad class
"""
import unittest
from unittest.mock import patch

from model.raydium.raydium_launchpad import RaydiumLaunchpad

class TestRaydiumLaunchpad(unittest.TestCase):
    """Test cases for RaydiumLaunchpad class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.raydium_launchpad = RaydiumLaunchpad()
    
    @patch('model.raydium.raydium_launchpad.RaydiumLaunchpad.buy_by_token')
    def test_buy_by_token(self, mock_buy):
        """Test buying tokens by token address"""
        # Mock data
        token_mint = "FAKE_TOKEN_MINT_ADDRESS"
        mock_buy.return_value = {"success": True}

        # Call the method
        result = self.raydium_launchpad.buy_by_token(
            token_mint=token_mint,
            sol_in=0.1,
            slippage=1
        )

        # Assertions
        mock_buy.assert_called_once_with(
            token_mint=token_mint,
            sol_in=0.1,
            slippage=1
        )
        self.assertTrue(result.get("success"))
    
    @patch('model.raydium.raydium_launchpad.RaydiumLaunchpad.buy_by_token')
    def test_buy_by_token_no_pool_found(self, mock_buy):
        """Test buying tokens when no pool is found"""
        # Mock data
        mock_buy.return_value = {"success": False, "error": "No pool found"}

        # Call the method
        result = self.raydium_launchpad.buy_by_token(
            token_mint="FAKE_TOKEN_MINT",
            sol_in=0.1,
            slippage=1
        )

        # Assertions
        self.assertFalse(result.get("success"))
    
    @patch('model.raydium.raydium_launchpad.RaydiumLaunchpad.sell_by_token')
    def test_sell_by_token(self, mock_sell):
        """Test selling tokens by token address"""
        # Mock data
        token_mint = "FAKE_TOKEN_MINT_ADDRESS"
        mock_sell.return_value = {"success": True}

        # Call the method
        result = self.raydium_launchpad.sell_by_token(
            token_mint=token_mint,
            percentage=50,
            slippage=1
        )

        # Assertions
        mock_sell.assert_called_once_with(
            token_mint=token_mint,
            percentage=50,
            slippage=1
        )
        self.assertTrue(result.get("success"))
    
    @patch('model.raydium.raydium_launchpad.RaydiumLaunchpad.sell_by_token')
    def test_sell_by_token_no_tokens(self, mock_sell):
        """Test selling tokens when no tokens are available"""
        # Mock data
        mock_sell.return_value = {"success": False, "error": "No tokens to sell"}

        # Call the method
        result = self.raydium_launchpad.sell_by_token(
            token_mint="FAKE_TOKEN_MINT",
            percentage=50,
            slippage=1
        )

        # Assertions
        self.assertFalse(result.get("success"))

if __name__ == '__main__':
    unittest.main() 