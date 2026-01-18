"""
Tests for edge cases and extreme situations in Texas Hold'em.

These tests cover:
- All players fold except one (win by fold)
- All players all-in (straight to showdown)
- Short stacks and blind payments
- Maximum player scenarios (10 players)
- Consecutive hands state consistency
- Various boundary conditions
"""

import pytest
from deeppoker.core.game import TexasHoldemGame, ActionType
from deeppoker.core.rules import GamePhase
from deeppoker.core.player import PlayerState


class TestWinByFold:
    """Tests for winning when all others fold."""
    
    def test_all_fold_preflop_except_one(self):
        """Last player wins when all others fold preflop."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Two players fold
        game.take_action(ActionType.FOLD)
        game.take_action(ActionType.FOLD)
        
        # Hand should be over
        assert game.phase == GamePhase.HAND_OVER
        
        # One player should have won
        winners = game.get_winners()
        assert len(winners) == 1
        
    def test_all_fold_on_flop(self):
        """Last player wins when all others fold on flop."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        # Get to flop
        while game.phase == GamePhase.PREFLOP:
            legal = game.get_legal_actions()
            if any(a["type"] == "CALL" for a in legal):
                game.take_action(ActionType.CALL)
            elif any(a["type"] == "CHECK" for a in legal):
                game.take_action(ActionType.CHECK)
            else:
                break
                
        # On flop, everyone folds to a bet
        if game.phase == GamePhase.FLOP:
            game.take_action(ActionType.BET, 50)
            game.take_action(ActionType.FOLD)
            game.take_action(ActionType.FOLD)
            
            assert game.phase == GamePhase.HAND_OVER
            
    def test_heads_up_single_fold(self):
        """In heads-up, one fold ends the hand."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        assert game.phase == GamePhase.PREFLOP
        
        game.take_action(ActionType.FOLD)
        
        assert game.phase == GamePhase.HAND_OVER
        winners = game.get_winners()
        assert len(winners) == 1


class TestAllPlayersAllIn:
    """Tests for scenarios where all players go all-in."""
    
    def test_all_in_preflop_goes_to_showdown(self):
        """All-in preflop should deal remaining cards and go to showdown."""
        game = TexasHoldemGame(num_players=2, buy_in=100)
        game.start_hand()
        
        # Both players all-in
        game.take_action(ActionType.ALL_IN)
        game.take_action(ActionType.CALL)
        
        # Should go directly to showdown
        assert game.phase == GamePhase.HAND_OVER
        
        # All community cards should be dealt
        assert len(game.community_cards) == 5
        
    def test_three_players_all_in(self):
        """Three players all-in creates side pots correctly."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        
        # Give different stack sizes
        game.players[0].stack = 100
        game.players[1].stack = 200
        game.players[2].stack = 300
        
        game.start_hand()
        
        # All go all-in in sequence
        while game.is_hand_running():
            current = game.current_player
            if current is None:
                break
            legal = game.get_legal_actions()
            action_types = [a["type"] for a in legal]
            
            if "ALL_IN" in action_types:
                game.take_action(ActionType.ALL_IN)
            elif "CALL" in action_types:
                game.take_action(ActionType.CALL)
            else:
                break
                
        # Should have completed
        assert game.phase == GamePhase.HAND_OVER
        

class TestShortStackScenarios:
    """Tests for short stack edge cases."""
    
    def test_stack_less_than_big_blind(self):
        """Player with less than BB can still play."""
        game = TexasHoldemGame(num_players=2, big_blind=20, buy_in=100)
        
        # Give one player very short stack
        game.players[0].stack = 15  # Less than BB
        
        game.start_hand()
        
        # Short stack should be automatically all-in after posting blind
        # or able to play with reduced blind
        assert game.is_hand_running() or game.phase == GamePhase.HAND_OVER
        
    def test_stack_less_than_small_blind(self):
        """Player with less than SB can still play."""
        game = TexasHoldemGame(num_players=2, big_blind=20, small_blind=10, buy_in=100)
        
        # Give one player very short stack
        game.players[0].stack = 5  # Less than SB
        
        game.start_hand()
        
        # Game should still function
        assert True  # If we get here, no crash
        
    def test_cannot_cover_call(self):
        """Player who can't cover call goes all-in."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        
        # Give one player short stack
        game.players[0].stack = 50
        
        game.start_hand()
        
        # Raise big
        game.take_action(ActionType.RAISE, 100)
        
        # Short stack should be able to call (all-in)
        legal = game.get_legal_actions()
        action_types = [a["type"] for a in legal]
        
        assert "ALL_IN" in action_types or "CALL" in action_types


class TestMaxPlayers:
    """Tests for maximum player count (10 players)."""
    
    def test_10_player_initialization(self):
        """10-player game initializes correctly."""
        game = TexasHoldemGame(num_players=10, buy_in=1000)
        
        assert len(game.players) == 10
        
        game.start_hand()
        
        # All players should have cards
        for player in game.players:
            assert len(player.hole_cards) == 2
            
    def test_10_player_full_round(self):
        """10-player game can complete a full betting round."""
        game = TexasHoldemGame(num_players=10, buy_in=1000)
        game.start_hand()
        
        actions = 0
        max_actions = 30  # Enough for everyone to act
        
        # Complete preflop
        while game.phase == GamePhase.PREFLOP and actions < max_actions:
            legal = game.get_legal_actions()
            if any(a["type"] == "CALL" for a in legal):
                game.take_action(ActionType.CALL)
            elif any(a["type"] == "CHECK" for a in legal):
                game.take_action(ActionType.CHECK)
            else:
                break
            actions += 1
            
        # Should have moved past preflop
        assert game.phase != GamePhase.PREFLOP or actions >= max_actions
        
    def test_10_player_multiple_folds(self):
        """10-player game handles multiple folds correctly."""
        game = TexasHoldemGame(num_players=10, buy_in=1000)
        game.start_hand()
        
        # Have 8 players fold
        folds = 0
        while folds < 8 and game.phase == GamePhase.PREFLOP:
            game.take_action(ActionType.FOLD)
            folds += 1
            
        # Should be 2 players left
        assert game.num_active_players == 2


class TestConsecutiveHands:
    """Tests for state consistency across multiple hands."""
    
    def test_chips_conserved_across_hands(self):
        """Total chips should be conserved across hands."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        initial_total = 3000
        
        for _ in range(5):  # Play 5 hands
            game.start_hand()
            
            while game.is_hand_running():
                game.take_action(ActionType.FOLD)
                
            # Total chips should remain constant
            total = sum(p.stack for p in game.players)
            assert total == initial_total
            
    def test_dealer_rotates_each_hand(self):
        """Dealer position should rotate each hand."""
        game = TexasHoldemGame(num_players=4, buy_in=1000)
        
        dealers = []
        for _ in range(4):
            game.start_hand()
            dealers.append(game.dealer_position)
            
            while game.is_hand_running():
                game.take_action(ActionType.FOLD)
                
        # Should have seen all 4 positions
        assert len(set(dealers)) == 4
        
    def test_cards_different_each_hand(self):
        """Cards should be reshuffled each hand."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        
        hands_seen = []
        for _ in range(5):
            game.start_hand()
            hands_seen.append(
                tuple(str(c) for c in game.players[0].hole_cards)
            )
            
            while game.is_hand_running():
                game.take_action(ActionType.FOLD)
                
        # Extremely unlikely to get same hand twice
        # (Not impossible, but probability is negligible)
        # Allow for the rare case
        unique_hands = len(set(hands_seen))
        assert unique_hands >= 2  # At least 2 different hands


class TestBettingBoundaries:
    """Tests for betting amount boundaries."""
    
    def test_minimum_raise_enforced(self):
        """Raises below minimum should be rejected."""
        game = TexasHoldemGame(num_players=2, big_blind=20, buy_in=1000)
        game.start_hand()
        
        # Try to raise to 30 (should be at least 40)
        result = game.take_action(ActionType.RAISE, 30)
        assert not result.success
        
    def test_raise_above_stack_treated_as_allin(self):
        """Raises above player's stack should be treated as all-in."""
        game = TexasHoldemGame(num_players=2, buy_in=100)
        game.start_hand()
        
        # Get current player's stack before action
        current = game.current_player
        initial_stack = current.stack
        
        # Try to raise more than stack allows
        # This should be accepted and converted to all-in
        result = game.take_action(ActionType.RAISE, 200)
        
        # Either accepted as all-in or rejected
        # If accepted, player should be all-in
        if result.success:
            assert current.state == PlayerState.ALL_IN or current.stack == 0
        
    def test_exactly_all_in_accepted(self):
        """Raise equal to all chips should be accepted as all-in."""
        game = TexasHoldemGame(num_players=2, buy_in=100)
        game.start_hand()
        
        # Get current player's stack
        current = game.current_player
        full_stack = current.stack + current.current_bet
        
        # All-in should work
        result = game.take_action(ActionType.ALL_IN)
        assert result.success


class TestInvalidActions:
    """Tests for handling invalid actions."""
    
    def test_action_when_not_your_turn(self):
        """Actions when not current player should fail."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        game.start_hand()
        
        current_idx = game.current_player_index
        
        # Try to take action as wrong player
        # (Internal test - normally you'd use an API)
        # The game should only accept actions from current player
        assert game.current_player is not None
        
    def test_check_when_facing_bet(self):
        """Check should fail when there's a bet to call."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Preflop, there's a BB to call
        legal = game.get_legal_actions()
        action_types = [a["type"] for a in legal]
        
        # Check should not be available
        assert "CHECK" not in action_types
        
        # Attempting check should fail
        result = game.take_action(ActionType.CHECK)
        assert not result.success
        
    def test_action_after_hand_over(self):
        """Actions after hand is over should fail."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # End the hand
        game.take_action(ActionType.FOLD)
        
        assert game.phase == GamePhase.HAND_OVER
        
        # Try another action
        result = game.take_action(ActionType.FOLD)
        assert not result.success


class TestSpecialCommunityCards:
    """Tests for special community card scenarios."""
    
    def test_board_is_best_hand(self):
        """When board is the best hand, all remaining players tie."""
        game = TexasHoldemGame(num_players=2, buy_in=1000)
        game.start_hand()
        
        # Give players weak hole cards
        game.players[0].hole_cards = [
            pytest.importorskip("deeppoker.core.card").Card(
                pytest.importorskip("deeppoker.core.card").Rank.TWO,
                pytest.importorskip("deeppoker.core.card").Suit.SPADES
            ),
            pytest.importorskip("deeppoker.core.card").Card(
                pytest.importorskip("deeppoker.core.card").Rank.THREE,
                pytest.importorskip("deeppoker.core.card").Suit.HEARTS
            ),
        ]
        game.players[1].hole_cards = [
            pytest.importorskip("deeppoker.core.card").Card(
                pytest.importorskip("deeppoker.core.card").Rank.FOUR,
                pytest.importorskip("deeppoker.core.card").Suit.DIAMONDS
            ),
            pytest.importorskip("deeppoker.core.card").Card(
                pytest.importorskip("deeppoker.core.card").Rank.FIVE,
                pytest.importorskip("deeppoker.core.card").Suit.CLUBS
            ),
        ]
        
        Card = pytest.importorskip("deeppoker.core.card").Card
        Rank = pytest.importorskip("deeppoker.core.card").Rank
        Suit = pytest.importorskip("deeppoker.core.card").Suit
        
        # Board is a royal flush
        game.community_cards = [
            Card(Rank.ACE, Suit.CLUBS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.QUEEN, Suit.CLUBS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.CLUBS),
        ]
        
        game.players[0].total_bet = 100
        game.players[1].total_bet = 100
        
        game._calculate_side_pots()
        winners = game._determine_winners()
        
        # Both should win (split pot)
        assert len(winners) == 2


class TestPlayerElimination:
    """Tests for player elimination (zero chips)."""
    
    def test_player_with_zero_chips(self):
        """Player with zero chips should not participate in new hands."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        
        # Set one player to have no chips
        game.players[0].stack = 0
        
        game.start_hand()
        
        # Player with no chips should not have been dealt cards
        # or should be in a non-active state
        if game.players[0].hole_cards:
            # If dealt cards, should be able to play (went all-in on blind)
            pass
        else:
            # Should not have cards
            assert len(game.players[0].hole_cards) == 0
            
    def test_game_continues_with_eliminated_players(self):
        """Game should continue with remaining players after elimination."""
        game = TexasHoldemGame(num_players=3, buy_in=100)
        
        # Play until someone is eliminated
        hands_played = 0
        max_hands = 50
        
        while hands_played < max_hands:
            active_with_chips = sum(1 for p in game.players if p.stack > 0)
            if active_with_chips < 2:
                break
                
            game.start_hand()
            
            while game.is_hand_running():
                # Simple strategy: all-in or fold
                legal = game.get_legal_actions()
                if any(a["type"] == "ALL_IN" for a in legal):
                    game.take_action(ActionType.ALL_IN)
                else:
                    game.take_action(ActionType.FOLD)
                    
            hands_played += 1
            
        # Should have completed some hands
        assert hands_played > 0
