"""
Hand Evaluation for Texas Hold'em.

This module evaluates 5-7 cards and returns the best 5-card hand rank.
The rank system uses a number from 1 (Royal Flush) to 7462 (worst high card),
allowing simple comparison: lower rank = better hand.

Hand Rankings (best to worst):
1. Royal Flush: A♠ K♠ Q♠ J♠ T♠
2. Straight Flush: 5 consecutive cards of same suit
3. Four of a Kind: 4 cards of same rank
4. Full House: 3 of a kind + pair
5. Flush: 5 cards of same suit
6. Straight: 5 consecutive cards
7. Three of a Kind: 3 cards of same rank
8. Two Pair: 2 different pairs
9. One Pair: 2 cards of same rank
10. High Card: No made hand

Note: Ace can be low in A-2-3-4-5 straight (wheel).
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Optional
from itertools import combinations
from enum import IntEnum
from collections import Counter

from deeppoker.core.card import Card, Rank, Suit


class HandRank(IntEnum):
    """Hand rankings from best (highest value) to worst (lowest value)."""
    ROYAL_FLUSH = 10
    STRAIGHT_FLUSH = 9
    FOUR_OF_A_KIND = 8
    FULL_HOUSE = 7
    FLUSH = 6
    STRAIGHT = 5
    THREE_OF_A_KIND = 4
    TWO_PAIR = 3
    ONE_PAIR = 2
    HIGH_CARD = 1


# Hand rank names for display
HAND_RANK_NAMES = {
    HandRank.ROYAL_FLUSH: "Royal Flush",
    HandRank.STRAIGHT_FLUSH: "Straight Flush",
    HandRank.FOUR_OF_A_KIND: "Four of a Kind",
    HandRank.FULL_HOUSE: "Full House",
    HandRank.FLUSH: "Flush",
    HandRank.STRAIGHT: "Straight",
    HandRank.THREE_OF_A_KIND: "Three of a Kind",
    HandRank.TWO_PAIR: "Two Pair",
    HandRank.ONE_PAIR: "One Pair",
    HandRank.HIGH_CARD: "High Card",
}


# Multiplier for hand rank to ensure better hands always have lower final rank
# Final rank = (10 - hand_rank) * RANK_MULTIPLIER + kicker_value
# This ensures Royal Flush (10) -> 0*M, High Card (1) -> 9*M
RANK_MULTIPLIER = 1000000


def evaluate_hand(cards: List[Card]) -> Tuple[int, HandRank, List[Card]]:
    """
    Evaluate a poker hand (5-7 cards).
    
    Args:
        cards: List of 5-7 Card objects
        
    Returns:
        Tuple of:
        - rank: Integer rank from 1 (Royal Flush) to 7462 (worst high card)
                Lower is better.
        - hand_type: HandRank enum value
        - best_cards: The 5 cards that make the best hand
        
    Raises:
        ValueError: If not 5-7 cards provided
    """
    if len(cards) < 5 or len(cards) > 7:
        raise ValueError(f"Need 5-7 cards, got {len(cards)}")
    
    # If exactly 5 cards, evaluate directly
    if len(cards) == 5:
        return _evaluate_5_cards(cards)
    
    # For 6-7 cards, find the best 5-card combination
    best_rank = float('inf')
    best_hand_type = HandRank.HIGH_CARD
    best_cards = []
    
    for combo in combinations(cards, 5):
        rank, hand_type, _ = _evaluate_5_cards(list(combo))
        if rank < best_rank:
            best_rank = rank
            best_hand_type = hand_type
            best_cards = list(combo)
    
    return best_rank, best_hand_type, best_cards


def _evaluate_5_cards(cards: List[Card]) -> Tuple[int, HandRank, List[Card]]:
    """Evaluate exactly 5 cards."""
    assert len(cards) == 5
    
    # Sort by rank descending
    sorted_cards = sorted(cards, key=lambda c: c.rank, reverse=True)
    ranks = [c.rank for c in sorted_cards]
    suits = [c.suit for c in sorted_cards]
    
    # Check for flush (all same suit)
    is_flush = len(set(suits)) == 1
    
    # Check for straight
    is_straight, straight_high = _check_straight(ranks)
    
    # Count rank occurrences
    rank_counts = Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)
    
    # Determine hand type
    if is_straight and is_flush:
        if straight_high == Rank.ACE:
            hand_type = HandRank.ROYAL_FLUSH
            rank = _calculate_rank(hand_type, [Rank.ACE])
        else:
            hand_type = HandRank.STRAIGHT_FLUSH
            # Rank by high card of straight
            rank = _calculate_rank(hand_type, [straight_high])
        return rank, hand_type, sorted_cards
    
    if counts == [4, 1]:  # Four of a kind
        hand_type = HandRank.FOUR_OF_A_KIND
        quad_rank = _get_rank_with_count(rank_counts, 4)
        kicker = _get_rank_with_count(rank_counts, 1)
        rank = _calculate_rank(hand_type, [quad_rank, kicker])
        # Sort cards: quads first, then kicker
        sorted_cards = _sort_by_count(sorted_cards, rank_counts)
        return rank, hand_type, sorted_cards
    
    if counts == [3, 2]:  # Full house
        hand_type = HandRank.FULL_HOUSE
        trips_rank = _get_rank_with_count(rank_counts, 3)
        pair_rank = _get_rank_with_count(rank_counts, 2)
        rank = _calculate_rank(hand_type, [trips_rank, pair_rank])
        sorted_cards = _sort_by_count(sorted_cards, rank_counts)
        return rank, hand_type, sorted_cards
    
    if is_flush:
        hand_type = HandRank.FLUSH
        rank = _calculate_high_card_rank(hand_type, ranks)
        return rank, hand_type, sorted_cards
    
    if is_straight:
        hand_type = HandRank.STRAIGHT
        rank = _calculate_rank(hand_type, [straight_high])
        # For wheel (A-2-3-4-5), reorder cards
        if straight_high == Rank.FIVE:
            sorted_cards = _reorder_wheel(sorted_cards)
        return rank, hand_type, sorted_cards
    
    if counts == [3, 1, 1]:  # Three of a kind
        hand_type = HandRank.THREE_OF_A_KIND
        trips_rank = _get_rank_with_count(rank_counts, 3)
        kickers = sorted([r for r, c in rank_counts.items() if c == 1], reverse=True)
        rank = _calculate_rank(hand_type, [trips_rank] + kickers)
        sorted_cards = _sort_by_count(sorted_cards, rank_counts)
        return rank, hand_type, sorted_cards
    
    if counts == [2, 2, 1]:  # Two pair
        hand_type = HandRank.TWO_PAIR
        pairs = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
        kicker = _get_rank_with_count(rank_counts, 1)
        rank = _calculate_rank(hand_type, pairs + [kicker])
        sorted_cards = _sort_by_count(sorted_cards, rank_counts)
        return rank, hand_type, sorted_cards
    
    if counts == [2, 1, 1, 1]:  # One pair
        hand_type = HandRank.ONE_PAIR
        pair_rank = _get_rank_with_count(rank_counts, 2)
        kickers = sorted([r for r, c in rank_counts.items() if c == 1], reverse=True)
        rank = _calculate_rank(hand_type, [pair_rank] + kickers)
        sorted_cards = _sort_by_count(sorted_cards, rank_counts)
        return rank, hand_type, sorted_cards
    
    # High card
    hand_type = HandRank.HIGH_CARD
    rank = _calculate_high_card_rank(hand_type, ranks)
    return rank, hand_type, sorted_cards


def _check_straight(ranks: List[Rank]) -> Tuple[bool, Optional[Rank]]:
    """
    Check if sorted ranks form a straight.
    
    Returns:
        Tuple of (is_straight, high_card_rank)
    """
    unique_ranks = sorted(set(ranks), reverse=True)
    if len(unique_ranks) != 5:
        return False, None
    
    # Check regular straight
    if unique_ranks[0] - unique_ranks[4] == 4:
        return True, unique_ranks[0]
    
    # Check wheel (A-2-3-4-5)
    if unique_ranks == [Rank.ACE, Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO]:
        return True, Rank.FIVE  # 5-high straight
    
    return False, None


def _get_rank_with_count(rank_counts: Counter, count: int) -> Rank:
    """Get the rank that appears 'count' times."""
    for rank, c in rank_counts.items():
        if c == count:
            return rank
    raise ValueError(f"No rank with count {count}")


def _sort_by_count(cards: List[Card], rank_counts: Counter) -> List[Card]:
    """Sort cards by count (descending), then by rank (descending)."""
    return sorted(cards, key=lambda c: (rank_counts[c.rank], c.rank), reverse=True)


def _reorder_wheel(cards: List[Card]) -> List[Card]:
    """Reorder wheel straight so Ace is last (5-4-3-2-A)."""
    ace = [c for c in cards if c.rank == Rank.ACE][0]
    others = sorted([c for c in cards if c.rank != Rank.ACE], 
                   key=lambda c: c.rank, reverse=True)
    return others + [ace]


def _calculate_rank(hand_type: HandRank, kicker_ranks: List[Rank]) -> int:
    """
    Calculate the absolute rank for a hand type and kickers.
    
    This creates a unique rank number where lower = better hand.
    Formula: (10 - hand_type) * RANK_MULTIPLIER + kicker_value
    
    Hand types go from 10 (Royal Flush) to 1 (High Card).
    So Royal Flush gets base 0, High Card gets base 9*M.
    """
    # Higher hand_type value = better hand, but we want lower rank = better
    base = (10 - int(hand_type)) * RANK_MULTIPLIER
    
    # Convert kickers to a single number
    # Each kicker position is weighted by powers of 13
    kicker_value = 0
    for i, rank in enumerate(kicker_ranks):
        # Invert rank (Ace=0, King=1, ..., 2=12) for lower=better
        inverted = Rank.ACE - rank
        kicker_value += inverted * (13 ** (len(kicker_ranks) - 1 - i))
    
    return base + kicker_value


def _calculate_high_card_rank(hand_type: HandRank, ranks: List[Rank]) -> int:
    """Calculate rank for hands determined by high cards (flush, high card)."""
    return _calculate_rank(hand_type, sorted(ranks, reverse=True)[:5])


def compare_hands(cards1: List[Card], cards2: List[Card]) -> int:
    """
    Compare two hands.
    
    Returns:
        -1 if cards1 wins, 1 if cards2 wins, 0 if tie
    """
    rank1, _, _ = evaluate_hand(cards1)
    rank2, _, _ = evaluate_hand(cards2)
    
    if rank1 < rank2:
        return -1  # cards1 wins (lower rank = better)
    elif rank1 > rank2:
        return 1   # cards2 wins
    else:
        return 0   # tie


def hand_rank_to_string(rank: int) -> str:
    """Convert numeric rank to human-readable string."""
    # Determine hand type from rank
    # rank = (10 - hand_type) * RANK_MULTIPLIER + kicker_value
    # So hand_type = 10 - (rank // RANK_MULTIPLIER)
    hand_type_value = 10 - (rank // RANK_MULTIPLIER)
    try:
        hand_type = HandRank(hand_type_value)
        return HAND_RANK_NAMES[hand_type]
    except ValueError:
        return "Unknown"


def get_hand_description(cards: List[Card]) -> str:
    """Get a human-readable description of the hand."""
    if len(cards) < 5:
        return "Incomplete hand"
    
    rank, hand_type, best_cards = evaluate_hand(cards)
    base_name = HAND_RANK_NAMES[hand_type]
    
    # Add detail based on hand type
    if hand_type == HandRank.ROYAL_FLUSH:
        return "Royal Flush"
    elif hand_type == HandRank.STRAIGHT_FLUSH:
        high = max(c.rank for c in best_cards)
        return f"Straight Flush, {_rank_name(high)} high"
    elif hand_type == HandRank.FOUR_OF_A_KIND:
        quad_rank = _get_most_common_rank(best_cards)
        return f"Four of a Kind, {_rank_name(quad_rank)}s"
    elif hand_type == HandRank.FULL_HOUSE:
        rank_counts = Counter(c.rank for c in best_cards)
        trips = max(rank_counts, key=rank_counts.get)
        pair = min(rank_counts, key=rank_counts.get)
        return f"Full House, {_rank_name(trips)}s full of {_rank_name(pair)}s"
    elif hand_type == HandRank.FLUSH:
        high = max(c.rank for c in best_cards)
        return f"Flush, {_rank_name(high)} high"
    elif hand_type == HandRank.STRAIGHT:
        # Handle wheel
        ranks = [c.rank for c in best_cards]
        if Rank.ACE in ranks and Rank.TWO in ranks:
            return "Straight, Five high (Wheel)"
        high = max(ranks)
        return f"Straight, {_rank_name(high)} high"
    elif hand_type == HandRank.THREE_OF_A_KIND:
        trips_rank = _get_most_common_rank(best_cards)
        return f"Three of a Kind, {_rank_name(trips_rank)}s"
    elif hand_type == HandRank.TWO_PAIR:
        rank_counts = Counter(c.rank for c in best_cards)
        pairs = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
        return f"Two Pair, {_rank_name(pairs[0])}s and {_rank_name(pairs[1])}s"
    elif hand_type == HandRank.ONE_PAIR:
        pair_rank = _get_most_common_rank(best_cards)
        return f"Pair of {_rank_name(pair_rank)}s"
    else:
        high = max(c.rank for c in best_cards)
        return f"High Card, {_rank_name(high)}"


def _get_most_common_rank(cards: List[Card]) -> Rank:
    """Get the most common rank in the cards."""
    rank_counts = Counter(c.rank for c in cards)
    return max(rank_counts, key=rank_counts.get)


def _rank_name(rank: Rank) -> str:
    """Get the name of a rank."""
    names = {
        Rank.TWO: "Two", Rank.THREE: "Three", Rank.FOUR: "Four",
        Rank.FIVE: "Five", Rank.SIX: "Six", Rank.SEVEN: "Seven",
        Rank.EIGHT: "Eight", Rank.NINE: "Nine", Rank.TEN: "Ten",
        Rank.JACK: "Jack", Rank.QUEEN: "Queen", Rank.KING: "King",
        Rank.ACE: "Ace"
    }
    return names[rank]
