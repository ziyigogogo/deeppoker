"""
Random Agent Implementation.

A simple agent that makes random legal moves.
Useful for testing and as a baseline for evaluation.
"""

import random
from typing import Dict, List, Any, Optional

from deeppoker.agents.base import BaseAgent


class RandomAgent(BaseAgent):
    """
    An agent that selects random legal actions.
    
    This agent is useful for:
    - Testing game logic
    - Providing opponents for training
    - Baseline comparison for other agents
    
    The agent has configurable tendencies:
    - fold_probability: How likely to fold when possible
    - raise_probability: How likely to raise vs call
    """
    
    def __init__(
        self,
        player_id: str,
        name: Optional[str] = None,
        fold_probability: float = 0.1,
        raise_probability: float = 0.3,
    ):
        """
        Initialize the random agent.
        
        Args:
            player_id: Unique identifier
            name: Optional name
            fold_probability: Probability of folding (0-1)
            raise_probability: Probability of raising vs calling (0-1)
        """
        super().__init__(player_id, name or f"Random-{player_id}")
        self.fold_probability = fold_probability
        self.raise_probability = raise_probability
    
    def observe(self, game_state: Dict[str, Any]) -> None:
        """Random agent doesn't need to observe state."""
        pass
    
    def act(
        self,
        game_state: Dict[str, Any],
        legal_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select a random legal action.
        
        Uses configured probabilities to bias towards certain actions.
        """
        if not legal_actions:
            return {"action": "FOLD", "amount": 0}
        
        # Convert to consistent format
        actions = []
        for action in legal_actions:
            if isinstance(action, str):
                actions.append({"type": action})
            else:
                actions.append(action)
        
        action_types = [a["type"] for a in actions]
        
        # Decide action based on probabilities
        roll = random.random()
        
        # Maybe fold
        if "FOLD" in action_types and roll < self.fold_probability:
            return {"action": "FOLD", "amount": 0}
        
        # Maybe raise/bet
        raise_actions = [a for a in actions if a["type"] in ("RAISE", "BET")]
        if raise_actions and roll < self.fold_probability + self.raise_probability:
            action = random.choice(raise_actions)
            
            # Pick a random amount in valid range
            min_amount = action.get("min", 0)
            max_amount = action.get("max", min_amount)
            
            if max_amount > min_amount:
                # Bias towards smaller raises
                amount = random.randint(min_amount, max_amount)
            else:
                amount = min_amount
            
            return {"action": action["type"], "amount": amount}
        
        # Check if possible
        if "CHECK" in action_types:
            return {"action": "CHECK", "amount": 0}
        
        # Call if possible
        call_action = next((a for a in actions if a["type"] == "CALL"), None)
        if call_action:
            return {"action": "CALL", "amount": call_action.get("amount", 0)}
        
        # Fall back to random action
        action = random.choice(actions)
        amount = action.get("amount", action.get("min", 0))
        return {"action": action["type"], "amount": amount}


class CallAgent(BaseAgent):
    """
    An agent that always calls (or checks).
    
    Useful for testing and as a simple baseline.
    """
    
    def __init__(self, player_id: str, name: Optional[str] = None):
        super().__init__(player_id, name or f"Caller-{player_id}")
    
    def observe(self, game_state: Dict[str, Any]) -> None:
        pass
    
    def act(
        self,
        game_state: Dict[str, Any],
        legal_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Always check or call."""
        action_types = []
        for action in legal_actions:
            if isinstance(action, str):
                action_types.append(action)
            else:
                action_types.append(action["type"])
        
        if "CHECK" in action_types:
            return {"action": "CHECK", "amount": 0}
        
        if "CALL" in action_types:
            call_action = next(
                (a for a in legal_actions 
                 if (isinstance(a, dict) and a.get("type") == "CALL") or a == "CALL"),
                None
            )
            amount = call_action.get("amount", 0) if isinstance(call_action, dict) else 0
            return {"action": "CALL", "amount": amount}
        
        # If can't check or call, fold
        return {"action": "FOLD", "amount": 0}


class AggressiveAgent(BaseAgent):
    """
    An agent that always raises when possible.
    
    Useful for testing raise logic and as a baseline.
    """
    
    def __init__(
        self,
        player_id: str,
        name: Optional[str] = None,
        raise_multiplier: float = 2.0
    ):
        """
        Initialize aggressive agent.
        
        Args:
            player_id: Unique identifier
            name: Optional name
            raise_multiplier: How much to raise relative to minimum
        """
        super().__init__(player_id, name or f"Aggro-{player_id}")
        self.raise_multiplier = raise_multiplier
    
    def observe(self, game_state: Dict[str, Any]) -> None:
        pass
    
    def act(
        self,
        game_state: Dict[str, Any],
        legal_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Always raise when possible, otherwise call."""
        actions = []
        for action in legal_actions:
            if isinstance(action, str):
                actions.append({"type": action})
            else:
                actions.append(action)
        
        # Look for raise/bet
        for action in actions:
            if action["type"] in ("RAISE", "BET"):
                min_amount = action.get("min", 0)
                max_amount = action.get("max", min_amount)
                
                # Raise by multiplier of minimum
                amount = int(min(min_amount * self.raise_multiplier, max_amount))
                return {"action": action["type"], "amount": amount}
        
        # Check if possible
        if any(a["type"] == "CHECK" for a in actions):
            return {"action": "CHECK", "amount": 0}
        
        # Call
        call_action = next((a for a in actions if a["type"] == "CALL"), None)
        if call_action:
            return {"action": "CALL", "amount": call_action.get("amount", 0)}
        
        return {"action": "FOLD", "amount": 0}


def random_agent(game) -> tuple:
    """
    Functional interface for random agent (compatible with texasholdem library).
    
    Args:
        game: TexasHoldemGame instance
        
    Returns:
        Tuple of (ActionType, amount)
    """
    from deeppoker.core.game import ActionType
    
    legal_actions = game.get_legal_actions()
    if not legal_actions:
        return ActionType.FOLD, 0
    
    action = random.choice(legal_actions)
    action_type = ActionType(action["type"])
    amount = action.get("amount", action.get("min", 0))
    
    return action_type, amount


def call_agent(game) -> tuple:
    """
    Functional interface for call agent (compatible with texasholdem library).
    
    Args:
        game: TexasHoldemGame instance
        
    Returns:
        Tuple of (ActionType, amount)
    """
    from deeppoker.core.game import ActionType
    
    legal_actions = game.get_legal_actions()
    action_types = [a["type"] for a in legal_actions]
    
    if "CHECK" in action_types:
        return ActionType.CHECK, 0
    
    if "CALL" in action_types:
        call_action = next(a for a in legal_actions if a["type"] == "CALL")
        return ActionType.CALL, call_action.get("amount", 0)
    
    return ActionType.FOLD, 0
