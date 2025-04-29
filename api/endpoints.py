"""
Game endpoints for creating and managing game sessions.
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from api.models import GetGameModel
from api.manager import ConnectionManager
from asynchronous.game_state_manager import monitor_player_disconnect
from database.database import get_db
from database.models import Match
from utils import game_utils
import utils.constants as c

router = APIRouter(tags=["game"])
manager = ConnectionManager()


@router.post("/create")
def create_game(db: Session = Depends(get_db)) -> dict:
    """
    Create a new game.
    """
    code = game_utils.generate_random_code(7)

    while db.query(Match).filter(Match.id == code).first() is not None:
        print("[INFO] Code already exists, generating a new one...")
        code = game_utils.generate_random_code(7)

    match_model = Match(
        id=code
    )
    db.add(match_model)
    db.commit()

    return {
        "ok": True,
        "code": code,
    }

@router.websocket("/ws/{game_code}")
async def join_game(
    websocket: WebSocket,
    game_code: str,
    player_name: str,
    db: Session = Depends(get_db),
    token: str = None
    ):
    """
    WebSocket endpoint for a game session identified by game_code.
    Clients can send JSON messages to pick a number or send a chat message.
    """
    #TODO: Reconnection tokens stack up with every reconnection, this should be fixed.
    #TODO: Change the reconnection token to be jwt based, as jwt tokens expire after a certain time.
    #TODO: Name should not be deleted when user disconnects.

    ##################################
    # PLAYER CONNECTION VERIFICATION #
    ##################################

    match = db.query(Match).filter(Match.id == game_code, Match.game_state == "created").first()

    if token:
        match = db.query(Match).filter(Match.id == game_code, Match.game_state == "ongoing").first()

    await websocket.accept()

    if not match:
        await websocket.send_json({"error": c.NOT_FOUND_MESSAGE})
        await websocket.close(code = 1003, reason =c. NOT_FOUND_MESSAGE)
        return

    if match.player1 and match.player2:
        await websocket.send_json({"error": c.GAME_FULL_MESSAGE})
        await websocket.close(code = 1003, reason = c.GAME_FULL_MESSAGE)
        return

    await manager.connect(game_code, player_name, websocket)

    if match.game_state == "created":
        await websocket.send_json(
            {
                "event": "game_reconnection_token",
                "message" : c.RECONNECTION_TOKEN_MESSAGE,
                "reconnection_token": str(manager.reconenction_ids[game_code][player_name]),}
            )

    print(f"[INFO] Player {player_name} connected to game {game_code}.")

    match match.game_state:
        case "created":
            if not match.player1:
                match.player1 = player_name
            else:
                match.player2 = player_name

        case "ongoing":
            if not token:
                await websocket.send_json({"error": c.GAME_IN_PROGRESS_MESSAGE})
                await websocket.close(code=1003, reason= c.GAME_IN_PROGRESS_MESSAGE)
                return

            if str(manager.reconenction_ids[game_code][player_name]) != token:
                await websocket.send_json({"error": c.INVALID_TOKEN_MESSAGE})
                #print("[INFO] Tokens: ", manager.reconenction_ids[game_code])
                await websocket.close(code=1003, reason= c.INVALID_TOKEN_MESSAGE)
                return

            if (datetime.now() - manager.reconnection_timers[game_code][player_name]).seconds > 2:
                await websocket.send_json({"error": c.EXPIRED_TOKEN_MESSAGE})
                await websocket.close(code=1003, reason=c.EXPIRED_TOKEN_MESSAGE)
                return

            if not match.player1:
                match.player1 = player_name
            else:
                match.player2 = player_name

            await websocket.send_json(
                {
                    "event": "game_connected",
                    "message": c.RECONNECTED_MESSAGE
                }
                )

            await manager.broadcast(
                game_code,
                {
                    "event" : "game_player_reconnected",
                    "message" : c.PLAYER_RECONNECT_MESSAGE.format(player_name)
                }
            )

        case "finished":
            await websocket.send_json({"error": c.GF_MESSAGE})
            await websocket.close(code=1003, reason = c.GF_MESSAGE)
            return

        case "_":
            await websocket.send_json({"error": c.INVALID_GAME_STATE})
            raise HTTPException(status_code=400, detail=c.INVALID_GAME_STATE)

    db.commit()

    ##################
    # GAMEPLAY LOGIC #
    ##################

    try:
        rounds = 10

        await websocket.send_json({"event": "game_join","message": c.JOIN_MESSAGE})

        if not await manager.is_room_full(game_code):
            await websocket.send_json({"event": "game_join_wfp", "message": c.WFPJ_MESSAGE})
            while not await manager.is_room_full(game_code):
                await asyncio.sleep(1)

        match.game_state = "ongoing"
        db.commit()

        for round_number in range(match.round, rounds + 1):
            db.refresh(match)
            match.ready_for_next_round = False

            await websocket.send_json(
                {
                    "event": "game_round_start",
                    "round": round_number,
                    "message": c.ROUND_MESSAGE.format(round_number),
                }
            )

            player_choice = await websocket.receive_json()

            while player_choice not in [0, 1]:
                await websocket.send_json({"error": c.INVALID_CHOICE_MESSAGE})
                player_choice = await websocket.receive_json()
                continue


            if player_name == match.player1:
                await manager.store_choice(game_code, match.player1)
                match.player1_choice_history += str(player_choice)
                match.player1_has_finished_round = True
            else:
                await manager.store_choice(game_code, match.player2)
                match.player2_choice_history += str(player_choice)
                match.player2_has_finished_round = True

            db.commit()

            if match.player1_has_finished_round and match.player2_has_finished_round:
                match.ready_for_next_round = True
                match.round += 1
                calculate_score = game_utils.calculate_score(
                    int(match.player1_choice_history[-1]),
                    int(match.player2_choice_history[-1])
                    )
                match.player1_score += calculate_score[0]
                match.player2_score += calculate_score[1]
                db.commit()


            if not match.ready_for_next_round:
                if not match.player1 or not match.player2:
                    await websocket.send_json(
                        {
                            "event": "game_round_wfp_disconnect",
                            "message": c.CHOICE_DISCONNECTED_MESSAGE
                        }
                    )
                else:
                    await websocket.send_json({"event": "game_round_wfp", "message": c.WFP_MESSAGE})

                while not match.ready_for_next_round:
                    db.refresh(match)
                    await asyncio.sleep(1)

            match.player1_has_finished_round = False
            match.player2_has_finished_round = False
            db.commit()
            #await manager.clear_choices(game_code)
            if match.game_state == "finished":
                await websocket.send_json(
                    {
                        "event": "game_unexpected_finish",
                        "message": c.UNEXPECTED_FINISH_MESSAGE
                    }
                )
                break

            await websocket.send_json({
                "event": "game_round_over",
                "round": round_number,
                "scores": [match.player1_score, match.player2_score],
                "choices": [match.player1_choice_history[-1], match.player2_choice_history[-1]],
            })

        winner = match.player1 if match.player1_score > match.player2_score else match.player2

        if match.player1:
            await manager.broadcast(game_code,
                {
                    "event": "game_over",
                    "scores": {
                        match.player1: match.player1_score,
                        match.player2: match.player2_score,
                    },
                    "winner": winner,

                })


    ##############################
    # PLAYER DISCONNECT HANDLING #
    ##############################

    except WebSocketDisconnect:
        print("Disconnected because of WebsocketDisconnect.")
        if player_name == match.player1:
            match.player1 = None
        else:
            match.player2 = None
        db.commit()

        if not match.player1 and not match.player2:
            match.game_state = "finished"
            db.commit()
        manager.disconnect(game_code, websocket)
        await manager.broadcast(
            game_code,
            {
                "event": "game_player_left",
                "message": c.DISCONNECT_MESSAGE.format(player_name)
            }
        )

        asyncio.create_task(
            monitor_player_disconnect(game_code, db, manager, websocket)
        )

    #pylint: disable=broad-exception-caught
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        manager.disconnect(game_code, websocket)
        await manager.broadcast(
            game_code,
            {
                "event": "game_player_left",
                "message": c.DISCONNECT_MESSAGE.format(player_name)
            }
        )
        if player_name == match.player1:
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
