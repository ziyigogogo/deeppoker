"""
WebSocket handling for real-time game communication.

This module provides:
- GameManager: Manages multiple game rooms
- WebSocket endpoint: Handles real-time player connections and game actions
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import logging
import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from deeppoker.core.game import TexasHoldemGame, ActionType
from deeppoker.core.rules import GamePhase


logger = logging.getLogger(__name__)


@dataclass
class PlayerConnection:
    """Represents a connected player."""
    player_id: str
    websocket: WebSocket
    room_id: str


@dataclass
class GameRoom:
    """A game room with its game instance and connected players."""
    room_id: str
    game: TexasHoldemGame
    connections: Dict[str, WebSocket] = field(default_factory=dict)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[str] = None):
        """Broadcast a message to all connected players."""
        for player_id, ws in self.connections.items():
            if player_id != exclude:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to {player_id}: {e}")
    
    async def send_state_to_all(self):
        """Send personalized game state to each connected player."""
        for player_id, ws in self.connections.items():
            try:
                state = self.game.get_state(for_player_id=player_id)
                await ws.send_json({
                    "type": "state",
                    **state
                })
            except Exception as e:
                logger.error(f"Error sending state to {player_id}: {e}")
    
    async def send_result(self, winners: List[Dict], players_cards: List[Dict]):
        """Send hand result to all players."""
        message = {
            "type": "result",
            "winners": winners,
            "players_cards": players_cards,
            "pot": self.game.pot_total,
            "board": [c.to_dict() for c in self.game.community_cards]
        }
        await self.broadcast(message)


class GameManager:
    """
    Manages multiple game rooms and player connections.
    
    Usage:
        manager = GameManager()
        room_id = manager.create_room(player_count=6)
        await manager.connect(room_id, player_id, websocket)
        await manager.handle_message(room_id, player_id, message)
        await manager.disconnect(room_id, player_id)
    """
    
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self._room_counter = 0
    
    def create_room(
        self,
        player_count: int = 2,
        big_blind: int = 20,
        small_blind: int = 10,
        buy_in: int = 1000,
    ) -> str:
        """Create a new game room."""
        self._room_counter += 1
        room_id = f"room-{self._room_counter}"
        
        game = TexasHoldemGame(
            num_players=player_count,
            big_blind=big_blind,
            small_blind=small_blind,
            buy_in=buy_in,
        )
        
        self.rooms[room_id] = GameRoom(room_id=room_id, game=game)
        logger.info(f"Created room {room_id} with {player_count} players")
        
        return room_id
    
    def get_room(self, room_id: str) -> Optional[GameRoom]:
        """Get a game room by ID."""
        return self.rooms.get(room_id)
    
    def get_or_create_default_room(self, player_count: int = 2) -> str:
        """Get the default room or create one if it doesn't exist."""
        if not self.rooms:
            return self.create_room(player_count=player_count)
        return next(iter(self.rooms.keys()))
    
    async def connect(
        self,
        room_id: str,
        player_id: str,
        websocket: WebSocket
    ) -> bool:
        """
        Connect a player to a room.
        
        Returns:
            True if connected successfully
        """
        room = self.get_room(room_id)
        if room is None:
            logger.warning(f"Room {room_id} not found")
            return False
        
        await websocket.accept()
        room.connections[player_id] = websocket
        logger.info(f"Player {player_id} connected to {room_id}")
        
        # Send current state to the new player
        state = room.game.get_state(for_player_id=player_id)
        await websocket.send_json({
            "type": "state",
            **state
        })
        
        # Notify others
        await room.broadcast(
            {"type": "player_joined", "player_id": player_id},
            exclude=player_id
        )
        
        return True
    
    async def disconnect(self, room_id: str, player_id: str):
        """Disconnect a player from a room."""
        room = self.get_room(room_id)
        if room and player_id in room.connections:
            del room.connections[player_id]
            logger.info(f"Player {player_id} disconnected from {room_id}")
            
            await room.broadcast({
                "type": "player_left",
                "player_id": player_id
            })
    
    async def handle_message(
        self,
        room_id: str,
        player_id: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a message from a player.
        
        Args:
            room_id: The room ID
            player_id: The player ID
            message: The message dict with 'type' and optional data
            
        Returns:
            Response dict
        """
        room = self.get_room(room_id)
        if room is None:
            return {"type": "error", "message": "Room not found"}
        
        msg_type = message.get("type", "")
        
        if msg_type == "action":
            return await self._handle_action(room, player_id, message)
        elif msg_type == "start_hand":
            return await self._handle_start_hand(room)
        elif msg_type == "get_state":
            return await self._handle_get_state(room, player_id)
        else:
            return {"type": "error", "message": f"Unknown message type: {msg_type}"}
    
    async def _handle_action(
        self,
        room: GameRoom,
        player_id: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a game action from a player."""
        game = room.game
        
        # Verify it's this player's turn
        if game.current_player is None or game.current_player.player_id != player_id:
            return {"type": "error", "message": "Not your turn"}
        
        # Parse action
        action_str = message.get("action", "").upper()
        amount = message.get("amount", 0)
        
        try:
            action_type = ActionType(action_str)
        except ValueError:
            return {"type": "error", "message": f"Invalid action: {action_str}"}
        
        # Execute action
        result = game.take_action(action_type, amount)
        
        if not result.success:
            return {"type": "error", "message": result.message}
        
        # Broadcast updated state to all players
        await room.send_state_to_all()
        
        # Check if hand is over
        if not game.is_hand_running():
            winners = game.get_winners()
            
            # Format winners
            formatted_winners = []
            for winner in winners:
                player = game._get_player_by_id(winner["player_id"])
                formatted_winners.append({
                    "id": winner["player_id"],
                    "won": winner["amount"],
                    "stack": player.stack if player else 0,
                    "hand_type": winner.get("hand_type"),
                    "description": winner.get("description"),
                })
            
            # Get all players' cards
            players_cards = []
            for player in game.players:
                if player.hole_cards:
                    players_cards.append({
                        "id": player.player_id,
                        "cards": [card.to_dict() for card in player.hole_cards],
                    })
            
            await room.send_result(formatted_winners, players_cards)
        
        return {
            "type": "action_result",
            "success": True,
            "action": action_str,
            "amount": result.amount
        }
    
    async def _handle_start_hand(self, room: GameRoom) -> Dict[str, Any]:
        """Handle starting a new hand."""
        game = room.game
        
        if not game.start_hand():
            return {"type": "error", "message": "Cannot start hand"}
        
        # Send state to all players
        await room.send_state_to_all()
        
        return {
            "type": "hand_started",
            "hand_number": game.hand_number
        }
    
    async def _handle_get_state(
        self,
        room: GameRoom,
        player_id: str
    ) -> Dict[str, Any]:
        """Handle a state request."""
        state = room.game.get_state(for_player_id=player_id)
        return {
            "type": "state",
            **state
        }


# Global game manager instance
game_manager = GameManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for game communication.
    
    Protocol:
    1. Client connects and sends: {"type": "join", "room_id": "...", "player_id": "..."}
    2. Server sends game state
    3. Client sends actions: {"type": "action", "action": "CALL", "amount": 0}
    4. Server broadcasts state updates
    """
    room_id: Optional[str] = None
    player_id: Optional[str] = None
    
    try:
        # Wait for join message
        await websocket.accept()
        join_msg = await websocket.receive_json()
        
        if join_msg.get("type") != "join":
            await websocket.send_json({
                "type": "error",
                "message": "First message must be join"
            })
            await websocket.close()
            return
        
        room_id = join_msg.get("room_id")
        player_id = join_msg.get("player_id")
        
        if not room_id or not player_id:
            await websocket.send_json({
                "type": "error",
                "message": "room_id and player_id required"
            })
            await websocket.close()
            return
        
        # Get or create room
        room = game_manager.get_room(room_id)
        if room is None:
            # Auto-create room for convenience
            room_id = game_manager.create_room(player_count=2)
            room = game_manager.get_room(room_id)
        
        # Register connection
        room.connections[player_id] = websocket
        logger.info(f"Player {player_id} joined {room_id}")
        
        # Send initial state
        state = room.game.get_state(for_player_id=player_id)
        await websocket.send_json({
            "type": "state",
            **state
        })
        
        # Message loop
        while True:
            message = await websocket.receive_json()
            response = await game_manager.handle_message(room_id, player_id, message)
            await websocket.send_json(response)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {player_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if room_id and player_id:
            await game_manager.disconnect(room_id, player_id)
