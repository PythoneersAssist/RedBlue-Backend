"""
Debug endpoints for development.
"""

from fastapi import APIRouter, Depends, HTTPException
from database.database import get_db
from database.models import Match, Match_Handler


router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/resetGameState/{game_code}")
async def reset_game_state(game_code: str, db=Depends(get_db)):
    """
    Reset the game state for a given game code.
    """
    match = db.query(Match).filter(Match.id == game_code).first()
    match_handler = db.query(Match_Handler).filter(Match_Handler.uuid == match.uuid).first()
    if not match:
        raise HTTPException(status_code=404, detail="Game not found")

    # Reset the game state
    match.game_state = "created"
    match.player1 = None
    match.player2 = None
    match.player1_choice_history = "-1"
    match.player2_choice_history = "-1"
    match.round = 1
    match.player1_score = 0
    match.player2_score = 0
    match_handler.player1_has_finished_round = False
    match_handler.player2_has_finished_round = False
    match_handler.ready_for_next_round = False
    match_handler.p1_chat_accept = None
    match_handler.p2_chat_accept = None
    match_handler.chat_ready = False
    match_handler.chat_finished = False
    db.commit()

    return {"message": "Game state reset successfully"}
