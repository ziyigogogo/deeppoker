"""
Pydantic schemas for API request/response validation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============= Request Schemas =============

class CreateRoomRequest(BaseModel):
    """Request to create a new game room."""
    player_count: int = Field(ge=2, le=10, default=2)
    big_blind: int = Field(gt=0, default=20)
    small_blind: int = Field(gt=0, default=10)
    buy_in: int = Field(gt=0, default=1000)


class JoinRoomRequest(BaseModel):
    """Request to join a game room."""
    player_id: str
    player_name: Optional[str] = None


class ActionRequest(BaseModel):
    """Request to take a game action."""
    action_type: str = Field(..., description="Action type: FOLD, CHECK, CALL, BET, RAISE, ALL_IN")
    amount: Optional[int] = Field(default=0, ge=0, description="Amount for BET/RAISE actions")


class InitGameRequest(BaseModel):
    """Request to initialize a game."""
    player_count: int = Field(ge=2, le=10, default=2)


# ============= Response Schemas =============

class CardSchema(BaseModel):
    """Card representation."""
    rank: str
    suit: str
    text: str
    color: str


class PlayerPublicSchema(BaseModel):
    """Public player information (visible to all)."""
    id: str
    seat: int
    stack: int
    bet: int
    total_bet: int
    state: str
    last_action: Optional[str] = None


class PlayerPrivateSchema(PlayerPublicSchema):
    """Private player information (visible only to the player)."""
    cards: Optional[List[CardSchema]] = None


class ActionSchema(BaseModel):
    """Available action."""
    type: str
    amount: Optional[int] = None
    min: Optional[int] = None
    max: Optional[int] = None


class RaiseRangeSchema(BaseModel):
    """Valid raise range."""
    min: int
    max: int


class PotRaiseValueSchema(BaseModel):
    """Pre-calculated pot raise value."""
    name: str
    total: int
    valid: bool


class PotRaiseValuesSchema(BaseModel):
    """All pot raise values."""
    pot_third: PotRaiseValueSchema
    pot_half: PotRaiseValueSchema
    pot_full: PotRaiseValueSchema
    pot_2x: PotRaiseValueSchema


class PublicInfoSchema(BaseModel):
    """Public game state information."""
    phase: str
    hand_number: int
    pot: int
    current_bet: int
    board: List[CardSchema]
    dealer_position: int
    small_blind_position: int
    big_blind_position: int
    current_player: Optional[str] = None
    players: List[PlayerPublicSchema]
    last_raise: int


class PrivateInfoSchema(BaseModel):
    """Private game state information for a specific player."""
    hand: List[CardSchema] = []
    current_player: Optional[int] = None
    available_moves: List[str] = []
    chips_to_call: int = 0
    min_raise: int = 0
    current_bet: int = 0
    raise_range: Optional[RaiseRangeSchema] = None
    pot_raise_values: Optional[PotRaiseValuesSchema] = None


class GameStateSchema(BaseModel):
    """Complete game state."""
    public_info: PublicInfoSchema
    private_info: PrivateInfoSchema


class WinnerSchema(BaseModel):
    """Winner information."""
    player_id: str = Field(..., alias="id")
    amount: int = Field(..., alias="won")
    hand_type: Optional[str] = None
    description: Optional[str] = None
    cards: Optional[List[str]] = None
    stack: Optional[int] = None
    
    class Config:
        populate_by_name = True


class ActionResultSchema(BaseModel):
    """Result of an action."""
    success: bool
    message: str
    action_type: Optional[str] = None
    amount: int = 0
    # Include winner info if hand is over
    winners: Optional[List[WinnerSchema]] = None
    players_cards: Optional[List[Dict[str, Any]]] = None
    pot: Optional[int] = None
    board: Optional[List[CardSchema]] = None


class RoomInfoSchema(BaseModel):
    """Room information."""
    room_id: str
    player_count: int
    big_blind: int
    small_blind: int
    buy_in: int
    phase: str


class ErrorSchema(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


# ============= WebSocket Message Schemas =============

class WSMessage(BaseModel):
    """Base WebSocket message."""
    type: str
    data: Optional[Dict[str, Any]] = None


class WSJoinMessage(BaseModel):
    """WebSocket join room message."""
    type: str = "join"
    room_id: str
    player_id: str


class WSActionMessage(BaseModel):
    """WebSocket action message."""
    type: str = "action"
    action: str  # FOLD, CHECK, CALL, BET, RAISE, ALL_IN
    amount: Optional[int] = 0


class WSStateMessage(BaseModel):
    """WebSocket state update message."""
    type: str = "state"
    public_info: Dict[str, Any]
    private_info: Dict[str, Any]


class WSResultMessage(BaseModel):
    """WebSocket hand result message."""
    type: str = "result"
    winners: List[Dict[str, Any]]
    players_cards: List[Dict[str, Any]]
    pot: int
    board: List[Dict[str, Any]]


class WSErrorMessage(BaseModel):
    """WebSocket error message."""
    type: str = "error"
    message: str
