"""
Game endpoints for creating and managing game sessions.
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from uuid import uuid4

from api.models import GetGameModel
from api.manager import ConnectionManager
from asynchronous.game_state_manager import monitor_player_disconnect
from database.database import get_db
from database.models import Match, Match_Handler
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

    _uuid=uuid4()

    match_model = Match(
        id=code,
        uuid=_uuid
    )

    match_handler_model = Match_Handler(
        uuid=_uuid
    )
    db.add(match_model)
    db.add(match_handler_model)
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
        await websocket.close(code = 1003, reason =c.NOT_FOUND_MESSAGE)
        return

    match_handler = db.query(Match_Handler).filter(Match_Handler.uuid == match.uuid).first()

    if match_handler.is_p1_online and match_handler.is_p2_online:
        await websocket.send_json({"error": c.GAME_FULL_MESSAGE})
        await websocket.close(code = 1003, reason = c.GAME_FULL_MESSAGE)
        return

    await manager.connect(game_code, player_name, websocket)

    if match.game_state == "created":
        await websocket.send_json(
            {
                "event": "game_reconnection_token",
                "message" : c.RECONNECTION_TOKEN_MESSAGE,
                "reconnection_token": str(manager.reconnection_ids[game_code][player_name]),}
            )

    match match.game_state:
        case "created":
            if not match.player1:
                match.player1 = player_name
                match_handler.is_p1_online = True
            else:
                match.player2 = player_name
                match_handler.is_p2_online = True

        case "ongoing":
            if not token:
                await websocket.send_json({"error": c.GAME_IN_PROGRESS_MESSAGE})
                await websocket.close(code=1003, reason= c.GAME_IN_PROGRESS_MESSAGE)
                return

            if str(manager.reconnection_ids[game_code][player_name]) != token:
                await websocket.send_json({"error": c.INVALID_TOKEN_MESSAGE})
                #print("[INFO] Tokens: ", manager.reconenction_ids[game_code])
                await websocket.close(code=1003, reason= c.INVALID_TOKEN_MESSAGE)
                return

            if (datetime.now() - manager.reconnection_timers[game_code][player_name]).seconds > c.DISCONNECT_TIMEOUT:
                await websocket.send_json({"error": c.EXPIRED_TOKEN_MESSAGE})
                await websocket.close(code=1003, reason=c.EXPIRED_TOKEN_MESSAGE)
                return

            if not match.player1:
                match.player1 = player_name
                match_handler.is_p1_online = True
            else:
                match.player2 = player_name
                match_handler.is_p2_online = True

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

        await manager.broadcast(
        game_code,
        {
            "event" : "game_player_join",
            "player_name" : player_name,
        }
        )

        if not await manager.is_room_full(game_code):
            await websocket.send_json({"event": "game_join_wfp", "message": c.WFPJ_MESSAGE})
            while not await manager.is_room_full(game_code):
                await asyncio.sleep(1)

        match.game_state = "ongoing"
        db.commit()

        for round_number in range(match.round, rounds + 1):
            db.refresh(match)
            db.refresh(match_handler)
            match_handler.ready_for_next_round = False

            if round_number in c.CHAT_ROUND:
                await websocket.send_json(
                    {
                        "event" : "chat_possibilty",
                        "message" : "A chatbox can now be opened for players to communicate. Awaiting user confirmation."
                    }
                )
                while True:
                    player_choice = await websocket.receive_json()
                    match player_choice["event"]:
                        case "chat_accept":
                            if player_name == match.player1:
                                match_handler.p1_chat_accept = True
                            else:
                                match_handler.p2_chat_accept = True
                            db.commit()
                            await websocket.send_json(
                                {
                                    "event" : "chat_accepted",
                                    "message" : "Chat request accepted."                              
                                }
                            )
                            break

                        case "chat_decline":
                            if player_name == match.player1:
                                match_handler.p1_chat_accept = False
                            else:
                                match_handler.p2_chat_accept = False
                            await websocket.send_json(
                                {
                                    "event" : "chat_declined",
                                    "message" : "Chat request declined."                              
                                }
                            )
                            break
                        case _:
                            await websocket.send_json(
                                {
                                    "event" : "malformed_request",
                                    "error" : "Unknown event. Please try again."
                                }
                            )
                db.commit()
                db.refresh(match_handler)
                print(match_handler.p1_chat_accept, match_handler.p2_chat_accept)
                if match_handler.p1_chat_accept and match_handler.p2_chat_accept:
                    match_handler.chat_ready = True
                    await manager.broadcast(
                        game_code,
                        {
                            "event" : "chat_start",
                            "message" : "Chat accepted by both players, you can now discuss."
                        }
                    )

                if match_handler.p1_chat_accept is None or match_handler.p2_chat_accept is None:
                    await websocket.send_json(
                        {
                            "event" : "chat_wfp_choice",
                            "message" : "Waiting for all players to make a choice."
                        }
                    )
                    while match_handler.p1_chat_accept is None or match_handler.p2_chat_accept is None:
                        print(match_handler.p1_chat_accept, match_handler.p2_chat_accept)
                        
                        db.refresh(match_handler)
                        await asyncio.sleep(0.5)

                    if match_handler.p1_chat_accept is False or match_handler.p2_chat_accept is False:
                        match_handler.chat_ready = False
                        match_handler.chat_finished = False
                        match_handler.p1_chat_accept = None
                        match_handler.p2_chat_accept = None
                        db.commit()

                        
                if match_handler.p1_chat_accept and match_handler.p2_chat_accept:
                    await websocket.send_json(
                        {
                            "event" : "game_hold",
                            "message" : "The game is on hold while the chat session is open."
                        }
                    )
                    while not match_handler.chat_finished:
                        db.refresh(match_handler)
                        await asyncio.sleep(2)

            await websocket.send_json(
                {
                    "event": "game_round_start",
                    "round": round_number,
                    "message": c.ROUND_MESSAGE.format(round_number),
                }
            )
           
            while True:
                player_choice = await websocket.receive_json()

                if not player_choice.get("event"):
                    await websocket.send_json(
                        {
                            "event" : "incorrect_format",
                            "error" : "The format sent does not have an event field."
                        }
                    )
                    continue
                if not player_choice.get("content"):
                    await websocket.send_json(
                        {
                            "event" : "malformed_request",
                            "error" : "The received json does not contain any content." 
                        }
                    )
                    continue

                match player_choice["event"]:
                    case "game_choice":
                        try:
                            int(player_choice["content"])
                        except Exception:
                            await websocket.send_json(
                                {
                                    "event" : "malformed_request",
                                    "error" : f"Unexpected json content for game_choice, expected int = 0,1 - received {player_choice['event']}."
                                }
                            )

                            continue
                        if player_name == match.player1:
                            await manager.store_choice(game_code, match.player1)
                            match.player1_choice_history += str(player_choice["content"])
                            match_handler.player1_has_finished_round = True
                        else:
                            await manager.store_choice(game_code, match.player2)
                            match.player2_choice_history += str(player_choice["content"])
                            match_handler.player2_has_finished_round = True
                        break

                    case "game_forfeit": # We do not need any content for this event
                        if player_name == match.player1:
                            abandoned_player = match.player1_score
                            remaining_player = match.player2_score
                        else:
                            abandoned_player = match.player2_score
                            remaining_player = match.player1_score

                        scores = game_utils.calculate_forfeit_score(
                            abandoned_player,
                            remaining_player,
                            round_number
                        )

                        if player_name == match.player1:
                            match.player1_score = scores[0]
                            match.player2_score = scores[1]
                        else:
                            match.player1_score = scores[1]
                            match.player2_score = scores[0]

                        await manager.broadcast(
                            game_code,
                            {
                                "event" : "game_forfeit",
                                "player" : player_name,
                                "message" : f"Player {player_name} has surrendered."
                            }
                        )
                        match.game_state = "finished"
                        break
                    case "game_disconnect": # We do not need any content for this event
                        await manager.broadcast(
                            game_code,
                            {
                                "event": "game_player_left",
                                "message": c.DISCONNECT_MESSAGE.format(player_name)
                            }
                        )
                        if player_name == match.player1:
                            match_handler.is_p1_online = False
                        else:
                            match_handler.is_p2_online = False
                        await websocket.close()
                        break
                    
            db.commit()
            if not match.game_state == "finished":
                if match_handler.player1_has_finished_round and match_handler.player2_has_finished_round:
                    match_handler.ready_for_next_round = True
                    match.round += 1
                    bonusRound = False if not round_number in [9,10] else True 
                    calculate_score = game_utils.calculate_score(
                        int(match.player1_choice_history[-1]),
                        int(match.player2_choice_history[-1]),
                        bonusRound
                        )
                    match.player1_score += calculate_score[0]
                    match.player2_score += calculate_score[1]
                    db.commit()


                if not match_handler.ready_for_next_round:
                    await websocket.send_json({"event": "game_round_wfp", "message": c.WFP_MESSAGE})

                    while not match_handler.ready_for_next_round:
                        db.refresh(match_handler)
                        await asyncio.sleep(0.1)

            match_handler.player1_has_finished_round = False
            match_handler.player2_has_finished_round = False
            db.commit()
            #await manager.clear_choices(game_code)
            if match.game_state == "finished":
                break
            
            index = 0 if player_name == match.player1 else 1
            await websocket.send_json({
                "event": "game_round_over",
                "round": round_number,
                "score" : [match.player1_score, match.player2_score],
                "choice" : [match.player1_choice_history[-1], match.player2_choice_history[-1]],
                "index" : index
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
        
        await manager.disconnect_all(game_code)
        await manager.delete_room(game_code)
    ##############################
    # PLAYER DISCONNECT HANDLING #
    ##############################

    except WebSocketDisconnect:
        print("Disconnected because of WebsocketDisconnect.")
        if manager.reconnection_timers.get(game_code) is None: # this only happens if the async task finished 
            return                                             # which then triggers an async task for each player
                                                               # we don't need that
        manager.reconnection_timers[game_code][player_name] = datetime.now()

        if player_name == match.player1:
            match_handler.is_p1_online = False
        else:
            match_handler.is_p2_online = False
        db.commit()

        if not match_handler.is_p1_online and not match_handler.is_p2_online:
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
            monitor_player_disconnect(game_code, db, manager, websocket, player_name)
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
            match_handler.is_p1_online = False
        else:
            match_handler.is_p2_online = False
        db.commit()
        await websocket.close(code=1003)

@router.websocket("/chat/{game_code}")
async def game_chat(
    websocket: WebSocket,
    game_code: int,
    player_name: str,
    db: Session = Depends(get_db)
    ):
    match = db.query(Match).filter(Match.id == game_code, Match.game_state == "ongoing").first()
    await websocket.accept()
    
    if not match:
        await websocket.send_json(
            {
                "error" : "Game not found."
            }
        )
        await websocket.close(code=1003)
        return
    match_handler = db.query(Match_Handler).filter(Match_Handler.uuid == match.uuid).first()

    if not player_name in [match.player1, match.player2]:
        await websocket.send_json(
            {
                "error" : "You are not allowed to join this chat session."
            }
        )
        await websocket.close(code=1003)
        return

    if match_handler.p1_chat_accept is False or match_handler.p2_chat_accept is False:
        await websocket.send_json(
            {
                "error": "Chat session is not open since both players didn't accept the request."
            }
        )
        await websocket.close(code=1003)
        return

    if match_handler.chat_finished:
        await websocket.send_json(
            {
                "error": "Chat session has already been closed."
            }
        )
        await websocket.close(code=1003)
        return
    if len(manager.chat_sockets) == 2:
        await websocket.send_json(
            {
                "error": "Chat session is full."
            }
        )
        await websocket.close()
        return

    await manager.chat_connect(game_code, websocket)
    await manager.chat_broadcast(
        game_code,
        {
            "event" : "chat_player_connected",
            "message" : f"{player_name} has connected."
        }
    )

    if len(manager.chat_sockets) < 2:
        await websocket.send_json(
            {
                "event": "chat_wfp_join",
                "message": "Waiting for all players to join"
            }
        )
        while len(manager.chat_sockets[game_code]) < 2:
            await websocket.send_json({str(len(manager.chat_sockets)) : 0})
            await asyncio.sleep(1)

    await websocket.send_json(
        {
            "event" : "chat_open",
            "message" : "All players have connected. Chat is now available."
        }
    )
    try:
        while True:
            p_message = await websocket.receive_json()

            if not p_message.get("event"):
                await websocket.send_json(
                    {
                        "event" : "incorrect_format",
                        "error" : "The format sent does not have an event field."
                    }
                )
                continue
            if not p_message.get("content"):
                await websocket.send_json(
                    {
                        "event" : "malformed_request",
                        "error" : "The received json does not contain any content." 
                    }
                )
                continue

            match p_message["event"]:
                case "chat_message":
                    if p_message["content"] == "":
                        print("Skipped")
                        continue
                    if len(p_message["content"]) > 255:
                        print("Skipped")
                        continue
                    await manager.chat_broadcast(
                        game_code,
                        {
                            "event" : "chat_message",
                            "player" : player_name,
                            "content" : p_message["content"]
                        }
                    )
                case "chat_stop":
                    break
        
        await manager.chat_broadcast(
            game_code,
            {
                "event" : "chat_ended",
                "message" : "The chat session has finished."
            }
        )
        match_handler.chat_finished = True
        db.commit()
        await manager.chat_disconnect_all(game_code)
    except WebSocketDisconnect:
        manager.chat_disconnect(game_code, websocket)
        await manager.chat_broadcast(
            game_code,
            {
                "event" : "chat_disconnect",
                "player" : player_name,
                "message" : "User has disconnected. The chat session will end."
            }
        )
        match_handler.chat_finished = True
        db.commit()
        await manager.chat_disconnect_all(game_code)
    except Exception as e:
        await manager.chat_disconnect(game_code, websocket)
        await manager.chat_broadcast(
            game_code,
            {
                "event" : "chat_disconnect",
                "player" : player_name,
                "message" : e
            }
        )
        match_handler.chat_finished = True
        db.commit()
        await manager.chat_disconnect_all(game_code)


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
