"""
Player class for Texas Hold'em.

Manages player state including:
- Stack (chip count)
- Hole cards
- Current bet in the round
- Player state (active, folded, all-in, out)
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from deeppoker.core.card import Card


class PlayerState(Enum):
    """Player states during a hand."""
    ACTIVE = auto()       # Still in the hand, can act
    FOLDED = auto()       # Has folded
    ALL_IN = auto()       # All-in, no more actions
    OUT = auto()          # Out of the game (no chips)
    SITTING_OUT = auto()  # Temporarily sitting out


@dataclass
class Player:
    """
    A player in the Texas Hold'em game.
    
    Attributes:
        player_id: Unique identifier for the player
        stack: Current chip count
        hole_cards: The player's private cards (2 cards)
        current_bet: Amount bet in the current betting round
        total_bet: Total amount bet in the current hand (for pot calculations)
        state: Current player state
        seat: Seat position at the table (0-indexed)
    """
    player_id: str
    stack: int
    seat: int = 0
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: int = 0
    total_bet: int = 0
    state: PlayerState = PlayerState.ACTIVE
    
    # Track if player has acted in current round (for betting round completion)
    has_acted: bool = False
    # Track last action for display
    last_action: Optional[str] = None
    
    def reset_for_new_hand(self) -> None:
        """Reset player state for a new hand."""
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet = 0
        self.has_acted = False
        self.last_action = None
        
        # Only reset to ACTIVE if player has chips
        if self.stack > 0:
            self.state = PlayerState.ACTIVE
        else:
            self.state = PlayerState.OUT
    
    def reset_for_new_round(self) -> None:
        """Reset player state for a new betting round (flop, turn, river)."""
        self.current_bet = 0
        self.has_acted = False
        
        # Keep state as ALL_IN if already all-in
        if self.state == PlayerState.ALL_IN:
            self.has_acted = True  # All-in players don't act
    
    def deal_cards(self, cards: List[Card]) -> None:
        """Deal hole cards to the player."""
        self.hole_cards = cards
    
    def bet(self, amount: int) -> int:
        """
        Place a bet.
        
        Args:
            amount: Amount to bet
            
        Returns:
            Actual amount bet (may be less if all-in)
        """
        if amount <= 0:
            return 0
            
        # Can't bet more than stack
        actual_amount = min(amount, self.stack)
        
        self.stack -= actual_amount
        self.current_bet += actual_amount
        self.total_bet += actual_amount
        
        # Check if all-in
        if self.stack == 0:
            self.state = PlayerState.ALL_IN
        
        return actual_amount
    
    def fold(self) -> None:
        """Fold the hand."""
        self.state = PlayerState.FOLDED
        self.last_action = "FOLD"
    
    def check(self) -> None:
        """Check (pass without betting)."""
        self.has_acted = True
        self.last_action = "CHECK"
    
    def call(self, amount_to_call: int) -> int:
        """
        Call the current bet.
        
        Args:
            amount_to_call: Amount needed to call
            
        Returns:
            Actual amount called (may be all-in)
        """
        actual = self.bet(amount_to_call)
        self.has_acted = True
        self.last_action = f"CALL ${actual}"
        return actual
    
    def raise_to(self, total_amount: int) -> int:
        """
        Raise to a total amount.
        
        Args:
            total_amount: Total bet amount (including call)
            
        Returns:
            Actual amount added to the pot
        """
        # Calculate how much more to add
        amount_to_add = total_amount - self.current_bet
        actual = self.bet(amount_to_add)
        self.has_acted = True
        
        if self.state == PlayerState.ALL_IN:
            self.last_action = f"ALL-IN ${self.total_bet}"
        else:
            self.last_action = f"RAISE ${self.current_bet}"
        
        return actual
    
    def go_all_in(self) -> int:
        """
        Go all-in.
        
        Returns:
            Total amount bet (previous bet + remaining stack)
        """
        remaining = self.stack
        self.bet(remaining)
        self.has_acted = True
        self.last_action = f"ALL-IN ${self.total_bet}"
        return remaining
    
    @property
    def is_active(self) -> bool:
        """Check if player can still act."""
        return self.state == PlayerState.ACTIVE
    
    @property
    def is_in_hand(self) -> bool:
        """Check if player is still in the hand (not folded, not out)."""
        return self.state in (PlayerState.ACTIVE, PlayerState.ALL_IN)
    
    @property
    def can_act(self) -> bool:
        """Check if player can take an action."""
        return self.state == PlayerState.ACTIVE and self.stack > 0
    
    @property
    def chips_at_stake(self) -> int:
        """Total chips the player has committed to the pot."""
        return self.total_bet
    
    def to_dict(self, hide_cards: bool = True) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Args:
            hide_cards: If True, don't include hole cards
        """
        result = {
            "id": self.player_id,
            "seat": self.seat,
            "stack": self.stack,
            "bet": self.current_bet,
            "total_bet": self.total_bet,
            "state": self.state.name,
            "last_action": self.last_action,
        }
        
        if not hide_cards and self.hole_cards:
            result["cards"] = [card.to_dict() for card in self.hole_cards]
        
        return result
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Get public information (visible to all players)."""
        return self.to_dict(hide_cards=True)
    
    def to_private_dict(self) -> Dict[str, Any]:
        """Get private information (only for this player)."""
        return self.to_dict(hide_cards=False)
    
    def __repr__(self) -> str:
        return (
            f"Player({self.player_id}, stack={self.stack}, "
            f"bet={self.current_bet}, state={self.state.name})"
        )
    
    def __str__(self) -> str:
        cards_str = " ".join(str(c) for c in self.hole_cards) if self.hole_cards else "??"
        return f"Player {self.player_id} [{cards_str}] ${self.stack}"
