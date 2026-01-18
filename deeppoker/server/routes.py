"""
HTTP API Routes for DeepPoker.

These routes handle game initialization and state queries.
Real-time game actions are handled via WebSocket.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from deeppoker.core.game import TexasHoldemGame, ActionType
from deeppoker.server.schemas import (
    InitGameRequest, ActionRequest, ActionResultSchema,
    ErrorSchema, CardSchema
)

router = APIRouter()

# Global game instance for single-room mode
# In production, use GameManager for multiple rooms
_game: Optional[TexasHoldemGame] = None

# Templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "client", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def get_game() -> TexasHoldemGame:
    """Get the current game instance."""
    global _game
    if _game is None:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return _game


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main game page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/init_game")
async def init_game(req: InitGameRequest) -> Dict[str, Any]:
    """
    Initialize a new game with the specified number of players.
    
    This creates a new game instance and prepares it for play.
    """
    global _game
    
    try:
        _game = TexasHoldemGame(
            num_players=req.player_count,
            big_blind=20,
            small_blind=10,
            buy_in=1000,
        )
        
        return {
            "success": True,
            "message": f"Game initialized with {req.player_count} players",
            "player_count": req.player_count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start_hand")
async def start_hand() -> Dict[str, Any]:
    """
    Start a new hand.
    
    Deals cards and posts blinds.
    """
    game = get_game()
    
    if not game.start_hand():
        raise HTTPException(status_code=400, detail="Cannot start hand")
    
    return {
        "success": True,
        "message": f"Hand #{game.hand_number} started",
        "hand_number": game.hand_number,
    }


@router.get("/get_game_state")
async def get_game_state() -> Dict[str, Any]:
    """
    Get the current game state.
    
    Returns public information and private information for the current player.
    """
    game = get_game()
    
    # Get state for current player
    current_player_id = game.current_player.player_id if game.current_player else None
    state = game.get_state(for_player_id=current_player_id)
    
    return state


@router.post("/take_action")
async def take_action(req: ActionRequest) -> Dict[str, Any]:
    """
    Take a game action.
    
    Processes the action and returns the result.
    If the hand ends, includes winner information.
    """
    game = get_game()
    
    # Parse action type
    try:
        action_type = ActionType(req.action_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action type: {req.action_type}")
    
    # Execute action
    result = game.take_action(action_type, req.amount or 0)
    
    if not result.success:
        return {"error": result.message}
    
    # Build response
    response: Dict[str, Any] = {
        "success": True,
        "message": result.message,
        "action_type": result.action_type.value if result.action_type else None,
        "amount": result.amount,
    }
    
    # Check if hand is over
    if not game.is_hand_running():
        winners = game.get_winners()
        
        # Format winners with current stack info
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
        
        response["winners"] = formatted_winners
        response["pot"] = game.pot_total
        
        # Include all players' cards for showdown
        players_cards = []
        for player in game.players:
            if player.hole_cards:
                players_cards.append({
                    "id": player.player_id,
                    "cards": [card.to_dict() for card in player.hole_cards],
                })
        response["players_cards"] = players_cards
        
        # Include board cards
        response["board"] = [card.to_dict() for card in game.community_cards]
    
    return response


@router.get("/legal_actions")
async def get_legal_actions() -> Dict[str, Any]:
    """
    Get legal actions for the current player.
    """
    game = get_game()
    
    if not game.is_hand_running():
        return {"actions": [], "message": "No hand in progress"}
    
    actions = game.get_legal_actions()
    return {"actions": actions}


@router.post("/reset_game")
async def reset_game() -> Dict[str, Any]:
    """
    Reset the game (for development/testing).
    """
    global _game
    _game = None
    return {"success": True, "message": "Game reset"}


# ============= Room Management Routes (for future multi-room support) =============

@router.post("/rooms")
async def create_room() -> Dict[str, Any]:
    """Create a new game room."""
    # TODO: Implement room management with GameManager
    room_id = "room-1"  # Placeholder
    return {
        "room_id": room_id,
        "message": "Room created (single-room mode)"
    }


@router.get("/rooms/{room_id}")
async def get_room(room_id: str) -> Dict[str, Any]:
    """Get room information."""
    game = get_game()
    return {
        "room_id": room_id,
        "phase": game.phase.name,
        "hand_number": game.hand_number,
        "player_count": game.num_players,
    }
