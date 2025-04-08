from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from utils import generator
from api.models import CreateGameModel, DeleteGameModel
from api.manager import ConnectionManager
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Match

router = APIRouter(prefix="/game", tags=["game"])
manager = ConnectionManager()

@router.post("/")
def create_game( model: CreateGameModel, db: Session = Depends(get_db),) -> dict:
    """
    Create a new game.
    """
    code = generator.generate_random_code(7)

    while db.query(Match).filter(Match.id == code).first() is not None:
        print("[INFO] Code already exists, generating a new one...")
        code = generator.generate_random_code(7)

    match_model = Match(
        id=code,
        player1=model.ownerName,
    )
    db.add(match_model)
    db.commit()
    
    return {
        "code": code,
    }

def delete_game(model: DeleteGameModel) -> dict:
    """
    Delete a game.
    """
    return {
        "type": "game:delete",
        "status": "OK",
    }

@router.websocket("/ws/{game_code}")
async def join_game(websocket: WebSocket, game_code: str, playerName: str):
    """
    WebSocket endpoint for a game session identified by game_code.
    Clients can send JSON messages to pick a number or send a chat message.
    """