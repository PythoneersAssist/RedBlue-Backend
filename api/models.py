from pydantic import BaseModel
from uuid import uuid4

class CreateGameModel(BaseModel):
    ownerName: str

class DeleteGameModel(BaseModel):
    gameCode: str

class GetGameModel(BaseModel):
    uuid: str