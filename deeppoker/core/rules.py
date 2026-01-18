"""
Texas Hold'em Rules and Constants.

This module defines the official rules based on WSOP (World Series of Poker)
Tournament Rules. Key rules verified:

1. Heads-up (2 players): Dealer posts small blind, non-dealer posts big blind.
   Preflop: Dealer acts first. Postflop: Non-dealer acts first.
   
2. Minimum raise: The minimum raise amount must be at least equal to the
   previous raise amount (not just the big blind).
   
3. All-in less than minimum raise: If a player goes all-in for less than
   a full raise, action is reopened only for players who haven't acted
   since the short all-in.
   
4. Side pots: When multiple players are all-in for different amounts,
   separate pots are created for each stack level.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Tuple


class GamePhase(Enum):
    """Phases of a Texas Hold'em hand."""
    WAITING = auto()      # Waiting for hand to start
    PREFLOP = auto()      # After hole cards dealt, before flop
    FLOP = auto()         # After 3 community cards
    TURN = auto()         # After 4th community card
    RIVER = auto()        # After 5th community card
    SHOWDOWN = auto()     # Determine winner
    HAND_OVER = auto()    # Hand is complete


class ActionType(Enum):
    """Possible player actions."""
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    BET = "BET"
    RAISE = "RAISE"
    ALL_IN = "ALL_IN"


class PlayerState(Enum):
    """Player states during a hand."""
    ACTIVE = auto()       # Still in the hand, can act
    FOLDED = auto()       # Has folded
    ALL_IN = auto()       # All-in, no more actions
    OUT = auto()          # Out of the game (no chips)
    SITTING_OUT = auto()  # Temporarily sitting out


@dataclass
class BlindStructure:
    """Blind structure for a game."""
    small_blind: int
    big_blind: int
    ante: int = 0  # Optional ante per player


# Default game settings
DEFAULT_SMALL_BLIND = 10
DEFAULT_BIG_BLIND = 20
DEFAULT_BUY_IN = 1000
DEFAULT_MAX_PLAYERS = 10
MIN_PLAYERS = 2
MAX_PLAYERS = 10

# Cards per phase
HOLE_CARDS = 2
FLOP_CARDS = 3
TURN_CARDS = 1
RIVER_CARDS = 1
TOTAL_COMMUNITY_CARDS = 5

# Hand evaluation
HAND_SIZE = 5  # Best 5-card hand


class PositionName(Enum):
    """Named positions at the poker table."""
    DEALER = "BTN"        # Button (Dealer)
    SMALL_BLIND = "SB"    # Small Blind
    BIG_BLIND = "BB"      # Big Blind
    UNDER_THE_GUN = "UTG" # First to act preflop
    HIJACK = "HJ"         # 2 seats before button
    CUTOFF = "CO"         # 1 seat before button


def get_blind_positions(num_players: int, dealer_position: int) -> Tuple[int, int]:
    """
    Calculate small blind and big blind positions.
    
    WSOP Rule: In heads-up play, the dealer posts the small blind.
    
    Args:
        num_players: Number of active players
        dealer_position: Position of the dealer (0-indexed)
        
    Returns:
        Tuple of (small_blind_position, big_blind_position)
    """
    if num_players < 2:
        raise ValueError("Need at least 2 players")
    
    if num_players == 2:
        # Heads-up: Dealer is small blind
        sb_pos = dealer_position
        bb_pos = (dealer_position + 1) % num_players
    else:
        # Standard: SB is left of dealer, BB is left of SB
        sb_pos = (dealer_position + 1) % num_players
        bb_pos = (dealer_position + 2) % num_players
    
    return sb_pos, bb_pos


def get_first_to_act_preflop(num_players: int, dealer_position: int) -> int:
    """
    Get the position of the first player to act preflop.
    
    WSOP Rule: 
    - Heads-up: Dealer (small blind) acts first preflop
    - Otherwise: UTG (left of big blind) acts first
    
    Args:
        num_players: Number of active players
        dealer_position: Position of the dealer
        
    Returns:
        Position of first player to act
    """
    if num_players == 2:
        # Heads-up: Dealer acts first preflop
        return dealer_position
    else:
        # UTG: Left of big blind
        return (dealer_position + 3) % num_players


def get_first_to_act_postflop(num_players: int, dealer_position: int) -> int:
    """
    Get the position of the first player to act postflop.
    
    WSOP Rule: First active player left of the dealer acts first.
    In heads-up, this is the non-dealer (big blind).
    
    Args:
        num_players: Number of active players  
        dealer_position: Position of the dealer
        
    Returns:
        Position of first player to act
    """
    # Always the player left of dealer (small blind in multi-way, BB in heads-up)
    return (dealer_position + 1) % num_players


def calculate_min_raise(
    current_bet: int,
    last_raise_amount: int,
    big_blind: int
) -> int:
    """
    Calculate the minimum raise amount.
    
    WSOP Rule: The minimum raise must be at least equal to the previous
    raise amount. If no raise has occurred, the minimum raise is the big blind.
    
    Args:
        current_bet: Current highest bet in the round
        last_raise_amount: The size of the last raise (the increase, not total)
        big_blind: Big blind amount
        
    Returns:
        Minimum total bet amount (including call + raise)
    """
    min_raise_increment = max(last_raise_amount, big_blind)
    return current_bet + min_raise_increment


def is_valid_raise(
    raise_total: int,
    current_bet: int,
    last_raise_amount: int,
    big_blind: int,
    player_stack: int
) -> bool:
    """
    Check if a raise amount is valid.
    
    A raise is valid if:
    1. It's at least the minimum raise, OR
    2. It's an all-in (player bets their entire stack)
    
    Args:
        raise_total: Total bet amount (not just the raise increment)
        current_bet: Current highest bet
        last_raise_amount: The size of the last raise
        big_blind: Big blind amount
        player_stack: Player's remaining stack
        
    Returns:
        True if the raise is valid
    """
    # All-in is always valid
    if raise_total >= player_stack:
        return True
    
    min_raise = calculate_min_raise(current_bet, last_raise_amount, big_blind)
    return raise_total >= min_raise


def is_action_reopened(
    all_in_amount: int,
    current_bet: int,
    last_raise_amount: int,
    big_blind: int
) -> bool:
    """
    Check if an all-in reopens the action.
    
    WSOP Rule: An all-in bet/raise that is less than a full raise does NOT
    reopen the betting for players who have already acted.
    
    Args:
        all_in_amount: The all-in bet amount
        current_bet: Current highest bet
        last_raise_amount: The size of the last raise
        big_blind: Big blind amount
        
    Returns:
        True if the all-in reopens action for all players
    """
    min_raise = calculate_min_raise(current_bet, last_raise_amount, big_blind)
    return all_in_amount >= min_raise
