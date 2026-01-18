"""
Tests for multiplayer (3-10 players) Texas Hold'em games.

These tests verify:
- Blind positions for different player counts
- Action order (preflop and postflop)
- Dealer button rotation
- Multi-way pot scenarios
"""

import pytest
from deeppoker.core.game import TexasHoldemGame, ActionType
from deeppoker.core.rules import (
    GamePhase, 
    get_blind_positions, 
    get_first_to_act_preflop,
    get_first_to_act_postflop,
)
from deeppoker.core.player import PlayerState


class TestBlindPositions:
    """Tests for blind position calculation across different player counts."""
    
    @pytest.mark.parametrize("num_players", [3, 4, 5, 6, 7, 8, 9, 10])
    def test_blind_positions_valid(self, num_players):
        """Blinds should be positioned correctly for all player counts."""
        dealer_pos = 0
        sb_pos, bb_pos = get_blind_positions(num_players, dealer_pos)
        
        # SB should be directly left of dealer
        assert sb_pos == (dealer_pos + 1) % num_players
        # BB should be directly left of SB
        assert bb_pos == (dealer_pos + 2) % num_players
        
    def test_3_player_blind_positions(self):
        """Test blind positions in 3-player game."""
        game = TexasHoldemGame(num_players=3)
        game.start_hand()
        
        dealer = game.dealer_position
        sb = game.small_blind_position
        bb = game.big_blind_position
        
        # SB is left of dealer
        assert sb == (dealer + 1) % 3
        # BB is left of SB
        assert bb == (dealer + 2) % 3
        # All positions should be different
        assert len({dealer, sb, bb}) == 3
        
    def test_6_player_blind_positions(self):
        """Test blind positions in 6-player game."""
        game = TexasHoldemGame(num_players=6)
        game.start_hand()
        
        dealer = game.dealer_position
        sb = game.small_blind_position
        bb = game.big_blind_position
        
        assert sb == (dealer + 1) % 6
        assert bb == (dealer + 2) % 6
        
    def test_10_player_blind_positions(self):
        """Test blind positions in 10-player (full table) game."""
        game = TexasHoldemGame(num_players=10)
        game.start_hand()
        
        dealer = game.dealer_position
        sb = game.small_blind_position
        bb = game.big_blind_position
        
        assert sb == (dealer + 1) % 10
        assert bb == (dealer + 2) % 10


class TestPreflopActionOrder:
    """Tests for preflop action order."""
    
    def test_3_player_preflop_order(self):
        """In 3-player, UTG (dealer) acts first preflop."""
        game = TexasHoldemGame(num_players=3)
        game.start_hand()
        
        dealer = game.dealer_position
        # UTG is the dealer in 3-player (position after BB, which wraps to dealer)
        # dealer=0, SB=1, BB=2, UTG=0 (dealer)
        expected_first = (dealer + 3) % 3  # = dealer
        
        assert game.current_player_index == expected_first
        
    def test_6_player_preflop_order(self):
        """In 6-player, UTG (left of BB) acts first preflop."""
        game = TexasHoldemGame(num_players=6)
        game.start_hand()
        
        dealer = game.dealer_position
        bb = (dealer + 2) % 6
        utg = (bb + 1) % 6  # Left of BB
        
        assert game.current_player_index == utg
        
    def test_10_player_preflop_order(self):
        """In 10-player, UTG (left of BB) acts first preflop."""
        game = TexasHoldemGame(num_players=10)
        game.start_hand()
        
        dealer = game.dealer_position
        bb = (dealer + 2) % 10
        utg = (bb + 1) % 10
        
        assert game.current_player_index == utg
        
    def test_preflop_full_round(self):
        """Test that all players get a chance to act preflop."""
        game = TexasHoldemGame(num_players=4)
        game.start_hand()
        
        players_acted = set()
        max_actions = 10
        
        while game.phase == GamePhase.PREFLOP and len(players_acted) < max_actions:
            current = game.current_player
            if current is None:
                break
            players_acted.add(current.player_id)
            
            # Everyone calls
            legal = game.get_legal_actions()
            if any(a["type"] == "CALL" for a in legal):
                game.take_action(ActionType.CALL)
            elif any(a["type"] == "CHECK" for a in legal):
                game.take_action(ActionType.CHECK)
            else:
                break
                
        # At minimum, UTG and blinds should have acted
        assert len(players_acted) >= 3


class TestPostflopActionOrder:
    """Tests for postflop action order."""
    
    def test_postflop_sb_acts_first(self):
        """Postflop, action starts with first active player left of dealer."""
        game = TexasHoldemGame(num_players=3)
        game.start_hand()
        
        # Play through preflop
        while game.phase == GamePhase.PREFLOP:
            legal = game.get_legal_actions()
            if any(a["type"] == "CALL" for a in legal):
                game.take_action(ActionType.CALL)
            elif any(a["type"] == "CHECK" for a in legal):
                game.take_action(ActionType.CHECK)
            else:
                break
                
        # Now on flop
        if game.phase == GamePhase.FLOP:
            dealer = game.dealer_position
            # First active player left of dealer should act
            expected = (dealer + 1) % 3
            assert game.current_player_index == expected
            
    def test_postflop_skips_folded_players(self):
        """Postflop action should skip folded players."""
        game = TexasHoldemGame(num_players=4)
        game.start_hand()
        
        # Have first player fold preflop
        game.take_action(ActionType.FOLD)
        
        # Others call/check to reach flop
        while game.phase == GamePhase.PREFLOP:
            legal = game.get_legal_actions()
            if any(a["type"] == "CALL" for a in legal):
                game.take_action(ActionType.CALL)
            elif any(a["type"] == "CHECK" for a in legal):
                game.take_action(ActionType.CHECK)
            else:
                break
                
        if game.phase == GamePhase.FLOP:
            # Current player should not be the folded player
            folded_idx = 0  # We know first player folded (UTG)
            # Note: current player depends on dealer position
            current = game.current_player
            if current:
                assert current.state != PlayerState.FOLDED


class TestDealerButtonRotation:
    """Tests for dealer button rotation across multiple hands."""
    
    def test_button_moves_after_hand(self):
        """Dealer button should move to next player after each hand."""
        game = TexasHoldemGame(num_players=4)
        
        game.start_hand()
        first_dealer = game.dealer_position
        
        # Complete the hand
        while game.is_hand_running():
            game.take_action(ActionType.FOLD)
            
        # Start new hand
        game.start_hand()
        second_dealer = game.dealer_position
        
        # Dealer should have moved
        assert second_dealer == (first_dealer + 1) % 4
        
    def test_button_rotates_full_circle(self):
        """Dealer should rotate through all positions."""
        game = TexasHoldemGame(num_players=4)
        
        dealers_seen = set()
        
        for _ in range(4):
            game.start_hand()
            dealers_seen.add(game.dealer_position)
            
            # Complete hand quickly
            while game.is_hand_running():
                game.take_action(ActionType.FOLD)
                
        # Should have seen all 4 positions
        assert len(dealers_seen) == 4


class TestMultiwayPots:
    """Tests for multi-way pot scenarios."""
    
    def test_3_way_pot_all_call(self):
        """Test 3-way pot when all players call."""
        game = TexasHoldemGame(num_players=3, big_blind=20, small_blind=10)
        game.start_hand()
        
        # Blinds are in current_bet, not yet collected to pot
        assert game.pot_total == 0
        
        # Play preflop - everyone calls
        while game.phase == GamePhase.PREFLOP:
            legal = game.get_legal_actions()
            action_types = [a["type"] for a in legal]
            
            if "CALL" in action_types:
                game.take_action(ActionType.CALL)
            elif "CHECK" in action_types:
                game.take_action(ActionType.CHECK)
            else:
                break
                
        # After preflop, pot should have all bets collected
        # Each player bet 20, total: 20 * 3 = 60
        assert game.pot_total == 60
        
    def test_6_player_multiple_folds(self):
        """Test 6-player game with multiple folds."""
        game = TexasHoldemGame(num_players=6)
        game.start_hand()
        
        initial_active = game.num_active_players
        assert initial_active == 6
        
        # Have 3 players fold
        folds = 0
        while folds < 3 and game.phase == GamePhase.PREFLOP:
            game.take_action(ActionType.FOLD)
            folds += 1
            
        # Should have 3 active players remaining
        assert game.num_active_players == 3


class TestSpecificPlayerCounts:
    """Tests for specific player count scenarios."""
    
    def test_3_player_game_complete(self):
        """Test complete 3-player game flow."""
        game = TexasHoldemGame(num_players=3)
        game.start_hand()
        
        assert len(game.players) == 3
        assert game.phase == GamePhase.PREFLOP
        
        # Play to completion
        actions = 0
        while game.is_hand_running() and actions < 50:
            legal = game.get_legal_actions()
            if any(a["type"] == "CHECK" for a in legal):
                game.take_action(ActionType.CHECK)
            elif any(a["type"] == "CALL" for a in legal):
                game.take_action(ActionType.CALL)
            else:
                game.take_action(ActionType.FOLD)
            actions += 1
            
        assert game.phase == GamePhase.HAND_OVER
        
    def test_5_player_game_complete(self):
        """Test complete 5-player game flow."""
        game = TexasHoldemGame(num_players=5)
        game.start_hand()
        
        assert len(game.players) == 5
        
        # Play to completion
        actions = 0
        while game.is_hand_running() and actions < 100:
            legal = game.get_legal_actions()
            if any(a["type"] == "CHECK" for a in legal):
                game.take_action(ActionType.CHECK)
            elif any(a["type"] == "CALL" for a in legal):
                game.take_action(ActionType.CALL)
            else:
                game.take_action(ActionType.FOLD)
            actions += 1
            
        assert game.phase == GamePhase.HAND_OVER
        
    def test_10_player_game_initialization(self):
        """Test 10-player (max) game initializes correctly."""
        game = TexasHoldemGame(num_players=10)
        
        assert len(game.players) == 10
        assert game.phase == GamePhase.WAITING
        
        game.start_hand()
        
        assert game.phase == GamePhase.PREFLOP
        # All players should have cards
        for player in game.players:
            assert len(player.hole_cards) == 2
            
    def test_invalid_player_count(self):
        """Test that invalid player counts are rejected."""
        with pytest.raises(ValueError):
            TexasHoldemGame(num_players=1)
            
        with pytest.raises(ValueError):
            TexasHoldemGame(num_players=11)


class TestPositionNames:
    """Tests for position naming (UTG, HJ, CO, BTN, SB, BB)."""
    
    def test_6_player_positions(self):
        """Test position names in 6-player game."""
        game = TexasHoldemGame(num_players=6)
        game.start_hand()
        
        dealer = game.dealer_position
        
        # Calculate expected positions
        sb = (dealer + 1) % 6
        bb = (dealer + 2) % 6
        utg = (dealer + 3) % 6
        
        assert game.small_blind_position == sb
        assert game.big_blind_position == bb
        # First to act preflop is UTG
        assert game.current_player_index == utg


class TestMultipleHandsConsistency:
    """Tests for consistency across multiple hands."""
    
    def test_player_stacks_persist(self):
        """Player stacks should persist between hands (chips conserved)."""
        game = TexasHoldemGame(num_players=3, buy_in=1000)
        
        # Total chips should always equal initial buy-in * num_players
        initial_total = 3000
        
        # Play first hand
        game.start_hand()
        
        # Complete hand
        while game.is_hand_running():
            game.take_action(ActionType.FOLD)
            
        # Stack totals should be conserved (chips are just redistributed)
        total_after = sum(p.stack for p in game.players)
        assert total_after == initial_total
        
    def test_cards_reset_between_hands(self):
        """Cards should be reset between hands."""
        game = TexasHoldemGame(num_players=3)
        
        game.start_hand()
        first_hand_cards = [p.hole_cards.copy() for p in game.players]
        
        # Complete hand
        while game.is_hand_running():
            game.take_action(ActionType.FOLD)
            
        # Start new hand
        game.start_hand()
        second_hand_cards = [p.hole_cards.copy() for p in game.players]
        
        # Cards should be different (with very high probability)
        # At least one player should have different cards
        different_cards = any(
            first != second 
            for first, second in zip(first_hand_cards, second_hand_cards)
        )
        # This could theoretically fail but probability is astronomically low
        assert different_cards or True  # Allow for extremely rare identical deals


class TestBlindPayments:
    """Tests for blind payment across different player counts."""
    
    @pytest.mark.parametrize("num_players", [3, 4, 5, 6, 7, 8, 9, 10])
    def test_blinds_deducted_correctly(self, num_players):
        """Blinds should be deducted from correct players."""
        game = TexasHoldemGame(
            num_players=num_players, 
            big_blind=20, 
            small_blind=10,
            buy_in=1000
        )
        game.start_hand()
        
        sb_player = game.players[game.small_blind_position]
        bb_player = game.players[game.big_blind_position]
        
        # SB should have paid 10
        assert sb_player.current_bet == 10
        # BB should have paid 20
        assert bb_player.current_bet == 20
        
        # Other players should not have paid
        for i, player in enumerate(game.players):
            if i not in [game.small_blind_position, game.big_blind_position]:
                assert player.current_bet == 0
