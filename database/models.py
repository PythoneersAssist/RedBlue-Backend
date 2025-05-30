"""
Table models for the database
"""

from uuid import uuid4

from sqlalchemy import Column, Integer, String, UUID, BOOLEAN
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """This just needs to be here."""

class Match(Base):
    """
    Model for Match class, used to simulate a game.
    """
    __tablename__ = "match"
    uuid = Column(UUID(as_uuid=True), primary_key=True, nullable=False, unique=True)
    id = Column(Integer, primary_key=True, nullable=False, unique=True, index=True)
    player1 = Column(String)
    player2 = Column(String, nullable=True)
    player1_score = Column(Integer, nullable=False, default=0)
    player2_score = Column(Integer, nullable=False, default=0)
    player1_choice_history = Column(String, nullable=True, default="-1")
    player2_choice_history = Column(String, nullable=True, default="-1")
    round = Column(Integer, nullable=False, default=1)
    game_state = Column(String, nullable=False, default="created")

class Match_Handler(Base):
    """
    Model for Match class, used to handle game options, settings, etc.
    """
    __tablename__ = "match_handler"
    uuid = Column(UUID(as_uuid=True), primary_key=True, nullable=False, unique=True)
    player1_has_finished_round = Column(BOOLEAN, nullable=False, default=False)
    player2_has_finished_round = Column(BOOLEAN, nullable=False, default=False)
    ready_for_next_round = Column(BOOLEAN, nullable=False, default=False)
    p1_chat_accept = Column(BOOLEAN, default=None)
    p2_chat_accept = Column(BOOLEAN, default=None)
    chat_ready = Column(BOOLEAN, nullable=False, default=False)
    chat_finished = Column(BOOLEAN, nullable=False, default=False)
    is_p1_online = Column(BOOLEAN, nullable=False, default=False)
    is_p2_online = Column(BOOLEAN, nullable=False, default=False)