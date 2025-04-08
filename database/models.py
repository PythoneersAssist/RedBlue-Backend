from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UUID
from sqlalchemy.orm import relationship, DeclarativeBase
from database.database import BASE

from uuid import uuid4

class Base(DeclarativeBase):
    pass

class Match(Base):
    __tablename__ = "match"
    id = Column(Integer, primary_key=True, nullable=False, unique=True, index=True)
    player1 = Column(String)
    player2 = Column(String, nullable=True)
    player1_score = Column(Integer, nullable=False, default=0)
    player2_score = Column(Integer, nullable=False, default=0)
    player1_choice_history = Column(String, nullable=True, default="-1")
    player2_choice_history = Column(String, nullable=True, default="-1")
    round = Column(Integer, nullable=False, default=1)

