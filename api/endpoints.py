from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from utils import generator
from api.models import CreateGameModel, DeleteGameModel
from api.manager import ConnectionManager
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Match
import asyncio

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
async def join_game(websocket: WebSocket, game_code: str, playerName: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for a game session identified by game_code.
    Clients can send JSON messages to pick a number or send a chat message.
    """
    match = db.query(Match).filter(Match.id == game_code).first()
    p1_cleared = False
    p2_cleared = False
    if not match:
        print("[INFO] Game not found.")
        await websocket.close(code=1003)
        return

    if not match.player1 == playerName and match.player2:
        print("[INFO] Game is full.")
        await websocket.close(code=1003)
        return

    await manager.connect(game_code, playerName)
    await websocket.accept()
    print(f"[INFO] Player {playerName} connected to game {game_code}.")

    if not match.player1 == playerName:
        match.player2 = playerName

    db.commit()

    try:
        await websocket.send_json({"message": "Joined game successfully."})
        rounds = 10
        scores = {match.player1: 0, match.player2: 0}

        if not await manager.is_room_full(game_code):
            await websocket.send_json({"message": "Waiting for the other player to join..."})
            while not await manager.is_room_full(game_code):
                await asyncio.sleep(1)

        for round_number in range(1, rounds + 1):
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
                db.commit()
            
            while not match.ready_for_next_round:
                await websocket.send_json({"message": "Waiting for both players to finish the round."})
                db.refresh(match)
                await asyncio.sleep(1)
            
            match.player1_has_finished_round = False
            match.player2_has_finished_round = False
            db.commit()
            await manager.clear_choices(game_code)
            calculate_score = generator.calculate_score(match.player1_choice_history[-1], match.player2_choice_history[-1])
            match.player1_score += calculate_score[0]
            match.player2_score += calculate_score[1]

            await websocket.send_json({
                "round": round_number,
                "scores": [match.player1_score, match.player2_score],
                "choices": [match.player1_choice_history[-1], match.player2_choice_history[-1]],
            })

        match.player1_score = scores[match.player1]
        match.player2_score = scores[match.player2]
        db.commit()

        await websocket.send_json({"message": "Game over!", "final_scores": scores})
    except WebSocketDisconnect:
        manager.disconnect(game_code,websocket)
        await websocket.close(code=1003)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        manager.disconnect(game_code,websocket)
        await websocket.close(code=1003)