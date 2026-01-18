"""
Base Agent Interface for DeepPoker.

This module defines the abstract base class for all poker agents.
The interface is designed to be compatible with reinforcement learning
frameworks like VERL for LLM-based agents.

Usage:
    class MyAgent(BaseAgent):
        def observe(self, game_state):
            # Process game state
            pass
        
        def act(self, game_state, legal_actions):
            # Return action dict
            return {"action": "CALL", "amount": 0}
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BaseAgent(ABC):
    """
    Abstract base class for poker agents.
    
    This interface is designed to support:
    - Rule-based agents
    - Statistical/probabilistic agents
    - Neural network agents
    - LLM-based agents (with RL training)
    
    Attributes:
        player_id: Unique identifier for this agent
        name: Human-readable name
    """
    
    def __init__(self, player_id: str, name: Optional[str] = None):
        """
        Initialize the agent.
        
        Args:
            player_id: Unique identifier for this agent
            name: Optional human-readable name
        """
        self.player_id = player_id
        self.name = name or f"Agent-{player_id}"
    
    @abstractmethod
    def observe(self, game_state: Dict[str, Any]) -> None:
        """
        Observe the current game state.
        
        This method is called whenever the game state changes,
        allowing the agent to update its internal state or beliefs.
        
        For LLM agents, this could be used to build context or
        update a memory buffer.
        
        Args:
            game_state: Dictionary containing:
                - public_info: Public game information
                - private_info: Private information for this agent
                    - hand: Agent's hole cards
                    - available_moves: List of legal actions
                    - chips_to_call: Amount needed to call
                    - raise_range: Valid raise amounts
        """
        pass
    
    @abstractmethod
    def act(
        self,
        game_state: Dict[str, Any],
        legal_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Choose an action given the current game state.
        
        This is the main decision-making method that must return
        a valid action from the legal actions.
        
        For LLM agents, this could involve:
        - Formatting the state as a prompt
        - Calling the LLM for reasoning
        - Parsing the response into an action
        
        Args:
            game_state: Current game state dictionary
            legal_actions: List of legal action dicts, each containing:
                - type: Action type (FOLD, CHECK, CALL, BET, RAISE, ALL_IN)
                - amount: Required amount (for CALL)
                - min/max: Valid range (for BET/RAISE)
        
        Returns:
            Action dictionary with:
                - action: Action type string
                - amount: Amount for BET/RAISE (optional, default 0)
        
        Example:
            return {"action": "RAISE", "amount": 100}
        """
        pass
    
    def reset(self) -> None:
        """
        Reset the agent's internal state for a new game or hand.
        
        Override this method if your agent maintains state between hands.
        """
        pass
    
    def on_hand_start(self, hand_number: int) -> None:
        """
        Called when a new hand starts.
        
        Args:
            hand_number: The hand number
        """
        pass
    
    def on_hand_end(self, result: Dict[str, Any]) -> None:
        """
        Called when a hand ends.
        
        This can be used for learning or updating strategy.
        
        Args:
            result: Dictionary containing:
                - winners: List of winner info
                - pot: Total pot amount
                - showdown: Whether there was a showdown
        """
        pass
    
    def get_action_for_game(
        self,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convenience method that combines observe and act.
        
        Args:
            game_state: Current game state
            
        Returns:
            Action dictionary
        """
        self.observe(game_state)
        legal_actions = game_state.get("private_info", {}).get("available_moves", [])
        
        # Convert string actions to action dicts if needed
        if legal_actions and isinstance(legal_actions[0], str):
            legal_actions = [{"type": a} for a in legal_actions]
        
        return self.act(game_state, legal_actions)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.player_id}, {self.name})"


class HumanAgent(BaseAgent):
    """
    Placeholder agent for human players.
    
    This agent doesn't make decisions automatically - it's used
    to mark a seat as controlled by a human player.
    """
    
    def __init__(self, player_id: str, name: Optional[str] = None):
        super().__init__(player_id, name or f"Human-{player_id}")
    
    def observe(self, game_state: Dict[str, Any]) -> None:
        """Human observation is handled by the UI."""
        pass
    
    def act(
        self,
        game_state: Dict[str, Any],
        legal_actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Human action is provided externally.
        
        This method should not be called directly - human actions
        come through the API/WebSocket.
        """
        raise NotImplementedError("Human actions should come through the API")
