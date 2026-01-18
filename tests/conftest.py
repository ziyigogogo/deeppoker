"""
Pytest configuration and shared fixtures for DeepPoker tests.
"""

import pytest
from deeppoker.core.card import Card, Deck, Rank, Suit
from deeppoker.core.player import Player
from deeppoker.core.game import TexasHoldemGame


@pytest.fixture
def deck():
    """Create a fresh shuffled deck."""
    return Deck(shuffle=True)


@pytest.fixture
def unshuffled_deck():
    """Create a fresh unshuffled deck."""
    return Deck(shuffle=False)


@pytest.fixture
def sample_player():
    """Create a sample player with 1000 chips."""
    return Player(player_id="test_player", stack=1000, seat=0)


@pytest.fixture
def two_player_game():
    """Create a 2-player game (heads-up)."""
    return TexasHoldemGame(
        num_players=2,
        big_blind=20,
        small_blind=10,
        buy_in=1000,
    )


@pytest.fixture
def six_player_game():
    """Create a 6-player game."""
    return TexasHoldemGame(
        num_players=6,
        big_blind=20,
        small_blind=10,
        buy_in=1000,
    )


@pytest.fixture
def sample_hand():
    """Create a sample 5-card hand (pair of aces)."""
    return [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.KING, Suit.DIAMONDS),
        Card(Rank.QUEEN, Suit.CLUBS),
        Card(Rank.JACK, Suit.SPADES),
    ]


@pytest.fixture
def royal_flush():
    """Create a royal flush hand."""
    return [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.QUEEN, Suit.SPADES),
        Card(Rank.JACK, Suit.SPADES),
        Card(Rank.TEN, Suit.SPADES),
    ]


@pytest.fixture
def straight_flush():
    """Create a straight flush (9-high)."""
    return [
        Card(Rank.NINE, Suit.HEARTS),
        Card(Rank.EIGHT, Suit.HEARTS),
        Card(Rank.SEVEN, Suit.HEARTS),
        Card(Rank.SIX, Suit.HEARTS),
        Card(Rank.FIVE, Suit.HEARTS),
    ]


@pytest.fixture
def wheel_straight():
    """Create a wheel straight (A-2-3-4-5)."""
    return [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.TWO, Suit.HEARTS),
        Card(Rank.THREE, Suit.DIAMONDS),
        Card(Rank.FOUR, Suit.CLUBS),
        Card(Rank.FIVE, Suit.SPADES),
    ]
