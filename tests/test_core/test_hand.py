"""
Tests for hand evaluation.
"""

import pytest
from deeppoker.core.card import Card, Rank, Suit
from deeppoker.core.hand import (
    evaluate_hand, compare_hands, HandRank,
    get_hand_description
)


class TestHandRanking:
    """Tests for hand ranking."""
    
    def test_royal_flush(self, royal_flush):
        """Test royal flush recognition."""
        rank, hand_type, _ = evaluate_hand(royal_flush)
        assert hand_type == HandRank.ROYAL_FLUSH
        # Royal flush has the lowest rank (best hand), base = (10-10)*1M = 0
        assert rank == 0  # Best possible hand
    
    def test_straight_flush(self, straight_flush):
        """Test straight flush recognition."""
        rank, hand_type, _ = evaluate_hand(straight_flush)
        assert hand_type == HandRank.STRAIGHT_FLUSH
    
    def test_four_of_a_kind(self):
        """Test four of a kind recognition."""
        hand = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.ACE, Suit.CLUBS),
            Card(Rank.KING, Suit.SPADES),
        ]
        rank, hand_type, _ = evaluate_hand(hand)
        assert hand_type == HandRank.FOUR_OF_A_KIND
    
    def test_full_house(self):
        """Test full house recognition."""
        hand = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.KING, Suit.SPADES),
        ]
        rank, hand_type, _ = evaluate_hand(hand)
        assert hand_type == HandRank.FULL_HOUSE
    
    def test_flush(self):
        """Test flush recognition."""
        hand = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.JACK, Suit.SPADES),
            Card(Rank.NINE, Suit.SPADES),
            Card(Rank.TWO, Suit.SPADES),
        ]
        rank, hand_type, _ = evaluate_hand(hand)
        assert hand_type == HandRank.FLUSH
    
    def test_straight(self):
        """Test straight recognition."""
        hand = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.SPADES),
        ]
        rank, hand_type, _ = evaluate_hand(hand)
        assert hand_type == HandRank.STRAIGHT
    
    def test_wheel_straight(self, wheel_straight):
        """Test wheel straight (A-2-3-4-5) recognition."""
        rank, hand_type, _ = evaluate_hand(wheel_straight)
        assert hand_type == HandRank.STRAIGHT
        
        # Wheel should be 5-high, not ace-high
        desc = get_hand_description(wheel_straight)
        assert "Five high" in desc or "Wheel" in desc
    
    def test_three_of_a_kind(self):
        """Test three of a kind recognition."""
        hand = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.SPADES),
        ]
        rank, hand_type, _ = evaluate_hand(hand)
        assert hand_type == HandRank.THREE_OF_A_KIND
    
    def test_two_pair(self):
        """Test two pair recognition."""
        hand = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.DIAMONDS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.SPADES),
        ]
        rank, hand_type, _ = evaluate_hand(hand)
        assert hand_type == HandRank.TWO_PAIR
    
    def test_one_pair(self, sample_hand):
        """Test one pair recognition."""
        rank, hand_type, _ = evaluate_hand(sample_hand)
        assert hand_type == HandRank.ONE_PAIR
    
    def test_high_card(self):
        """Test high card recognition."""
        hand = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.JACK, Suit.DIAMONDS),
            Card(Rank.NINE, Suit.CLUBS),
            Card(Rank.TWO, Suit.SPADES),
        ]
        rank, hand_type, _ = evaluate_hand(hand)
        assert hand_type == HandRank.HIGH_CARD


class TestHandComparison:
    """Tests for comparing hands."""
    
    def test_royal_flush_beats_straight_flush(self, royal_flush, straight_flush):
        """Royal flush beats straight flush."""
        result = compare_hands(royal_flush, straight_flush)
        assert result == -1  # First hand wins
    
    def test_flush_beats_straight(self):
        """Flush beats straight."""
        # Non-straight flush (K-J-9-7-2 of spades)
        flush = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.JACK, Suit.SPADES),
            Card(Rank.NINE, Suit.SPADES),
            Card(Rank.SEVEN, Suit.SPADES),
            Card(Rank.TWO, Suit.SPADES),
        ]
        # Straight (A-K-Q-J-T, not flush)
        straight = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.HEARTS),
        ]
        result = compare_hands(flush, straight)
        assert result == -1  # Flush wins
    
    def test_higher_pair_wins(self):
        """Higher pair beats lower pair."""
        pair_aces = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.DIAMONDS),
            Card(Rank.QUEEN, Suit.CLUBS),
            Card(Rank.JACK, Suit.SPADES),
        ]
        pair_kings = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.SPADES),
        ]
        result = compare_hands(pair_aces, pair_kings)
        assert result == -1
    
    def test_kicker_decides(self):
        """Same pair, different kicker."""
        pair_ace_king = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.DIAMONDS),
            Card(Rank.FIVE, Suit.CLUBS),
            Card(Rank.TWO, Suit.SPADES),
        ]
        pair_ace_queen = [
            Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.ACE, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.HEARTS),
            Card(Rank.FIVE, Suit.SPADES),
            Card(Rank.TWO, Suit.HEARTS),
        ]
        result = compare_hands(pair_ace_king, pair_ace_queen)
        assert result == -1  # King kicker wins
    
    def test_tie(self):
        """Identical hands tie."""
        hand1 = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.NINE, Suit.SPADES),
        ]
        hand2 = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.DIAMONDS),
            Card(Rank.QUEEN, Suit.CLUBS),
            Card(Rank.JACK, Suit.SPADES),
            Card(Rank.NINE, Suit.HEARTS),
        ]
        result = compare_hands(hand1, hand2)
        assert result == 0  # Tie


class TestSevenCardEvaluation:
    """Tests for 7-card hand evaluation."""
    
    def test_best_five_from_seven(self):
        """Select best 5 cards from 7."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.TWO, Suit.HEARTS),  # Not used
            Card(Rank.THREE, Suit.DIAMONDS),  # Not used
        ]
        rank, hand_type, best_cards = evaluate_hand(cards)
        assert hand_type == HandRank.FULL_HOUSE
        assert len(best_cards) == 5
    
    def test_flush_from_six_suited(self):
        """Find flush in 6 suited cards."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.QUEEN, Suit.SPADES),
            Card(Rank.JACK, Suit.SPADES),
            Card(Rank.NINE, Suit.SPADES),
            Card(Rank.TWO, Suit.SPADES),
            Card(Rank.THREE, Suit.HEARTS),
        ]
        rank, hand_type, _ = evaluate_hand(cards)
        assert hand_type == HandRank.FLUSH


class TestHandDescription:
    """Tests for hand description."""
    
    def test_royal_flush_description(self, royal_flush):
        """Test royal flush description."""
        desc = get_hand_description(royal_flush)
        assert "Royal Flush" in desc
    
    def test_pair_description(self, sample_hand):
        """Test pair description."""
        desc = get_hand_description(sample_hand)
        assert "Pair" in desc
        assert "Ace" in desc
