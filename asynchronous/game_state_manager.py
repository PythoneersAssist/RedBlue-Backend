"""
This module handles player disconnection, and broadcasts messages to all players in a game session.
"""

import asyncio
from datetime import datetime

from database.models import Match, Match_Handler
from utils.constants import DISCONNECT_TIMEOUT, GAME_TIMEOUT_MESSAGE

async def monitor_player_disconnect(game_code, db, manager, websocket, player_name):
    """
    Monitor player disconnection and handle reconnection logic.
    If a player is disconnected for more than DISCONNECT_TIMEOUT seconds, remove them from the game.
    """
    while True:
        if (
        manager.reconnection_timers.get(game_code) and
        manager.reconnection_timers[game_code].get(player_name)
        ):
            timer = manager.reconnection_timers[game_code][player_name]
            if (datetime.now() - timer).seconds > DISCONNECT_TIMEOUT:

                match = db.query(Match).filter(
                    Match.id == game_code,
                    Match.game_state == "ongoing"
                ).first()

                if not match:
                    return

                match_handler = db.query(Match_Handler).filter(
                    Match_Handler.uuid == match.uuid
                ).first()
                
                if match_handler.is_p1_online and match_handler.is_p2_online:
                    return # Both players are online, no need to finish the game

                if not match_handler.is_p1_online and not match_handler.is_p2_online:
                    return

                match.game_state = "finished"
                db.commit()

                await manager.broadcast(
                    game_code,
                    {
                        "event": "game_timeout",
                        "message": GAME_TIMEOUT_MESSAGE
                    }
                )
                winner = (match.player1
                        if match.player1_score > match.player2_score
                        else match.player2
                        )

                await manager.broadcast(game_code,
                    {
                        "event": "game_over_disconnect_score",
                        "scores": {
                            match.player1: match.player1_score,
                            match.player2: match.player2_score,
                        },
                        "winner": winner,
                    }
                )
                await manager.disconnect_all(game_code)
                del manager.active_connections[game_code]
                del manager.reconnection_ids[game_code]
                del manager.reconnection_timers[game_code]
                return

        await asyncio.sleep(DISCONNECT_TIMEOUT / 10)
