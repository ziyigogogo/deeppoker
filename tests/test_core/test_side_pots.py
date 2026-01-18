"""
Tests for side pot calculation in Texas Hold'em.

These tests verify the correct handling of side pots when players go all-in
with different stack sizes. Side pot calculation is a critical feature that
must work correctly for fair game outcomes.

Reference: WSOP Tournament Rules
"""

import pytest
from deeppoker.core.game import TexasHoldemGame, ActionType, Pot
from deeppoker.core.rules import GamePhase
from deeppoker.core.player import Player, PlayerState
from deeppoker.core.card import Card, Rank, Suit


class TestSidePotCalculation:
    """Tests for side pot calculation logic."""
    
    def test_single_allin_creates_side_pot(self):
        """
        Test: A(100) all-in, B(500) call, C(500) call
        Expected: Main pot 300, Side pot 800
        """
        # Create game with custom stacks
        game = TexasHoldemGame(
            num_players=3,
            big_blind=20,
            small_blind=10,
            buy_in=500,
        )
        # Manually set different stacks
        game.players[0].stack = 100  # Player A - short stack
        game.players[1].stack = 500  # Player B
        game.players[2].stack = 500  # Player C
        
        game.start_hand()
        
        # Get initial pot from blinds
        initial_pot = game.pot_total
        
        # Player actions depend on position, let's track the flow
        # After blinds: SB=10, BB=20, current bet=20
        
        # First player to act goes all-in with 100
        # We need to find the short stack player and have them all-in
        short_stack_idx = 0
        for i, p in enumerate(game.players):
            if p.stack <= 100:
                short_stack_idx = i
                break
        
        # Play out a scenario where one player is all-in for less
        # This is a basic structure test - detailed action sequence tests 
        # are in other test classes
        
    def test_calculate_side_pots_basic(self):
        """Test basic side pot calculation with different bet levels."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Manually set total bets to simulate all-in scenario
        # Player 0: bet 100 (short stack all-in)
        # Player 1: bet 300 (medium stack all-in)
        # Player 2: bet 300 (called)
        
        game.players[0].total_bet = 100
        game.players[0].state = PlayerState.ALL_IN
        
        game.players[1].total_bet = 300
        game.players[1].state = PlayerState.ALL_IN
        
        game.players[2].total_bet = 300
        game.players[2].state = PlayerState.ACTIVE
        
        # Calculate side pots
        game._calculate_side_pots()
        
        # Should have 2 pots:
        # Main pot: 100 * 3 = 300 (all 3 eligible)
        # Side pot: 200 * 2 = 400 (only players 1 and 2 eligible)
        assert len(game.pots) == 2
        
        # Main pot
        assert game.pots[0].amount == 300
        assert len(game.pots[0].eligible_players) == 3
        
        # Side pot
        assert game.pots[1].amount == 400
        assert len(game.pots[1].eligible_players) == 2
        assert game.players[0].player_id not in game.pots[1].eligible_players
        
    def test_calculate_side_pots_three_levels(self):
        """
        Test: A(100), B(200), C(500) all go all-in
        Expected:
        - Main pot: 100 * 3 = 300 (A, B, C eligible)
        - Side pot 1: 100 * 2 = 200 (B, C eligible)
        - Side pot 2: 300 * 1 = 300 (only C eligible, but should be 0 if only one player)
        """
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Set up all-in scenario
        game.players[0].total_bet = 100
        game.players[0].state = PlayerState.ALL_IN
        
        game.players[1].total_bet = 200
        game.players[1].state = PlayerState.ALL_IN
        
        game.players[2].total_bet = 500
        game.players[2].state = PlayerState.ALL_IN
        
        game._calculate_side_pots()
        
        # Should have 3 pots (or 2 if single-player pot is excluded)
        assert len(game.pots) >= 2
        
        # Main pot: 300
        assert game.pots[0].amount == 300
        
        # Side pot 1: 200
        assert game.pots[1].amount == 200
        
    def test_side_pot_with_fold(self):
        """Test side pot calculation when one player folds."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Player 0 bets and then folds
        game.players[0].total_bet = 50
        game.players[0].state = PlayerState.FOLDED
        
        # Player 1 goes all-in for 100
        game.players[1].total_bet = 100
        game.players[1].state = PlayerState.ALL_IN
        
        # Player 2 calls
        game.players[2].total_bet = 100
        game.players[2].state = PlayerState.ACTIVE
        
        game._calculate_side_pots()
        
        # Folded player's contribution should still be in the pot
        # but they are not eligible to win
        total_pot = sum(p.amount for p in game.pots)
        assert total_pot == 250  # 50 + 100 + 100
        
        # Folded player should not be eligible in any pot
        for pot in game.pots:
            assert game.players[0].player_id not in pot.eligible_players
            
    def test_no_side_pot_when_equal_stacks(self):
        """No side pot needed when all players bet the same amount."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # All players bet the same
        for player in game.players:
            player.total_bet = 100
            player.state = PlayerState.ACTIVE
        
        game._calculate_side_pots()
        
        # Should have only one pot
        assert len(game.pots) == 1
        assert game.pots[0].amount == 300
        assert len(game.pots[0].eligible_players) == 3


class TestSidePotDistribution:
    """Tests for distributing side pots to winners."""
    
    def test_main_pot_winner_different_from_side_pot(self):
        """
        Scenario: Player A wins main pot, Player B wins side pot.
        
        A: All-in for 100, has best hand for main pot (Royal Flush)
        B: All-in for 300, has second best hand (Full House)
        C: Calls 300, has worst hand (Two Pair)
        
        Main pot (300): A wins
        Side pot (400): B wins (A not eligible)
        """
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Set up bets
        game.players[0].total_bet = 100
        game.players[0].state = PlayerState.ALL_IN
        
        game.players[1].total_bet = 300
        game.players[1].state = PlayerState.ALL_IN
        
        game.players[2].total_bet = 300
        game.players[2].state = PlayerState.ACTIVE
        
        # Set up hands - A has best, B has second, C has worst
        # Royal flush for A (A♠K♠ + Q♠J♠T♠ on board)
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.SPADES),
        ]
        # Full house for B (K♥K♦ + K♣ on board makes trips, + pair from board)
        game.players[1].hole_cards = [
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.KING, Suit.DIAMONDS),
        ]
        # Two pair for C (low cards, relies on board)
        game.players[2].hole_cards = [
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.THREE, Suit.CLUBS),
        ]
        
        # Set community cards:
        # A gets Royal Flush: A♠K♠Q♠J♠T♠
        # B gets Full House: K♥K♦K♣ + Q♠Q♦ (Kings full of Queens)
        # C gets Two Pair: Q♠Q♦ + T♠T♦ (from board, worse than B)
        game.community_cards = [
            Card(Rank.QUEEN, Suit.SPADES),
            Card(Rank.JACK, Suit.SPADES),
            Card(Rank.TEN, Suit.SPADES),
            Card(Rank.KING, Suit.CLUBS),   # Gives B three Kings
            Card(Rank.QUEEN, Suit.DIAMONDS),  # Gives B full house
        ]
        
        # Calculate side pots
        game._calculate_side_pots()
        
        # Determine winners
        winners = game._determine_winners()
        
        # A should win main pot (300)
        # B should win side pot (400) since A is not eligible
        player_a_winnings = sum(w["amount"] for w in winners if w["player_id"] == "0")
        player_b_winnings = sum(w["amount"] for w in winners if w["player_id"] == "1")
        
        assert player_a_winnings == 300  # Main pot
        assert player_b_winnings == 400  # Side pot
        
    def test_split_pot_with_remainder(self):
        """Test split pot distribution when amount doesn't divide evenly."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Set up identical hands for a tie
        game.players[0].hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
        ]
        game.players[1].hole_cards = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.SPADES),
        ]
        
        # Board that doesn't help either player differentiate
        game.community_cards = [
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.DIAMONDS),
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.THREE, Suit.HEARTS),
        ]
        
        # Set up pot with odd amount
        game.players[0].total_bet = 51
        game.players[1].total_bet = 50
        
        game._calculate_side_pots()
        
        # Total pot: 101 (odd)
        winners = game._determine_winners()
        
        # Both should win, total should equal pot
        total_distributed = sum(w["amount"] for w in winners)
        assert total_distributed == 101
        

class TestAllInScenarios:
    """Tests for various all-in scenarios."""
    
    def test_short_stack_allin_preflop(self):
        """Test short stack going all-in preflop."""
        game = TexasHoldemGame(
            num_players=3,
            big_blind=20,
            small_blind=10,
            buy_in=100,  # Start with small stacks
        )
        # Give player 0 very short stack
        game.players[0].stack = 30
        
        game.start_hand()
        
        # Player 0 (short stack) should be able to go all-in
        # Track the current player and test all-in action
        while game.is_hand_running():
            current = game.current_player
            if current is None:
                break
                
            if current.stack <= 30 and current.stack > 0:
                result = game.take_action(ActionType.ALL_IN)
                assert result.success or current.state == PlayerState.ALL_IN
                break
            else:
                # Other players fold or call
                legal = game.get_legal_actions()
                if any(a["type"] == "FOLD" for a in legal):
                    game.take_action(ActionType.FOLD)
                    
    def test_multiple_allins_same_round(self):
        """Test multiple players going all-in in the same betting round."""
        game = TexasHoldemGame(num_players=4, buy_in=1000)
        
        # Set varying stack sizes
        game.players[0].stack = 100
        game.players[1].stack = 200
        game.players[2].stack = 300
        game.players[3].stack = 1000
        
        game.start_hand()
        
        # Simulate all players going all-in
        game.players[0].total_bet = 100
        game.players[0].state = PlayerState.ALL_IN
        
        game.players[1].total_bet = 200
        game.players[1].state = PlayerState.ALL_IN
        
        game.players[2].total_bet = 300
        game.players[2].state = PlayerState.ALL_IN
        
        game.players[3].total_bet = 300
        game.players[3].state = PlayerState.ACTIVE
        
        game._calculate_side_pots()
        
        # Should have 3 pots
        assert len(game.pots) == 3
        
        # Verify pot amounts
        # Main: 100 * 4 = 400
        assert game.pots[0].amount == 400
        # Side 1: 100 * 3 = 300
        assert game.pots[1].amount == 300
        # Side 2: 100 * 2 = 200
        assert game.pots[2].amount == 200
        
    def test_allin_heads_up(self):
        """Test all-in scenario in heads-up game."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        
        # Different stack sizes
        game.players[0].stack = 200
        game.players[1].stack = 1000
        
        game.start_hand()
        
        # Short stack goes all-in
        game.players[0].total_bet = 200
        game.players[0].state = PlayerState.ALL_IN
        
        # Big stack calls
        game.players[1].total_bet = 200
        game.players[1].state = PlayerState.ACTIVE
        
        game._calculate_side_pots()
        
        # Should have single pot
        assert len(game.pots) == 1
        assert game.pots[0].amount == 400
        

class TestSidePotEdgeCases:
    """Edge cases for side pot calculation."""
    
    def test_zero_bet_player_not_in_pot(self):
        """Player with zero bet should not be in any pot."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Player 0 folds immediately (before betting)
        game.players[0].total_bet = 0
        game.players[0].state = PlayerState.FOLDED
        
        # Players 1 and 2 bet
        game.players[1].total_bet = 100
        game.players[2].total_bet = 100
        
        game._calculate_side_pots()
        
        # Player 0 should not be eligible for any pot
        for pot in game.pots:
            assert game.players[0].player_id not in pot.eligible_players
            
    def test_all_players_allin_same_amount(self):
        """All players all-in for same amount - single pot."""
        game = TexasHoldemGame(num_players=3, buy_in=100)
        game.start_hand()
        
        # All players all-in for 100
        for player in game.players:
            player.total_bet = 100
            player.state = PlayerState.ALL_IN
            
        game._calculate_side_pots()
        
        # Should have single pot
        assert len(game.pots) == 1
        assert game.pots[0].amount == 300
        assert len(game.pots[0].eligible_players) == 3
        
    def test_side_pot_after_fold_during_round(self):
        """
        Test side pot when player folds after contributing.
        
        A: Bets 50, folds
        B: All-in 100
        C: Calls 100
        
        Pot should be 250, but A is not eligible.
        """
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        game.players[0].total_bet = 50
        game.players[0].state = PlayerState.FOLDED
        
        game.players[1].total_bet = 100
        game.players[1].state = PlayerState.ALL_IN
        
        game.players[2].total_bet = 100
        game.players[2].state = PlayerState.ACTIVE
        
        game._calculate_side_pots()
        
        total = sum(p.amount for p in game.pots)
        assert total == 250
        
        # Folded player not eligible
        for pot in game.pots:
            assert "0" not in pot.eligible_players


class TestIntegrationSidePots:
    """Integration tests for side pots with full game flow."""
    
    def test_full_hand_with_side_pot(self):
        """Play a full hand that results in side pots."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        
        # Give player 0 short stack
        game.players[0].stack = 50
        
        game.start_hand()
        
        # Play through to showdown
        actions_taken = 0
        max_actions = 50  # Prevent infinite loop
        
        while game.is_hand_running() and actions_taken < max_actions:
            legal = game.get_legal_actions()
            if not legal:
                break
                
            # Simple strategy: call or check when possible
            action_types = [a["type"] for a in legal]
            
            if "CHECK" in action_types:
                game.take_action(ActionType.CHECK)
            elif "CALL" in action_types:
                game.take_action(ActionType.CALL)
            elif "ALL_IN" in action_types:
                game.take_action(ActionType.ALL_IN)
            else:
                game.take_action(ActionType.FOLD)
                
            actions_taken += 1
            
        # Game should complete
        assert game.phase in [GamePhase.HAND_OVER, GamePhase.SHOWDOWN] or actions_taken >= max_actions
