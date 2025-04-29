"""
Debug endpoints for development.
"""

from fastapi import APIRouter, Depends, HTTPException
from database.database import get_db
from database.models import Match


router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/resetGameState/{game_code}")
async def reset_game_state(game_code: str, db=Depends(get_db)):
    """
    Reset the game state for a given game code.
    """
    match = db.query(Match).filter(Match.id == game_code).first()
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
    match.player1_has_finished_round = False
    match.player2_has_finished_round = False
    match.ready_for_next_round = False
    db.commit()

    return {"message": "Game state reset successfully"}
