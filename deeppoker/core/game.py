"""
Texas Hold'em Game Engine - State Machine Implementation.

This module implements the core game logic for Texas Hold'em poker.
It handles:
- Game state management (phases: preflop, flop, turn, river, showdown)
- Player actions (fold, check, call, bet, raise, all-in)
- Blind posting and dealer button rotation
- Heads-up special rules
- Side pot calculations for all-in situations

Reference: WSOP Official Tournament Rules
"""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import logging

from deeppoker.core.card import Card, Deck
from deeppoker.core.player import Player, PlayerState
from deeppoker.core.hand import evaluate_hand, HandRank, get_hand_description
from deeppoker.core.rules import (
    GamePhase, ActionType,
    get_blind_positions, get_first_to_act_preflop, get_first_to_act_postflop,
    calculate_min_raise, is_valid_raise, is_action_reopened,
    DEFAULT_BIG_BLIND, DEFAULT_SMALL_BLIND, DEFAULT_BUY_IN,
    HOLE_CARDS, FLOP_CARDS, TURN_CARDS, RIVER_CARDS,
)


logger = logging.getLogger(__name__)


@dataclass
class Pot:
    """Represents a pot (main pot or side pot)."""
    amount: int = 0
    eligible_players: List[str] = field(default_factory=list)
    
    def add(self, amount: int) -> None:
        self.amount += amount


@dataclass 
class ActionResult:
    """Result of a player action."""
    success: bool
    message: str
    action_type: Optional[ActionType] = None
    amount: int = 0


@dataclass
class ActionRecord:
    """Records a player action for history tracking and WSOP Rule 96."""
    player_id: str
    action_type: ActionType
    amount: int  # Total bet amount
    raise_amount: int  # The raise increment (for raises only)
    is_all_in: bool
    phase: GamePhase


class TexasHoldemGame:
    """
    Texas Hold'em game engine implementing a state machine.
    
    Usage:
        game = TexasHoldemGame(num_players=6, big_blind=20, small_blind=10)
        game.start_hand()
        
        while game.is_hand_running():
            state = game.get_state()
            action = get_player_action(state)  # From UI or AI
            result = game.take_action(action['type'], action.get('amount', 0))
            
        winners = game.get_winners()
    """
    
    def __init__(
        self,
        num_players: int = 2,
        big_blind: int = DEFAULT_BIG_BLIND,
        small_blind: int = DEFAULT_SMALL_BLIND,
        buy_in: int = DEFAULT_BUY_IN,
        player_ids: Optional[List[str]] = None,
    ):
        """
        Initialize a new Texas Hold'em game.
        
        Args:
            num_players: Number of players (2-10)
            big_blind: Big blind amount
            small_blind: Small blind amount
            buy_in: Starting stack for each player
            player_ids: Optional list of player IDs
        """
        if num_players < 2 or num_players > 10:
            raise ValueError("Number of players must be 2-10")
        
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.buy_in = buy_in
        
        # Create players
        if player_ids is None:
            player_ids = [str(i) for i in range(num_players)]
        
        self.players: List[Player] = [
            Player(player_id=pid, stack=buy_in, seat=i)
            for i, pid in enumerate(player_ids)
        ]
        
        # Game state
        self.deck = Deck(shuffle=False)
        self.community_cards: List[Card] = []
        self.phase = GamePhase.WAITING
        self.hand_number = 0
        
        # Position tracking
        self.dealer_position = 0
        self.small_blind_position = 0
        self.big_blind_position = 0
        self.current_player_index = 0
        
        # Betting state
        self.current_bet = 0  # Current highest bet in the round
        self.last_raise_amount = 0  # Size of the last raise
        self.last_aggressor_index = -1  # Player who made the last raise
        self.min_raise = big_blind  # Minimum raise amount
        
        # Pot tracking
        self.pots: List[Pot] = [Pot()]
        
        # Track if betting round is complete
        self._players_to_act: List[int] = []
        
        # Hand history for replay
        self.hand_history: List[Dict[str, Any]] = []
        
        # Track actions in current betting round for WSOP Rule 96
        self.round_actions: List[ActionRecord] = []
        
        # Track consecutive all-in raises for WSOP Rule 96
        self._consecutive_allin_raise_sum: int = 0
    
    @property
    def num_players(self) -> int:
        """Number of players at the table."""
        return len(self.players)
    
    @property
    def num_active_players(self) -> int:
        """Number of players still in the hand."""
        return sum(1 for p in self.players if p.is_in_hand)
    
    @property
    def current_player(self) -> Optional[Player]:
        """The player whose turn it is to act."""
        if not self.is_hand_running():
            return None
        return self.players[self.current_player_index]
    
    @property
    def pot_total(self) -> int:
        """Total amount in all pots."""
        return sum(pot.amount for pot in self.pots)
    
    def is_game_running(self) -> bool:
        """Check if the game can continue (at least 2 players with chips)."""
        return sum(1 for p in self.players if p.stack > 0 or p.is_in_hand) >= 2
    
    def is_hand_running(self) -> bool:
        """Check if a hand is currently in progress."""
        return self.phase not in (GamePhase.WAITING, GamePhase.HAND_OVER)
    
    def start_hand(self) -> bool:
        """
        Start a new hand.
        
        Returns:
            True if hand started successfully, False otherwise
        """
        if not self.is_game_running():
            logger.warning("Cannot start hand: not enough players with chips")
            return False
        
        self.hand_number += 1
        logger.info(f"Starting hand #{self.hand_number}")
        
        # Reset for new hand
        self.deck = Deck(shuffle=True)
        self.community_cards = []
        self.pots = [Pot()]
        self.current_bet = 0
        self.last_raise_amount = 0
        self.last_aggressor_index = -1
        self.hand_history = []
        
        # Reset players
        for player in self.players:
            player.reset_for_new_hand()
        
        # Move dealer button
        self._move_dealer_button()
        
        # Post blinds
        self._post_blinds()
        
        # Deal hole cards
        self._deal_hole_cards()
        
        # Set first player to act
        self.phase = GamePhase.PREFLOP
        self._setup_betting_round()
        
        self._log_action("HAND_START", {
            "hand_number": self.hand_number,
            "dealer": self.dealer_position,
            "small_blind": self.small_blind_position,
            "big_blind": self.big_blind_position,
        })
        
        return True
    
    def _move_dealer_button(self) -> None:
        """Move the dealer button to the next active player."""
        # Find next player with chips
        start = (self.dealer_position + 1) % self.num_players
        for i in range(self.num_players):
            pos = (start + i) % self.num_players
            if self.players[pos].stack > 0:
                self.dealer_position = pos
                break
        
        # Calculate blind positions
        active_indices = [i for i, p in enumerate(self.players) if p.stack > 0]
        num_active = len(active_indices)
        
        self.small_blind_position, self.big_blind_position = get_blind_positions(
            num_active, 
            active_indices.index(self.dealer_position) if self.dealer_position in active_indices else 0
        )
        
        # Convert relative positions to actual seat indices
        self.small_blind_position = active_indices[self.small_blind_position]
        self.big_blind_position = active_indices[self.big_blind_position]
    
    def _post_blinds(self) -> None:
        """Post small and big blinds."""
        sb_player = self.players[self.small_blind_position]
        bb_player = self.players[self.big_blind_position]
        
        # Post small blind (bet() sets current_bet, which will be collected later)
        sb_amount = sb_player.bet(self.small_blind)
        sb_player.last_action = f"SB ${sb_amount}"
        
        # Post big blind
        bb_amount = bb_player.bet(self.big_blind)
        bb_player.last_action = f"BB ${bb_amount}"
        
        self.current_bet = self.big_blind
        self.last_raise_amount = self.big_blind
        
        logger.debug(f"Blinds posted: SB={sb_amount} BB={bb_amount}")
    
    def _deal_hole_cards(self) -> None:
        """Deal 2 hole cards to each active player."""
        for player in self.players:
            if player.stack > 0 or player.current_bet > 0:  # Has chips or posted blind
                cards = self.deck.deal(HOLE_CARDS)
                player.deal_cards(cards)
                player.state = PlayerState.ACTIVE
    
    def _setup_betting_round(self) -> None:
        """Setup the betting round for the current phase."""
        # Reset player bet tracking for the round
        # In preflop, don't reset current_bet because blinds are already posted
        if self.phase != GamePhase.PREFLOP:
            for player in self.players:
                player.reset_for_new_round()
        else:
            # For preflop, just reset has_acted flags
            for player in self.players:
                player.has_acted = False
                if player.state == PlayerState.ALL_IN:
                    player.has_acted = True
        
        self.current_bet = 0 if self.phase != GamePhase.PREFLOP else self.big_blind
        self.last_raise_amount = self.big_blind if self.phase == GamePhase.PREFLOP else 0
        self.min_raise = self.big_blind
        self.last_aggressor_index = -1
        
        # Reset action tracking for WSOP Rule 96
        self.round_actions = []
        self._consecutive_allin_raise_sum = 0
        
        # Determine first player to act
        active_indices = [i for i, p in enumerate(self.players) if p.is_in_hand]
        
        if self.phase == GamePhase.PREFLOP:
            # In heads-up: Dealer (SB) acts first preflop
            # In multi-way: UTG (left of BB) acts first
            if len(active_indices) == 2:
                # Heads-up: dealer acts first
                self.current_player_index = self.dealer_position
            else:
                # UTG: Left of big blind (dealer + 3)
                self.current_player_index = (self.dealer_position + 3) % self.num_players
                # Find next active player if this one is not active
                while not self.players[self.current_player_index].is_in_hand:
                    self.current_player_index = (self.current_player_index + 1) % self.num_players
        else:
            # Postflop: First active player left of dealer
            # In heads-up: BB (non-dealer) acts first
            self.current_player_index = (self.dealer_position + 1) % self.num_players
            # Find next active player if this one is not active
            while not self.players[self.current_player_index].is_in_hand:
                self.current_player_index = (self.current_player_index + 1) % self.num_players
        
        # Build list of players who need to act
        self._players_to_act = [i for i, p in enumerate(self.players) 
                                if p.is_active and p.stack > 0]
    
    def _advance_to_next_active_player(self) -> bool:
        """
        Advance to the next player who can act.
        
        Returns:
            True if there's a player to act, False if round is complete
        """
        # Check if only one player remains
        if self.num_active_players <= 1:
            self._end_hand_early()
            return False
        
        # Check if betting round is complete
        if self._is_betting_round_complete():
            self._end_betting_round()
            return self.is_hand_running()
        
        # Find next active player
        start = self.current_player_index
        for _ in range(self.num_players):
            self.current_player_index = (self.current_player_index + 1) % self.num_players
            player = self.players[self.current_player_index]
            
            if player.is_active and player.stack > 0:
                return True
        
        # No one can act
        self._end_betting_round()
        return self.is_hand_running()
    
    def _is_betting_round_complete(self) -> bool:
        """Check if the current betting round is complete."""
        active_players = [p for p in self.players if p.is_active]
        
        # All active players must have:
        # 1. Acted at least once
        # 2. Either matched the current bet or gone all-in
        for player in active_players:
            if not player.has_acted:
                return False
            if player.current_bet < self.current_bet and player.stack > 0:
                return False
        
        return True
    
    def _end_betting_round(self) -> None:
        """End the current betting round and advance to next phase."""
        # Collect bets into pot
        self._collect_bets_to_pot()
        
        # Check if we should go to showdown (everyone all-in or only one active)
        active_with_chips = [p for p in self.players if p.is_in_hand and p.stack > 0]
        
        if len(active_with_chips) <= 1:
            # Deal remaining cards and go to showdown
            self._deal_remaining_cards()
            self._go_to_showdown()
            return
        
        # Advance to next phase
        if self.phase == GamePhase.PREFLOP:
            self._deal_flop()
            self.phase = GamePhase.FLOP
        elif self.phase == GamePhase.FLOP:
            self._deal_turn()
            self.phase = GamePhase.TURN
        elif self.phase == GamePhase.TURN:
            self._deal_river()
            self.phase = GamePhase.RIVER
        elif self.phase == GamePhase.RIVER:
            self._go_to_showdown()
            return
        
        self._setup_betting_round()
    
    def _deal_flop(self) -> None:
        """Deal the flop (3 community cards)."""
        self.deck.burn()
        self.community_cards.extend(self.deck.deal(FLOP_CARDS))
        self._log_action("FLOP", {"cards": [str(c) for c in self.community_cards]})
    
    def _deal_turn(self) -> None:
        """Deal the turn (4th community card)."""
        self.deck.burn()
        self.community_cards.extend(self.deck.deal(TURN_CARDS))
        self._log_action("TURN", {"card": str(self.community_cards[-1])})
    
    def _deal_river(self) -> None:
        """Deal the river (5th community card)."""
        self.deck.burn()
        self.community_cards.extend(self.deck.deal(RIVER_CARDS))
        self._log_action("RIVER", {"card": str(self.community_cards[-1])})
    
    def _deal_remaining_cards(self) -> None:
        """Deal remaining community cards (when going directly to showdown)."""
        while len(self.community_cards) < 5:
            if len(self.community_cards) == 0:
                self.deck.burn()
                self.community_cards.extend(self.deck.deal(FLOP_CARDS))
            else:
                self.deck.burn()
                self.community_cards.extend(self.deck.deal(1))
    
    def _go_to_showdown(self) -> None:
        """Go to showdown and determine winner(s)."""
        self.phase = GamePhase.SHOWDOWN
        self._collect_bets_to_pot()
        self._calculate_side_pots()
        
        winners = self._determine_winners()
        self._distribute_pots(winners)
        
        self.phase = GamePhase.HAND_OVER
        self._log_action("SHOWDOWN", {"winners": winners})
    
    def _end_hand_early(self) -> None:
        """End the hand when only one player remains."""
        self._collect_bets_to_pot()
        
        # Find the remaining player
        remaining = [p for p in self.players if p.is_in_hand]
        if remaining:
            winner = remaining[0]
            winner.stack += self.pot_total
            
            self._log_action("WIN_BY_FOLD", {
                "winner": winner.player_id,
                "amount": self.pot_total
            })
        
        self.phase = GamePhase.HAND_OVER
    
    def _collect_bets_to_pot(self) -> None:
        """Collect all player bets into the pot."""
        for player in self.players:
            if player.current_bet > 0:
                self.pots[0].amount += player.current_bet
                player.current_bet = 0
    
    def _add_to_pot(self, amount: int) -> None:
        """Add amount to the current pot."""
        self.pots[0].amount += amount
    
    def _calculate_side_pots(self) -> None:
        """Calculate side pots for all-in situations."""
        # Get all players who contributed to the pot
        contributors = [(p, p.total_bet) for p in self.players if p.total_bet > 0]
        if not contributors:
            return
        
        # Sort by contribution amount
        contributors.sort(key=lambda x: x[1])
        
        # Reset pots
        self.pots = []
        prev_level = 0
        
        for player, bet_level in contributors:
            if bet_level > prev_level:
                # Create a new pot for this level
                pot_contribution = bet_level - prev_level
                eligible = [p.player_id for p, b in contributors 
                           if b >= bet_level and p.is_in_hand]
                
                if eligible:
                    pot_amount = pot_contribution * len([p for p, b in contributors if b >= bet_level])
                    self.pots.append(Pot(amount=pot_amount, eligible_players=eligible))
                
                prev_level = bet_level
    
    def _determine_winners(self) -> List[Dict[str, Any]]:
        """
        Determine winners for each pot.
        
        Returns:
            List of winner info dicts with player_id, amount won, and hand description
        """
        winners = []
        
        for pot in self.pots:
            if not pot.eligible_players:
                continue
            
            # Evaluate hands for eligible players
            player_hands = []
            for pid in pot.eligible_players:
                player = self._get_player_by_id(pid)
                if player and player.is_in_hand:
                    all_cards = player.hole_cards + self.community_cards
                    rank, hand_type, best_cards = evaluate_hand(all_cards)
                    player_hands.append({
                        "player": player,
                        "rank": rank,
                        "hand_type": hand_type,
                        "best_cards": best_cards,
                        "description": get_hand_description(all_cards)
                    })
            
            if not player_hands:
                continue
            
            # Find best hand(s)
            best_rank = min(h["rank"] for h in player_hands)
            pot_winners = [h for h in player_hands if h["rank"] == best_rank]
            
            # Split pot among winners
            split_amount = pot.amount // len(pot_winners)
            remainder = pot.amount % len(pot_winners)
            
            # WSOP Rule 73: Odd chip goes to the first player clockwise from the button
            # First, give each winner their split amount
            for winner in pot_winners:
                winners.append({
                    "player_id": winner["player"].player_id,
                    "amount": split_amount,
                    "hand_type": winner["hand_type"].name,
                    "description": winner["description"],
                    "cards": [str(c) for c in winner["best_cards"]]
                })
            
            # Distribute remainder chips according to WSOP Rule 73
            # Odd chips go to players closest to the left of the dealer button
            if remainder > 0:
                winner_pids = [w["player"].player_id for w in pot_winners]
                # Find winners in clockwise order from dealer
                for i in range(self.num_players):
                    pos = (self.dealer_position + 1 + i) % self.num_players
                    pid = self.players[pos].player_id
                    if pid in winner_pids:
                        # Give this winner one chip of remainder
                        for w in winners:
                            if w["player_id"] == pid:
                                w["amount"] += 1
                                break
                        remainder -= 1
                        if remainder == 0:
                            break
        
        return winners
    
    def _distribute_pots(self, winners: List[Dict[str, Any]]) -> None:
        """Distribute winnings to players."""
        for winner in winners:
            player = self._get_player_by_id(winner["player_id"])
            if player:
                player.stack += winner["amount"]
    
    def _get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        for player in self.players:
            if player.player_id == player_id:
                return player
        return None
    
    def take_action(self, action_type: ActionType, amount: int = 0) -> ActionResult:
        """
        Process a player action.
        
        Args:
            action_type: Type of action (FOLD, CHECK, CALL, BET, RAISE, ALL_IN)
            amount: Amount for BET/RAISE actions (total amount, not increment)
            
        Returns:
            ActionResult indicating success/failure and details
        """
        if not self.is_hand_running():
            return ActionResult(False, "No hand in progress")
        
        player = self.current_player
        if player is None:
            return ActionResult(False, "No current player")
        
        # Validate and execute action
        result = self._execute_action(player, action_type, amount)
        
        if result.success:
            player.has_acted = True
            self._log_action(action_type.value, {
                "player": player.player_id,
                "amount": result.amount
            })
            
            # Advance to next player
            self._advance_to_next_active_player()
        
        return result
    
    def _execute_action(self, player: Player, action_type: ActionType, amount: int) -> ActionResult:
        """Execute the specified action for the player."""
        chips_to_call = self.current_bet - player.current_bet
        
        if action_type == ActionType.FOLD:
            player.fold()
            return ActionResult(True, "Folded", ActionType.FOLD, 0)
        
        elif action_type == ActionType.CHECK:
            if chips_to_call > 0:
                return ActionResult(False, f"Cannot check, must call ${chips_to_call}")
            player.check()
            return ActionResult(True, "Checked", ActionType.CHECK, 0)
        
        elif action_type == ActionType.CALL:
            if chips_to_call <= 0:
                return ActionResult(False, "Nothing to call, use CHECK")
            actual = player.call(chips_to_call)
            return ActionResult(True, f"Called ${actual}", ActionType.CALL, actual)
        
        elif action_type == ActionType.BET:
            if self.current_bet > 0:
                return ActionResult(False, "Cannot bet when there's already a bet, use RAISE")
            if amount < self.big_blind:
                return ActionResult(False, f"Minimum bet is ${self.big_blind}")
            if amount > player.stack:
                return ActionResult(False, f"Cannot bet more than stack (${player.stack})")
            
            actual = player.raise_to(amount)
            self.current_bet = player.current_bet
            self.last_raise_amount = amount
            self.last_aggressor_index = self.current_player_index
            self._reset_actions_except_current()
            return ActionResult(True, f"Bet ${amount}", ActionType.BET, actual)
        
        elif action_type == ActionType.RAISE:
            if self.current_bet == 0:
                return ActionResult(False, "No bet to raise, use BET")
            
            min_raise_total = calculate_min_raise(
                self.current_bet, self.last_raise_amount, self.big_blind
            )
            
            is_all_in = amount >= player.stack + player.current_bet
            
            # All-in is always valid
            if is_all_in:
                amount = player.stack + player.current_bet  # All-in
            elif amount < min_raise_total:
                return ActionResult(
                    False, 
                    f"Minimum raise is to ${min_raise_total} (current: ${self.current_bet}, min raise: ${self.last_raise_amount})"
                )
            
            raise_increment = amount - self.current_bet
            actual = player.raise_to(amount)
            
            # Record action for WSOP Rule 96
            self._record_action(player, ActionType.RAISE, amount, raise_increment, is_all_in)
            
            # Check if this reopens action using WSOP Rule 96
            if self._should_reopen_action(raise_increment, is_all_in):
                self.last_raise_amount = raise_increment if raise_increment >= self.last_raise_amount else self._consecutive_allin_raise_sum
                self._reset_actions_except_current()
                # Reset consecutive all-in sum after reopening
                self._consecutive_allin_raise_sum = 0
            
            self.current_bet = player.current_bet
            self.last_aggressor_index = self.current_player_index
            
            return ActionResult(True, f"Raised to ${player.current_bet}", ActionType.RAISE, actual)
        
        elif action_type == ActionType.ALL_IN:
            if player.stack == 0:
                return ActionResult(False, "Already all-in")
            
            all_in_total = player.current_bet + player.stack
            actual = player.go_all_in()
            
            if all_in_total > self.current_bet:
                # Check if it's a raise
                raise_increment = all_in_total - self.current_bet
                
                # Record action for WSOP Rule 96
                self._record_action(player, ActionType.ALL_IN, all_in_total, raise_increment, True)
                
                # Check if this reopens action using WSOP Rule 96
                if self._should_reopen_action(raise_increment, True):
                    self.last_raise_amount = raise_increment if raise_increment >= self.last_raise_amount else self._consecutive_allin_raise_sum
                    self._reset_actions_except_current()
                    self._consecutive_allin_raise_sum = 0
                
                self.current_bet = all_in_total
                self.last_aggressor_index = self.current_player_index
            else:
                # Just calling, record as call
                self._record_action(player, ActionType.ALL_IN, all_in_total, 0, True)
            
            return ActionResult(True, f"All-in for ${all_in_total}", ActionType.ALL_IN, actual)
        
        return ActionResult(False, f"Unknown action: {action_type}")
    
    def _reset_actions_except_current(self) -> None:
        """Reset has_acted for all players except current (they need to act again after a raise)."""
        for i, player in enumerate(self.players):
            if i != self.current_player_index and player.is_active:
                player.has_acted = False
    
    def _record_action(
        self, 
        player: Player, 
        action_type: ActionType, 
        amount: int, 
        raise_amount: int,
        is_all_in: bool
    ) -> None:
        """Record an action for history tracking and WSOP Rule 96."""
        self.round_actions.append(ActionRecord(
            player_id=player.player_id,
            action_type=action_type,
            amount=amount,
            raise_amount=raise_amount,
            is_all_in=is_all_in,
            phase=self.phase,
        ))
        
        # Track consecutive all-in raises for WSOP Rule 96
        if is_all_in and raise_amount > 0:
            # This is an all-in raise, add to consecutive sum
            self._consecutive_allin_raise_sum += raise_amount
        elif not is_all_in and raise_amount > 0:
            # Non-all-in raise resets consecutive sum
            self._consecutive_allin_raise_sum = 0
    
    def _should_reopen_action(self, raise_increment: int, is_all_in: bool) -> bool:
        """
        Check if a raise should reopen action according to WSOP Rule 96.
        
        WSOP Rule 96: An all-in raise less than the previous raise shall not reopen
        the betting for players who have already acted, UNLESS two or more such 
        all-in raises total greater than or equal to the previous raise.
        
        Args:
            raise_increment: The amount this raise is increasing the bet by
            is_all_in: Whether this is an all-in
            
        Returns:
            True if action should be reopened
        """
        min_raise_increment = max(self.last_raise_amount, self.big_blind)
        
        # Full raise always reopens
        if raise_increment >= min_raise_increment:
            return True
        
        # If not all-in and not a full raise, it shouldn't be valid (handled elsewhere)
        if not is_all_in:
            return False
        
        # Short all-in: Check if consecutive all-in raises total >= min raise
        # WSOP Rule 96 exception
        if self._consecutive_allin_raise_sum >= min_raise_increment:
            return True
        
        return False
    
    def get_legal_actions(self, player: Optional[Player] = None) -> List[Dict[str, Any]]:
        """
        Get legal actions for the specified player (or current player).
        
        Returns:
            List of action dicts with type and constraints
        """
        if player is None:
            player = self.current_player
        
        if player is None or not player.is_active:
            return []
        
        actions = []
        chips_to_call = max(0, self.current_bet - player.current_bet)
        
        # Fold is always available
        actions.append({"type": ActionType.FOLD.value})
        
        # Check if no bet to call
        if chips_to_call == 0:
            actions.append({"type": ActionType.CHECK.value})
        else:
            # Call
            call_amount = min(chips_to_call, player.stack)
            actions.append({
                "type": ActionType.CALL.value,
                "amount": call_amount
            })
        
        # Bet/Raise if player has chips left after calling
        if player.stack > chips_to_call:
            if self.current_bet == 0:
                # Bet
                min_bet = self.big_blind
                max_bet = player.stack
                actions.append({
                    "type": ActionType.BET.value,
                    "min": min_bet,
                    "max": max_bet
                })
            else:
                # Raise
                min_raise_total = calculate_min_raise(
                    self.current_bet, self.last_raise_amount, self.big_blind
                )
                max_raise = player.stack + player.current_bet
                
                if max_raise >= min_raise_total:
                    actions.append({
                        "type": ActionType.RAISE.value,
                        "min": min(min_raise_total, max_raise),
                        "max": max_raise
                    })
        
        # All-in is always available if player has chips
        if player.stack > 0:
            actions.append({
                "type": ActionType.ALL_IN.value,
                "amount": player.stack + player.current_bet
            })
        
        return actions
    
    def get_state(self, for_player_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the current game state.
        
        Args:
            for_player_id: If specified, include private info for this player
            
        Returns:
            Game state dictionary
        """
        # Public information
        public_info = {
            "phase": self.phase.name,
            "hand_number": self.hand_number,
            "pot": self.pot_total,
            "current_bet": self.current_bet,
            "board": [c.to_dict() for c in self.community_cards],
            "dealer_position": self.dealer_position,
            "small_blind_position": self.small_blind_position,
            "big_blind_position": self.big_blind_position,
            "current_player": self.current_player.player_id if self.current_player else None,
            "players": [p.to_public_dict() for p in self.players],
            "last_raise": self.last_raise_amount,
        }
        
        # Private information (for specific player)
        private_info = {}
        if for_player_id:
            player = self._get_player_by_id(for_player_id)
            if player:
                private_info = {
                    "hand": [c.to_dict() for c in player.hole_cards],
                    "current_player": self.current_player_index if self.current_player else None,
                    "available_moves": [a["type"] for a in self.get_legal_actions(player)],
                    "chips_to_call": max(0, self.current_bet - player.current_bet),
                    "min_raise": calculate_min_raise(
                        self.current_bet, self.last_raise_amount, self.big_blind
                    ),
                    "current_bet": player.current_bet,
                    "raise_range": self._get_raise_range(player),
                    "pot_raise_values": self._calculate_pot_raise_values(player),
                }
        
        return {
            "public_info": public_info,
            "private_info": private_info
        }
    
    def _get_raise_range(self, player: Player) -> Dict[str, int]:
        """Get the valid raise range for a player."""
        min_raise_total = calculate_min_raise(
            self.current_bet, self.last_raise_amount, self.big_blind
        )
        max_raise = player.stack + player.current_bet
        
        return {
            "min": min(min_raise_total, max_raise),
            "max": max_raise
        }
    
    def _calculate_pot_raise_values(self, player: Player) -> Dict[str, Dict[str, Any]]:
        """Calculate standard pot-relative raise values."""
        chips_to_call = max(0, self.current_bet - player.current_bet)
        effective_pot = self.pot_total + chips_to_call
        
        min_raise_total = calculate_min_raise(
            self.current_bet, self.last_raise_amount, self.big_blind
        )
        max_raise = player.stack + player.current_bet
        
        def make_raise_value(multiplier: float, name: str) -> Dict[str, Any]:
            # Pot-sized raise = current_bet + (pot + current_bet) * multiplier
            amount = int(self.current_bet + effective_pot * multiplier)
            valid = min_raise_total <= amount <= max_raise
            return {
                "name": name,
                "total": min(max(amount, min_raise_total), max_raise) if valid else 0,
                "valid": valid
            }
        
        return {
            "pot_third": make_raise_value(1/3, "1/3 Pot"),
            "pot_half": make_raise_value(1/2, "1/2 Pot"),
            "pot_full": make_raise_value(1.0, "1x Pot"),
            "pot_2x": make_raise_value(2.0, "2x Pot"),
        }
    
    def _log_action(self, action: str, details: Dict[str, Any]) -> None:
        """Log an action to hand history."""
        self.hand_history.append({
            "action": action,
            "phase": self.phase.name,
            **details
        })
    
    def get_winners(self) -> List[Dict[str, Any]]:
        """Get winner information after hand is complete."""
        if self.phase != GamePhase.HAND_OVER:
            return []
        
        # Return from history
        for entry in reversed(self.hand_history):
            if entry["action"] in ("SHOWDOWN", "WIN_BY_FOLD"):
                if "winners" in entry:
                    return entry["winners"]
                if "winner" in entry:
                    return [{
                        "player_id": entry["winner"],
                        "amount": entry["amount"],
                        "hand_type": "WIN_BY_FOLD",
                        "description": "All other players folded"
                    }]
        return []
