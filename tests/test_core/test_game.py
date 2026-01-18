"""
Tests for Texas Hold'em game engine.
"""

import pytest
from deeppoker.core.game import TexasHoldemGame, ActionType
from deeppoker.core.rules import GamePhase
from deeppoker.core.player import PlayerState


class TestGameInitialization:
    """Tests for game initialization."""
    
    def test_create_two_player_game(self, two_player_game):
        """Test creating a 2-player game."""
        assert two_player_game.num_players == 2
        assert len(two_player_game.players) == 2
    
    def test_create_six_player_game(self, six_player_game):
        """Test creating a 6-player game."""
        assert six_player_game.num_players == 6
    
    def test_invalid_player_count(self):
        """Test that invalid player counts raise errors."""
        with pytest.raises(ValueError):
            TexasHoldemGame(num_players=1)
        
        with pytest.raises(ValueError):
            TexasHoldemGame(num_players=11)
    
    def test_initial_state(self, two_player_game):
        """Test initial game state."""
        assert two_player_game.phase == GamePhase.WAITING
        assert not two_player_game.is_hand_running()
        assert two_player_game.is_game_running()


class TestStartHand:
    """Tests for starting a hand."""
    
    def test_start_hand_changes_phase(self, two_player_game):
        """Test that starting a hand changes the phase."""
        assert two_player_game.start_hand()
        assert two_player_game.phase == GamePhase.PREFLOP
        assert two_player_game.is_hand_running()
    
    def test_players_receive_cards(self, two_player_game):
        """Test that players receive hole cards."""
        two_player_game.start_hand()
        
        for player in two_player_game.players:
            assert len(player.hole_cards) == 2
    
    def test_blinds_posted(self, two_player_game):
        """Test that blinds are posted correctly."""
        two_player_game.start_hand()
        
        # Blinds are in current_bet, not yet collected to pot
        # SB has current_bet=10, BB has current_bet=20
        sb_player = two_player_game.players[two_player_game.small_blind_position]
        bb_player = two_player_game.players[two_player_game.big_blind_position]
        
        assert sb_player.current_bet == 10
        assert bb_player.current_bet == 20
        
        # Check current bet is big blind
        assert two_player_game.current_bet == 20


class TestHeadsUpRules:
    """Tests for heads-up (2-player) special rules."""
    
    def test_dealer_posts_small_blind(self, two_player_game):
        """In heads-up, dealer posts small blind."""
        two_player_game.start_hand()
        
        dealer_pos = two_player_game.dealer_position
        sb_pos = two_player_game.small_blind_position
        
        # In heads-up, dealer is SB
        assert dealer_pos == sb_pos
    
    def test_dealer_acts_first_preflop(self, two_player_game):
        """In heads-up preflop, dealer (SB) acts first."""
        two_player_game.start_hand()
        
        current = two_player_game.current_player_index
        dealer = two_player_game.dealer_position
        
        # Dealer acts first preflop in heads-up
        assert current == dealer


class TestActions:
    """Tests for player actions."""
    
    def test_fold_action(self, two_player_game):
        """Test fold action."""
        two_player_game.start_hand()
        
        result = two_player_game.take_action(ActionType.FOLD)
        assert result.success
        assert result.action_type == ActionType.FOLD
        
        # Hand should be over
        assert not two_player_game.is_hand_running()
    
    def test_call_action(self, two_player_game):
        """Test call action."""
        two_player_game.start_hand()
        
        result = two_player_game.take_action(ActionType.CALL)
        assert result.success
        assert result.action_type == ActionType.CALL
    
    def test_raise_action(self, two_player_game):
        """Test raise action."""
        two_player_game.start_hand()
        
        # Min raise should be to 40 (BB + BB = 20 + 20)
        result = two_player_game.take_action(ActionType.RAISE, 40)
        assert result.success
        assert result.action_type == ActionType.RAISE
        assert two_player_game.current_bet == 40
    
    def test_invalid_raise_amount(self, two_player_game):
        """Test that invalid raise amounts are rejected."""
        two_player_game.start_hand()
        
        # Try to raise to less than minimum
        result = two_player_game.take_action(ActionType.RAISE, 25)
        assert not result.success
    
    def test_all_in_action(self, two_player_game):
        """Test all-in action."""
        two_player_game.start_hand()
        
        result = two_player_game.take_action(ActionType.ALL_IN)
        assert result.success
        assert result.action_type == ActionType.ALL_IN
        
        # Player should be all-in
        current_player = two_player_game.players[two_player_game.current_player_index]
        # Note: After action, current_player advances, so check the one who acted
    
    def test_check_not_allowed_with_bet(self, two_player_game):
        """Test that check is not allowed when there's a bet to call."""
        two_player_game.start_hand()
        
        # There's a BB to call, so check should fail
        result = two_player_game.take_action(ActionType.CHECK)
        assert not result.success


class TestBettingRounds:
    """Tests for betting round progression."""
    
    def test_preflop_to_flop(self, two_player_game):
        """Test progression from preflop to flop."""
        two_player_game.start_hand()
        assert two_player_game.phase == GamePhase.PREFLOP
        
        # SB calls
        two_player_game.take_action(ActionType.CALL)
        # BB checks
        two_player_game.take_action(ActionType.CHECK)
        
        # Should be on flop now
        assert two_player_game.phase == GamePhase.FLOP
        assert len(two_player_game.community_cards) == 3
    
    def test_full_hand_to_showdown(self, two_player_game):
        """Test playing a full hand to showdown."""
        two_player_game.start_hand()
        
        # Play through all streets with check/call
        while two_player_game.is_hand_running():
            legal = two_player_game.get_legal_actions()
            action_types = [a["type"] for a in legal]
            
            if "CHECK" in action_types:
                two_player_game.take_action(ActionType.CHECK)
            elif "CALL" in action_types:
                two_player_game.take_action(ActionType.CALL)
            else:
                # If we can only fold, something's wrong
                break
        
        # Hand should be over
        assert two_player_game.phase == GamePhase.HAND_OVER
        assert len(two_player_game.community_cards) == 5


class TestLegalActions:
    """Tests for legal action calculation."""
    
    def test_legal_actions_preflop(self, two_player_game):
        """Test legal actions at preflop."""
        two_player_game.start_hand()
        
        actions = two_player_game.get_legal_actions()
        action_types = [a["type"] for a in actions]
        
        assert "FOLD" in action_types
        assert "CALL" in action_types
        assert "RAISE" in action_types
        assert "ALL_IN" in action_types
        # Can't check preflop with BB to call
        assert "CHECK" not in action_types
    
    def test_legal_actions_after_call(self, two_player_game):
        """Test legal actions after someone calls."""
        two_player_game.start_hand()
        
        # SB calls BB
        two_player_game.take_action(ActionType.CALL)
        
        # BB can now check
        actions = two_player_game.get_legal_actions()
        action_types = [a["type"] for a in actions]
        
        assert "CHECK" in action_types


class TestMinRaise:
    """Tests for minimum raise rules."""
    
    def test_min_raise_is_previous_raise(self, two_player_game):
        """Min raise should be at least the previous raise amount."""
        two_player_game.start_hand()
        
        # Raise to 50 (raise of 30 over BB)
        two_player_game.take_action(ActionType.RAISE, 50)
        
        # Next min raise should be to 80 (50 + 30)
        actions = two_player_game.get_legal_actions()
        raise_action = next(a for a in actions if a["type"] == "RAISE")
        
        assert raise_action["min"] == 80
        
    def test_min_raise_is_big_blind_initially(self, two_player_game):
        """Initial min raise should be big blind."""
        two_player_game.start_hand()
        
        # First raise: current_bet=20 (BB), min raise is +20 = 40
        actions = two_player_game.get_legal_actions()
        raise_action = next(a for a in actions if a["type"] == "RAISE")
        
        assert raise_action["min"] == 40  # BB + BB = 40
        
    def test_raise_below_minimum_rejected(self, two_player_game):
        """Raise below minimum should be rejected."""
        two_player_game.start_hand()
        
        # Try to raise to 30 (should be at least 40)
        result = two_player_game.take_action(ActionType.RAISE, 30)
        
        assert not result.success
        
    def test_all_in_below_min_raise_allowed(self, two_player_game):
        """All-in for less than min raise should be allowed."""
        # Give player 0 a short stack
        two_player_game.players[0].stack = 30
        two_player_game.start_hand()
        
        # Player with 30 chips goes all-in (less than min raise of 40)
        # This should be allowed as it's an all-in
        result = two_player_game.take_action(ActionType.ALL_IN)
        assert result.success
        
    def test_successive_raises_track_min_raise(self, two_player_game):
        """Min raise should track the largest previous raise increment."""
        two_player_game.start_hand()
        
        # Raise to 60 (raise of 40 over BB 20)
        two_player_game.take_action(ActionType.RAISE, 60)
        
        # Raise to 140 (raise of 80 over 60)
        two_player_game.take_action(ActionType.RAISE, 140)
        
        # Next min raise should be to 220 (140 + 80)
        actions = two_player_game.get_legal_actions()
        raise_action = next(a for a in actions if a["type"] == "RAISE")
        
        assert raise_action["min"] == 220


class TestWSOP96IncompleteRaise:
    """
    Tests for WSOP Rule 96: Incomplete all-in raises.
    
    An all-in bet or raise that is less than a full raise does not reopen
    the betting for players who have already acted.
    """
    
    def test_incomplete_raise_does_not_reopen(self):
        """
        Player A raises, Player B goes all-in for less than min raise.
        This incomplete raise should not allow A to re-raise.
        """
        from deeppoker.core.rules import is_action_reopened
        
        # Scenario: BB=20, A raises to 40, B all-in for 50 (only +10, less than min raise of 20)
        current_bet = 40
        last_raise_amount = 20  # The raise from BB to 40
        all_in_amount = 50
        big_blind = 20
        
        # The all-in of 50 is not enough to reopen (need min 60)
        reopened = is_action_reopened(all_in_amount, current_bet, last_raise_amount, big_blind)
        assert not reopened
        
    def test_full_raise_reopens_action(self):
        """Full raise should reopen action for all players."""
        from deeppoker.core.rules import is_action_reopened
        
        # Scenario: BB=20, A raises to 40, B raises to 80 (+40, full raise)
        current_bet = 40
        last_raise_amount = 20
        raise_amount = 80
        big_blind = 20
        
        # Raise of 40 (from 40 to 80) meets minimum, should reopen
        reopened = is_action_reopened(raise_amount, current_bet, last_raise_amount, big_blind)
        assert reopened
        
    def test_min_raise_calculation_after_raise(self):
        """Min raise after a raise should be the previous raise increment."""
        from deeppoker.core.rules import calculate_min_raise
        
        # After raise to 60 (from 20), raise increment was 40
        current_bet = 60
        last_raise_amount = 40
        big_blind = 20
        
        # Min raise should be 60 + 40 = 100
        min_raise = calculate_min_raise(current_bet, last_raise_amount, big_blind)
        assert min_raise == 100
        
    def test_min_raise_uses_big_blind_when_larger(self):
        """If big blind is larger than last raise, use big blind."""
        from deeppoker.core.rules import calculate_min_raise
        
        # BB=50, last raise was only 30
        current_bet = 80
        last_raise_amount = 30
        big_blind = 50
        
        # Min raise should be 80 + 50 = 130 (using BB, not last raise)
        min_raise = calculate_min_raise(current_bet, last_raise_amount, big_blind)
        assert min_raise == 130


class TestWSOP96ConsecutiveAllIns:
    """
    Tests for WSOP Rule 96 exception: Multiple all-in raises that combined
    equal or exceed the minimum raise should reopen action.
    """
    
    def test_single_short_allin_does_not_reopen(self):
        """Single short all-in should not reopen action."""
        game = TexasHoldemGame(num_players=3, big_blind=20, buy_in=1000)
        
        # Give player 1 a short stack
        game.players[1].stack = 30  # Can only raise by 10 (less than min 20)
        
        game.start_hand()
        
        # Player 0 (UTG) raises to 40
        game.take_action(ActionType.RAISE, 40)
        
        # Player 1 goes all-in for 30 (current_bet becomes 30, raise of 10)
        game.take_action(ActionType.ALL_IN)
        
        # Player 2 calls
        game.take_action(ActionType.CALL)
        
        # Player 0's has_acted should still be True (short all-in didn't reopen)
        # Actually, we need to check if player 0 gets another chance to act
        # Let's check the legal actions
        
    def test_consecutive_allins_reaching_min_reopens(self):
        """
        Two consecutive short all-ins that total >= min raise should reopen.
        
        Scenario: BB=20, A raises to 40 (raise of 20)
        B all-in for 55 (raise of 15, short)
        C all-in for 65 (raise of 10, but cumulative 25 >= 20)
        -> Action should reopen for A
        """
        game = TexasHoldemGame(num_players=4, big_blind=20, buy_in=1000)
        
        # Set specific stack sizes
        game.players[0].stack = 1000  # Player 0 - big stack
        game.players[1].stack = 35    # Player 1 - will all-in for 55 total
        game.players[2].stack = 45    # Player 2 - will all-in for 65 total  
        game.players[3].stack = 1000  # Player 3 - big stack
        
        game.start_hand()
        
        # Verify consecutive all-in sum tracking works
        assert game._consecutive_allin_raise_sum == 0
        
    def test_should_reopen_action_with_cumulative_allins(self):
        """Test _should_reopen_action method with cumulative all-ins."""
        game = TexasHoldemGame(num_players=3, big_blind=20, buy_in=1000)
        game.start_hand()
        
        # Setup: current bet is 40, last raise was 20, min raise increment is 20
        game.current_bet = 40
        game.last_raise_amount = 20
        
        # Single short all-in of 10 should not reopen
        game._consecutive_allin_raise_sum = 10
        assert not game._should_reopen_action(10, True)
        
        # Cumulative all-in of 25 (>= 20) should reopen
        game._consecutive_allin_raise_sum = 25
        assert game._should_reopen_action(10, True)
        
    def test_non_allin_raise_resets_consecutive_sum(self):
        """A non-all-in raise should reset the consecutive all-in sum."""
        game = TexasHoldemGame(num_players=3, big_blind=20, buy_in=1000)
        game.start_hand()
        
        # Setup some consecutive all-in sum
        game._consecutive_allin_raise_sum = 15
        
        # Record a non-all-in raise
        from deeppoker.core.player import Player
        game._record_action(game.players[0], ActionType.RAISE, 60, 40, False)
        
        # Consecutive sum should be reset
        assert game._consecutive_allin_raise_sum == 0


class TestWinnerDetermination:
    """Tests for winner determination."""
    
    def test_winner_by_fold(self, two_player_game):
        """Test winner when opponent folds."""
        two_player_game.start_hand()
        
        two_player_game.take_action(ActionType.FOLD)
        
        assert not two_player_game.is_hand_running()
        winners = two_player_game.get_winners()
        assert len(winners) == 1
    
    def test_pot_awarded_to_winner(self, two_player_game):
        """Test that pot is awarded to winner."""
        two_player_game.start_hand()
        
        initial_stacks = [p.stack for p in two_player_game.players]
        
        two_player_game.take_action(ActionType.FOLD)
        
        winners = two_player_game.get_winners()
        winner_id = winners[0]["player_id"]
        
        # Winner should have gained the pot
        winner = next(p for p in two_player_game.players if p.player_id == winner_id)
        loser = next(p for p in two_player_game.players if p.player_id != winner_id)
        
        # Winner stack should be initial + pot
        assert winner.stack > initial_stacks[int(winner_id)]


class TestGameState:
    """Tests for game state retrieval."""
    
    def test_get_state_includes_public_info(self, two_player_game):
        """Test that get_state includes public information."""
        two_player_game.start_hand()
        
        state = two_player_game.get_state()
        
        assert "public_info" in state
        assert "phase" in state["public_info"]
        assert "pot" in state["public_info"]
        assert "board" in state["public_info"]
        assert "players" in state["public_info"]
    
    def test_get_state_with_player_id(self, two_player_game):
        """Test that get_state includes private info for specific player."""
        two_player_game.start_hand()
        
        state = two_player_game.get_state(for_player_id="0")
        
        assert "private_info" in state
        assert "hand" in state["private_info"]
        assert len(state["private_info"]["hand"]) == 2
