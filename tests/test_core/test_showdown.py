"""
Tests for showdown hand comparison and winner determination.

These tests verify:
- Correct hand ranking at showdown
- Best 5 from 7 cards selection
- Multi-way pot winner determination
- Tie handling and pot splitting
- Different winners for different pots (side pots)
"""

import pytest
from deeppoker.core.game import TexasHoldemGame, ActionType
from deeppoker.core.player import PlayerState
from deeppoker.core.card import Card, Rank, Suit
from deeppoker.core.hand import evaluate_hand, compare_hands, HandRank


class TestShowdownBasics:
    """Basic showdown tests."""
    
    def test_two_player_showdown_winner(self):
        """Test basic 2-player showdown determines correct winner."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Set up hands
        # Player 0: Pair of Aces
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
        ]
        # Player 1: Pair of Kings
        game.players[1].hole_cards = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
        ]
        
        # Set community cards
        game.community_cards = [
            Card(Rank.TWO, Suit.DIAMONDS),
            Card(Rank.THREE, Suit.CLUBS),
            Card(Rank.FOUR, Suit.DIAMONDS),
            Card(Rank.FIVE, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.HEARTS),
        ]
        
        # Set up bets for showdown
        game.players[0].total_bet = 100
        game.players[1].total_bet = 100
        
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # Player 0 (Aces) should win
        assert len(winners) == 1
        assert winners[0]["player_id"] == "0"
        assert winners[0]["amount"] == 200
        
    def test_three_player_showdown(self):
        """Test 3-player showdown determines correct winner."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Player 0: Flush
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.HEARTS),
        ]
        # Player 1: Straight
        game.players[1].hole_cards = [
            Card(Rank.SIX, Suit.SPADES),
            Card(Rank.SEVEN, Suit.CLUBS),
        ]
        # Player 2: Two Pair
        game.players[2].hole_cards = [
            Card(Rank.EIGHT, Suit.DIAMONDS),
            Card(Rank.EIGHT, Suit.CLUBS),
        ]
        
        # Board gives potential flush and straight
        game.community_cards = [
            Card(Rank.TWO, Suit.HEARTS),
            Card(Rank.THREE, Suit.HEARTS),
            Card(Rank.FOUR, Suit.HEARTS),
            Card(Rank.FIVE, Suit.SPADES),
            Card(Rank.NINE, Suit.DIAMONDS),
        ]
        
        # All players bet same amount
        for i, p in enumerate(game.players):
            p.total_bet = 100
            
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # Player 0 (Flush) should win
        assert len(winners) == 1
        assert winners[0]["player_id"] == "0"
        

class TestBestFiveFromSeven:
    """Tests for selecting best 5 cards from 7."""
    
    def test_best_five_uses_both_hole_cards(self):
        """Test when best hand uses both hole cards."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Player 0: Pocket pair that becomes trips with board
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
        ]
        game.players[1].hole_cards = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.QUEEN, Suit.HEARTS),
        ]
        
        # Board that doesn't form a straight
        game.community_cards = [
            Card(Rank.ACE, Suit.DIAMONDS),  # Gives player 0 trips
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.DIAMONDS),
            Card(Rank.NINE, Suit.CLUBS),
            Card(Rank.JACK, Suit.HEARTS),
        ]
        
        # Evaluate player 0's hand
        all_cards = game.players[0].hole_cards + game.community_cards
        rank, hand_type, best_five = evaluate_hand(all_cards)
        
        # Should be three of a kind (Aces)
        assert hand_type == HandRank.THREE_OF_A_KIND
        # Best five should include both hole cards (AA) and board A
        ace_count = sum(1 for c in best_five if c.rank == Rank.ACE)
        assert ace_count == 3
        
    def test_best_five_uses_one_hole_card(self):
        """Test when best hand uses only one hole card."""
        # Player has A♠2♦, board is K♠Q♠J♠T♠3♥
        # Best hand is K-high straight (K-Q-J-T-9 would need 9)
        # Actually best is flush: K♠Q♠J♠T♠A♠ (using A♠)
        hole = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.TWO, Suit.DIAMONDS),
        ]
        board = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.QUEEN, Suit.SPADES),
            Card(Rank.JACK, Suit.SPADES),
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.THREE, Suit.HEARTS),
        ]
        
        all_cards = hole + board
        rank, hand_type, best_five = evaluate_hand(all_cards)
        
        # Should be Royal Flush!
        assert hand_type == HandRank.ROYAL_FLUSH
        
    def test_best_five_uses_zero_hole_cards(self):
        """Test when best hand uses no hole cards (plays the board)."""
        hole = [
            Card(Rank.TWO, Suit.DIAMONDS),
            Card(Rank.THREE, Suit.CLUBS),
        ]
        # Board is a straight flush
        board = [
            Card(Rank.FIVE, Suit.HEARTS),
            Card(Rank.SIX, Suit.HEARTS),
            Card(Rank.SEVEN, Suit.HEARTS),
            Card(Rank.EIGHT, Suit.HEARTS),
            Card(Rank.NINE, Suit.HEARTS),
        ]
        
        all_cards = hole + board
        rank, hand_type, best_five = evaluate_hand(all_cards)
        
        # Best hand is straight flush on board
        assert hand_type == HandRank.STRAIGHT_FLUSH


class TestTieHandling:
    """Tests for tie handling at showdown."""
    
    def test_exact_tie_splits_pot(self):
        """Test that exact ties split the pot evenly."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Both players have same hand (straight)
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.TWO, Suit.HEARTS),
        ]
        game.players[1].hole_cards = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.TWO, Suit.SPADES),
        ]
        
        # Board completes the same straight for both
        game.community_cards = [
            Card(Rank.THREE, Suit.DIAMONDS),
            Card(Rank.FOUR, Suit.CLUBS),
            Card(Rank.FIVE, Suit.DIAMONDS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.HEARTS),
        ]
        
        game.players[0].total_bet = 100
        game.players[1].total_bet = 100
        
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # Both should win
        assert len(winners) == 2
        # Each gets half
        total_won = sum(w["amount"] for w in winners)
        assert total_won == 200
        
    def test_three_way_tie(self):
        """Test three-way tie splits pot."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # All players play the board
        game.players[0].hole_cards = [Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.SPADES)]
        game.players[1].hole_cards = [Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.HEARTS)]
        game.players[2].hole_cards = [Card(Rank.TWO, Suit.DIAMONDS), Card(Rank.THREE, Suit.DIAMONDS)]
        
        # Board is the best hand for all
        game.community_cards = [
            Card(Rank.ACE, Suit.CLUBS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.CLUBS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.CLUBS),
        ]
        
        for p in game.players:
            p.total_bet = 100
            
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # All three should win
        assert len(winners) == 3
        # Total distributed should equal pot
        total_won = sum(w["amount"] for w in winners)
        assert total_won == 300
        
    def test_kicker_breaks_tie(self):
        """Test that kicker breaks a tie."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Player 0: Pair of Aces with King kicker
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
        ]
        # Player 1: Pair of Aces with Queen kicker
        game.players[1].hole_cards = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.SPADES),
        ]
        
        # Board without straight possibility
        game.community_cards = [
            Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.DIAMONDS),
            Card(Rank.NINE, Suit.CLUBS),
            Card(Rank.JACK, Suit.HEARTS),
        ]
        
        game.players[0].total_bet = 100
        game.players[1].total_bet = 100
        
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # Player 0 should win (King kicker beats Queen)
        assert len(winners) == 1
        assert winners[0]["player_id"] == "0"


class TestMultiplePotWinners:
    """Tests for different winners in main pot vs side pots."""
    
    def test_different_winner_per_pot(self):
        """Test that different players can win different pots."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Player 0: Best hand, but shortest stack (only in main pot)
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
        ]
        game.players[0].total_bet = 100
        game.players[0].state = PlayerState.ALL_IN
        
        # Player 1: Second best hand, medium stack
        game.players[1].hole_cards = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
        ]
        game.players[1].total_bet = 300
        game.players[1].state = PlayerState.ALL_IN
        
        # Player 2: Worst hand, largest stack
        game.players[2].hole_cards = [
            Card(Rank.QUEEN, Suit.SPADES),
            Card(Rank.QUEEN, Suit.HEARTS),
        ]
        game.players[2].total_bet = 300
        game.players[2].state = PlayerState.ACTIVE
        
        # Board doesn't improve anyone
        game.community_cards = [
            Card(Rank.TWO, Suit.DIAMONDS),
            Card(Rank.THREE, Suit.CLUBS),
            Card(Rank.FOUR, Suit.DIAMONDS),
            Card(Rank.FIVE, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.HEARTS),
        ]
        
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # Player 0 wins main pot (100*3 = 300)
        # Player 1 wins side pot (200*2 = 400)
        player_0_winnings = sum(w["amount"] for w in winners if w["player_id"] == "0")
        player_1_winnings = sum(w["amount"] for w in winners if w["player_id"] == "1")
        
        assert player_0_winnings == 300
        assert player_1_winnings == 400


class TestShowdownHandDescriptions:
    """Tests for hand description at showdown."""
    
    def test_winner_hand_description(self):
        """Test that winner's hand is correctly described."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Player 0: Full house
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
        ]
        game.players[1].hole_cards = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.QUEEN, Suit.HEARTS),
        ]
        
        # Board gives player 0 full house (Aces full of twos)
        game.community_cards = [
            Card(Rank.ACE, Suit.DIAMONDS),
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.TWO, Suit.DIAMONDS),
            Card(Rank.FIVE, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.HEARTS),
        ]
        
        game.players[0].total_bet = 100
        game.players[1].total_bet = 100
        
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        assert len(winners) == 1
        assert "Full House" in winners[0]["description"]


class TestFoldedPlayersExcluded:
    """Tests that folded players are excluded from showdown."""
    
    def test_folded_player_not_in_showdown(self):
        """Folded players should not participate in showdown."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Player 0 has best hand but folded
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.ACE, Suit.HEARTS),
        ]
        game.players[0].total_bet = 50
        game.players[0].state = PlayerState.FOLDED
        
        # Player 1 has medium hand
        game.players[1].hole_cards = [
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
        ]
        game.players[1].total_bet = 100
        
        # Player 2 has worst hand
        game.players[2].hole_cards = [
            Card(Rank.QUEEN, Suit.SPADES),
            Card(Rank.QUEEN, Suit.HEARTS),
        ]
        game.players[2].total_bet = 100
        
        game.community_cards = [
            Card(Rank.TWO, Suit.DIAMONDS),
            Card(Rank.THREE, Suit.CLUBS),
            Card(Rank.FOUR, Suit.DIAMONDS),
            Card(Rank.FIVE, Suit.CLUBS),
            Card(Rank.SEVEN, Suit.HEARTS),
        ]
        
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # Player 0 should NOT win even though they have best hand
        # Player 1 should win
        assert all(w["player_id"] != "0" for w in winners)
        assert any(w["player_id"] == "1" for w in winners)


class TestWSOP73OddChipRule:
    """Tests for WSOP Rule 73: Odd chip distribution."""
    
    def test_odd_chip_to_first_player_from_button(self):
        """Odd chip should go to first winner clockwise from the button."""
        from deeppoker.core.game import Pot
        
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # All players have same hand (play the board)
        game.players[0].hole_cards = [Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.HEARTS)]
        game.players[1].hole_cards = [Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.SPADES)]
        game.players[2].hole_cards = [Card(Rank.TWO, Suit.DIAMONDS), Card(Rank.THREE, Suit.CLUBS)]
        
        # Board is Royal Flush - everyone ties
        game.community_cards = [
            Card(Rank.ACE, Suit.CLUBS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.CLUBS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.CLUBS),
        ]
        
        # Set up pot with odd amount (100 / 3 = 33 remainder 1)
        game.pots = [Pot(amount=100, eligible_players=['0', '1', '2'])]
        
        winners = game._determine_winners()
        
        # Find who gets the extra chip
        dealer = game.dealer_position
        first_winner_pos = (dealer + 1) % 3
        first_winner_pid = str(first_winner_pos)
        
        # The first winner clockwise from button should get 34
        for w in winners:
            if w["player_id"] == first_winner_pid:
                assert w["amount"] == 34, f"Player {first_winner_pid} should get odd chip"
            else:
                assert w["amount"] == 33
                
    def test_odd_chip_with_two_remainder(self):
        """When remainder is 2, first two winners get extra chips."""
        from deeppoker.core.game import Pot
        
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # All players tie
        game.players[0].hole_cards = [Card(Rank.TWO, Suit.SPADES), Card(Rank.THREE, Suit.HEARTS)]
        game.players[1].hole_cards = [Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.SPADES)]
        game.players[2].hole_cards = [Card(Rank.TWO, Suit.DIAMONDS), Card(Rank.THREE, Suit.CLUBS)]
        
        game.community_cards = [
            Card(Rank.ACE, Suit.CLUBS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.CLUBS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.CLUBS),
        ]
        
        # 101 / 3 = 33 remainder 2
        game.pots = [Pot(amount=101, eligible_players=['0', '1', '2'])]
        
        winners = game._determine_winners()
        
        # Total should be 101
        total = sum(w["amount"] for w in winners)
        assert total == 101


class TestShowdownIntegration:
    """Integration tests for complete showdown scenarios."""
    
    def test_full_hand_to_showdown(self):
        """Test complete hand from start to showdown."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Play through all streets checking/calling
        max_actions = 50
        actions = 0
        
        while game.is_hand_running() and actions < max_actions:
            legal = game.get_legal_actions()
            action_types = [a["type"] for a in legal]
            
            if "CHECK" in action_types:
                game.take_action(ActionType.CHECK)
            elif "CALL" in action_types:
                game.take_action(ActionType.CALL)
            else:
                break
            actions += 1
            
        # Game should have completed
        from deeppoker.core.rules import GamePhase
        assert game.phase == GamePhase.HAND_OVER
        
        # There should be winner(s)
        winners = game.get_winners()
        assert len(winners) >= 1
        
        # Total won should equal pot
        # (Pot = all bets collected)
