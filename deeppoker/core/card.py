"""
Card and Deck classes for Texas Hold'em.

Card representation uses a compact integer encoding for fast hand evaluation,
while providing human-readable string representations.

Reference: Similar to texasholdem library's approach but with clearer API.
"""

from __future__ import annotations
import random
from typing import List, Optional, Tuple
from enum import IntEnum


class Suit(IntEnum):
    """Card suits with integer values for fast comparison."""
    CLUBS = 0     # ♣
    DIAMONDS = 1  # ♦
    HEARTS = 2    # ♥
    SPADES = 3    # ♠


class Rank(IntEnum):
    """Card ranks from 2 (lowest) to Ace (highest)."""
    TWO = 0
    THREE = 1
    FOUR = 2
    FIVE = 3
    SIX = 4
    SEVEN = 5
    EIGHT = 6
    NINE = 7
    TEN = 8
    JACK = 9
    QUEEN = 10
    KING = 11
    ACE = 12


# String mappings
SUIT_SYMBOLS = {
    Suit.CLUBS: "♣",
    Suit.DIAMONDS: "♦", 
    Suit.HEARTS: "♥",
    Suit.SPADES: "♠",
}

SUIT_CHARS = {
    Suit.CLUBS: "c",
    Suit.DIAMONDS: "d",
    Suit.HEARTS: "h",
    Suit.SPADES: "s",
}

RANK_CHARS = {
    Rank.TWO: "2",
    Rank.THREE: "3",
    Rank.FOUR: "4",
    Rank.FIVE: "5",
    Rank.SIX: "6",
    Rank.SEVEN: "7",
    Rank.EIGHT: "8",
    Rank.NINE: "9",
    Rank.TEN: "T",
    Rank.JACK: "J",
    Rank.QUEEN: "Q",
    Rank.KING: "K",
    Rank.ACE: "A",
}

# Reverse mappings
CHAR_TO_RANK = {v: k for k, v in RANK_CHARS.items()}
CHAR_TO_RANK["10"] = Rank.TEN  # Also accept "10"
CHAR_TO_SUIT = {v: k for k, v in SUIT_CHARS.items()}
SYMBOL_TO_SUIT = {v: k for k, v in SUIT_SYMBOLS.items()}


class Card:
    """
    A playing card represented as (rank, suit).
    
    Cards can be created from:
    - Rank and Suit enums: Card(Rank.ACE, Suit.SPADES)
    - String notation: Card.from_string("As") or Card.from_string("A♠")
    - Integer (0-51): Card.from_int(51) = Ace of Spades
    
    The integer encoding is: card_int = rank * 4 + suit
    This allows for fast comparison and evaluation.
    """
    
    __slots__ = ("rank", "suit", "_int")
    
    def __init__(self, rank: Rank, suit: Suit):
        self.rank = Rank(rank)
        self.suit = Suit(suit)
        self._int = int(self.rank) * 4 + int(self.suit)
    
    @classmethod
    def from_string(cls, s: str) -> Card:
        """
        Create a card from string notation.
        
        Accepts formats:
        - "As", "Kh", "Td", "2c" (rank + suit char)
        - "A♠", "K♥", "T♦", "2♣" (rank + suit symbol)
        """
        s = s.strip()
        if len(s) < 2:
            raise ValueError(f"Invalid card string: {s}")
        
        rank_char = s[0].upper()
        suit_part = s[1:]
        
        if rank_char not in CHAR_TO_RANK:
            raise ValueError(f"Invalid rank: {rank_char}")
        
        rank = CHAR_TO_RANK[rank_char]
        
        # Try suit char first, then symbol
        if suit_part.lower() in CHAR_TO_SUIT:
            suit = CHAR_TO_SUIT[suit_part.lower()]
        elif suit_part in SYMBOL_TO_SUIT:
            suit = SYMBOL_TO_SUIT[suit_part]
        else:
            raise ValueError(f"Invalid suit: {suit_part}")
        
        return cls(rank, suit)
    
    @classmethod
    def from_int(cls, card_int: int) -> Card:
        """Create a card from integer (0-51)."""
        if not 0 <= card_int <= 51:
            raise ValueError(f"Card int must be 0-51, got {card_int}")
        rank = Rank(card_int // 4)
        suit = Suit(card_int % 4)
        return cls(rank, suit)
    
    def to_int(self) -> int:
        """Return the integer representation (0-51)."""
        return self._int
    
    def __int__(self) -> int:
        return self._int
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Card):
            return self._int == other._int
        return False
    
    def __hash__(self) -> int:
        return self._int
    
    def __lt__(self, other: Card) -> bool:
        """Compare by rank only (for sorting)."""
        return self.rank < other.rank
    
    def __repr__(self) -> str:
        return f"Card({RANK_CHARS[self.rank]}{SUIT_CHARS[self.suit]})"
    
    def __str__(self) -> str:
        return f"{RANK_CHARS[self.rank]}{SUIT_SYMBOLS[self.suit]}"
    
    @property
    def short_str(self) -> str:
        """Short string like 'As', 'Kh'."""
        return f"{RANK_CHARS[self.rank]}{SUIT_CHARS[self.suit]}"
    
    @property
    def pretty_str(self) -> str:
        """Pretty string like '[ A ♠ ]'."""
        return f"[ {RANK_CHARS[self.rank]} {SUIT_SYMBOLS[self.suit]} ]"
    
    @property
    def color(self) -> str:
        """Return 'red' for hearts/diamonds, 'black' for clubs/spades."""
        return "red" if self.suit in (Suit.HEARTS, Suit.DIAMONDS) else "black"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "rank": RANK_CHARS[self.rank],
            "suit": SUIT_SYMBOLS[self.suit],
            "text": str(self),
            "color": self.color,
        }


class Deck:
    """
    A standard 52-card deck.
    
    Usage:
        deck = Deck()
        deck.shuffle()
        hole_cards = deck.deal(2)
        flop = deck.deal(3)
    """
    
    def __init__(self, shuffle: bool = True):
        """Initialize a new deck, optionally shuffled."""
        self.reset()
        if shuffle:
            self.shuffle()
    
    def reset(self) -> None:
        """Reset the deck to a full 52 cards in order."""
        self._cards: List[Card] = [
            Card(rank, suit)
            for rank in Rank
            for suit in Suit
        ]
        self._dealt: List[Card] = []
    
    def shuffle(self) -> None:
        """Shuffle the remaining cards in the deck."""
        random.shuffle(self._cards)
    
    def deal(self, n: int = 1) -> List[Card]:
        """
        Deal n cards from the top of the deck.
        
        Raises:
            ValueError: If not enough cards remain.
        """
        if n > len(self._cards):
            raise ValueError(f"Cannot deal {n} cards, only {len(self._cards)} remain")
        
        dealt = self._cards[:n]
        self._cards = self._cards[n:]
        self._dealt.extend(dealt)
        return dealt
    
    def deal_one(self) -> Card:
        """Deal a single card."""
        return self.deal(1)[0]
    
    def burn(self) -> Card:
        """Burn (discard) the top card."""
        return self.deal_one()
    
    @property
    def remaining(self) -> int:
        """Number of cards remaining in the deck."""
        return len(self._cards)
    
    @property
    def dealt_cards(self) -> List[Card]:
        """List of cards that have been dealt."""
        return self._dealt.copy()
    
    def __len__(self) -> int:
        return len(self._cards)
    
    def __repr__(self) -> str:
        return f"Deck({self.remaining} cards remaining)"


def parse_cards(cards_str: str) -> List[Card]:
    """
    Parse multiple cards from a string.
    
    Accepts formats:
    - "As Kh Td" (space-separated)
    - "AsKhTd" (no separator, 2 chars each)
    - "A♠ K♥ T♦" (with symbols)
    
    Returns:
        List of Card objects
    """
    cards_str = cards_str.strip()
    
    # Try space-separated first
    if " " in cards_str:
        return [Card.from_string(s) for s in cards_str.split()]
    
    # Try 2-char chunks
    result = []
    i = 0
    while i < len(cards_str):
        # Check for symbol (unicode char)
        if i + 1 < len(cards_str) and cards_str[i + 1] in SYMBOL_TO_SUIT:
            result.append(Card.from_string(cards_str[i:i+2]))
            i += 2
        elif i + 1 < len(cards_str) and cards_str[i + 1].lower() in CHAR_TO_SUIT:
            result.append(Card.from_string(cards_str[i:i+2]))
            i += 2
        else:
            raise ValueError(f"Cannot parse card at position {i}: {cards_str[i:]}")
    
    return result
