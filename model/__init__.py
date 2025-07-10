"""
Raydium Trading Bot - Model Package

This package provides a complete trading infrastructure for Raydium DEX with:
- Abstract interfaces for extensibility
- Solana blockchain providers
- Raydium-specific trading implementations

Directory Structure:
- interfaces/: Abstract base classes
- providers/: Solana blockchain implementations
- raydium/: Raydium DEX specific classes
"""

# Import all interfaces
from .interfaces import APIProvider, TokenProvider, TransactionProvider

# Import all providers
from .providers import SolanaProvider, SolanaTokenProvider, SolanaTransactionProvider

# Import all raydium implementations
from .raydium import RaydiumUnified, RaydiumUnifiedJito, RaydiumAPI, HeliusSenderClient

# Convenience imports for backwards compatibility
__all__ = [
    # Abstract interfaces
    'APIProvider',
    'TokenProvider',
    'TransactionProvider',
    
    # Solana providers
    'SolanaProvider',
    'SolanaTokenProvider',
    'SolanaTransactionProvider',
    
    # Raydium implementations
    'RaydiumUnified',
    'RaydiumUnifiedJito',
    'RaydiumAPI',
    'HeliusSenderClient',
] 