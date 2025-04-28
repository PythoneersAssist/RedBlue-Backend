from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from utils import generator
from sqlalchemy.orm import Session
import asyncio
from uuid import uuid4

from api.models import *
from api.manager import ConnectionManager
from database.database import get_db
from database.models import Match

router = APIRouter(tags=["game"])
manager = ConnectionManager()

@router.post("/create")
def create_game(db: Session = Depends(get_db)) -> dict:
    """
    Create a new game.
    """
    code = generator.generate_random_code(7)

    while db.query(Match).filter(Match.id == code).first() is not None:
        print("[INFO] Code already exists, generating a new one...")
        code = generator.generate_random_code(7)

    match_model = Match(
        id=code
    )
    db.add(match_model)
    db.commit()
    
    return {
        "ok": True,
        "code": code,
    }

@router.delete("/delete")
def delete_game(model: DeleteGameModel) -> dict:
    """
    Delete a game.
    """
    return {
        "type": "game:delete",
        "status": "OK",
    }

@router.websocket("/ws/{game_code}")
async def join_game(websocket: WebSocket, game_code: str, playerName: str, db: Session = Depends(get_db), token: str = None):
    """
    WebSocket endpoint for a game session identified by game_code.
    Clients can send JSON messages to pick a number or send a chat message.
    """
    #TODO: Reconnection tokens stack up with every reconnection, this should be fixed.
    match = db.query(Match).filter(Match.id == game_code).first()
    if token:
        match = db.query(Match).filter(Match.id == game_code, Match.game_state == "ongoing").first()
    await websocket.accept()
    if not match:
        await websocket.send_json({"error": "Game not found."})
        await websocket.close(code=1003, reason="Game not found.")
        return

    if match.player1 and match.player2:
        await websocket.send_json({"error": "Game is full."})
        await websocket.close(code=1003, reason="Game is full.")
        return

    await manager.connect(game_code, playerName, websocket)
    if match.game_state == "created":
        await websocket.send_json(
            {
                "event": "game_reconnection_token",
                "message" : "You have received a reconnection token. This should be used if the user disconnects.",
                "reconnection_token": str(manager.reconenction_ids[game_code][playerName]),}
            )

    print(f"[INFO] Player {playerName} connected to game {game_code}.")

    match match.game_state:
        case "created":
            if not match.player1:
                match.player1 = playerName
            else:
                match.player2 = playerName
        case "ongoing":
            if not token:
                await websocket.send_json({"error": "Game is already in progress. Please provide a reconnection token."})
                await websocket.close(code=1003, reason="Game is already in progress. Please provide a reconnection token.")
                return
            if str(manager.reconenction_ids[game_code][playerName]) != token:
                await websocket.send_json({"error": "Invalid reconnection token."})
                #print("[INFO] Tokens: ", manager.reconenction_ids[game_code])
                await websocket.close(code=1003, reason="Invalid reconnection token.")
                return
            if not match.player1:
                match.player1 = playerName
            else:
                match.player2 = playerName
            await websocket.send_json({"event": "game_connected", "message": "Reconnected to the game successfully."})
            await manager.broadcast(game_code, {"message": f"{playerName} has reconnected."})
        case "finished":
            await websocket.send_json({"error": "Game is already finished."})
            await websocket.close(code=1003, reason="Game is already finished.")
            return
        case "_":
            await websocket.send_json({"error": "Invalid game state."})
            raise HTTPException(status_code=400, detail="Invalid game state. If you see this I fucked up.")
    db.commit()

    try:
        await websocket.send_json({"event": "game_join","message": "Joined game successfully."})
        rounds = 10
        scores = {match.player1: 0, match.player2: 0}

        if not await manager.is_room_full(game_code):
            await websocket.send_json({"event": "game_join_wfp", "message": "Waiting for the other player to join..."})
            while not await manager.is_room_full(game_code):
                await asyncio.sleep(1)

        match.game_state = "ongoing"
        db.commit()
        for round_number in range(match.round, rounds + 1):
            db.refresh(match)
            match.ready_for_next_round = False

            await websocket.send_json({"message": f"Round {round_number}: Pick a color (0 for Red, 1 for Blue)"})

            if playerName == match.player1:
                player1_choice = await websocket.receive_json()

                if player1_choice not in [0, 1]:
                    await websocket.send_json({"error": "Invalid choice. Must be 0 or 1."})
                    continue

                await manager.store_choice(game_code, match.player1)
                match.player1_choice_history += str(player1_choice)
                match.player1_has_finished_round = True
                db.commit()

            elif playerName == match.player2:
                player2_choice = await websocket.receive_json()

                if player2_choice not in [0, 1]:
                    await websocket.send_json({"error": "Invalid choice. Must be 0 or 1."})
                    continue

                await manager.store_choice(game_code, match.player2)
                match.player2_choice_history += str(player2_choice)
                match.player2_has_finished_round = True
                db.commit()

            if match.player1_has_finished_round and match.player2_has_finished_round:
                match.ready_for_next_round = True
                match.round += 1
                calculate_score = generator.calculate_score(int(match.player1_choice_history[-1]), int(match.player2_choice_history[-1]))
                match.player1_score += calculate_score[0]
                match.player2_score += calculate_score[1]
                db.commit()
            
            while not match.ready_for_next_round:
                await websocket.send_json({"message": "Waiting for both players to finish the round."})
                db.refresh(match)
                await asyncio.sleep(1)

            match.player1_has_finished_round = False
            match.player2_has_finished_round = False
            db.commit()
            #await manager.clear_choices(game_code)
            

            await websocket.send_json({
                "event": "game_round_over",
                "round": round_number,
                "scores": [match.player1_score, match.player2_score],
                "choices": [match.player1_choice_history[-1], match.player2_choice_history[-1]],
            })

        await manager.broadcast(game_code,
            {
                "event": "game_over",
                "scores": {
                    match.player1: match.player1_score,
                    match.player2: match.player2_score,
                },
                "winner": match.player1 if match.player1_score > match.player2_score else match.player2,

            })

    except WebSocketDisconnect:
        print(f"Disconnected because of WebsocketDisconnect.")
        if playerName == match.player1:
            match.player1 = None
        else:
            match.player2 = None
        db.commit()

        if not match.player1 and not match.player2:
            match.game_state = "finished"
            db.commit()

        manager.disconnect(game_code, websocket)
        print(manager.sockets[game_code])
        await manager.broadcast(game_code, {"message": f"{playerName} has disconnected."})
    except Exception as e:
        print(f"Disconnected because of an error. Error: {e}")
        await websocket.send_json({"error": str(e)})
        manager.disconnect(game_code, websocket)
        await manager.broadcast(game_code, {"message": f"{playerName} has disconnected."})
        if playerName == match.player1:
            match.player1 = None
        else:
            match.player2 = None
        db.commit()
        await websocket.close(code=1003)


@router.get("/games")
async def get_games(
    page_size: int = Query(default=10, ge=1, le=100),
    page_number: int = Query(default=1, ge=1),
    game_state: str = None,
    game_code: int = None,
    db: Session = Depends(get_db)
    ):
    """
    Get a list of all active games.
    """
    games = db.query(Match).all()

    if game_state:
        games = [game for game in games if game.game_state == game_state]
    if game_code:
        games = [game for game in games if game.id == game_code]

    if not games:
        return {
            "ok": True,
            "games": [],
        }

    total_games = len(games)
    total_pages = (total_games + page_size - 1) // page_size

    if page_number > total_pages:
        raise HTTPException(status_code=404, detail="Page not found")

    start = (page_number - 1) * page_size
    end = start + page_size
    paginated_games = games[start:end]

    paginated_games = [
        {
            "player1": game.player1,
            "player1_score": game.player1_score,
            "player2": game.player2,
            "player2_score": game.player2_score,
            "game_state": game.game_state,
        }
        for game in paginated_games
    ]
    return {
        "ok": True,
        "games": paginated_games,
        "total_games": total_games,
        "total_pages": total_pages,
        "current_page": page_number,
    }

@router.post("/game")
async def fetch_game_details(
    model: GetGameModel,
    db: Session = Depends(get_db)
):
    """
    Fetch details of a specific game using its game code.
    """
    game = db.query(Match).filter(Match.uuid == model.uuid).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    game_details = {
        "game_code": game.id,
        "player1": game.player1,
        "player2": game.player2,
        "player1_score": game.player1_score,
        "player2_score": game.player2_score,
        "round": game.round,
        "game_state": game.game_state,
    }
    return {
        "ok": True,
        "game": game_details
    }