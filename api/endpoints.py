from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from game.match import Match
from utils import generator
from models import CreateGameModel, DeleteGameModel
from manager import ConnectionManager

router = APIRouter(prefix="/game", tags=["game"])

active_games = [] # FAKE DB
manager = ConnectionManager()

@router.get("/")
def create_game(model: CreateGameModel) -> dict:
    """
    Create a new game.
    """
    code = generator.generate_code()

    while code in [game.code for game in active_games]:
        print("[INFO] Code already exists, generating a new one...")
        code = generator.generate_code()

    new_match = Match(generator.generate_code(), model.ownerName)
    active_games.append(new_match)

    return {
        "type": "game:create",
        "code": code,
    }

def delete_game(model: DeleteGameModel) -> dict:
    """
    Delete a game.
    """
    active_games = [game for game in active_games if game.code != model.code]
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
    await manager.connect(game_code, websocket)
    game = next((game for game in active_games if game.code == game_code), None)
    if game is None:
        await websocket.close(code=1000, reason="Game not found")
        return
    if not game.owner:
        game.add_player(playerName)
    elif not game.slave:
        game.add_player(playerName)
    else:
        await websocket.close(code=1000, reason="Game is full")
        return
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            if message_type == "pick":
                number = data.get("number")
                if number not in [1, 2]:
                    await websocket.send_json({"error": "Invalid number selection. Choose 1 or 2."})
                    continue
                # Broadcast the pick to all clients in the game session
                await manager.broadcast(game_code, {"type": "pick", "number": number})
            else:
                await websocket.send_json({"error": "Invalid message type. Use 'pick'."})
    except WebSocketDisconnect:
        manager.disconnect(game_code, websocket)