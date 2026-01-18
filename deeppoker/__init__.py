"""
DeepPoker R1 - Texas Hold'em Poker Engine

A standalone Texas Hold'em poker game project with:
- Pure Python game core logic (no external poker dependencies)
- FastAPI + WebSocket server architecture
- AI Agent interface for LLM RL integration

Usage:
    from deeppoker.core import Card, Deck, Player, TexasHoldemGame
    from deeppoker.agents import BaseAgent, RandomAgent
"""

__version__ = "0.1.1"
__codename__ = "R1"  # Reasoning v1

from deeppoker.core.card import Card, Deck
from deeppoker.core.player import Player
from deeppoker.core.game import TexasHoldemGame
from deeppoker.core.hand import HandRank, evaluate_hand

__all__ = [
    "Card",
    "Deck", 
    "Player",
    "TexasHoldemGame",
    "HandRank",
    "evaluate_hand",
    "__version__",
    "__codename__",
]
