from pydantic import BaseModel

class CreateGameModel(BaseModel):
    ownerName: str

class DeleteGameModel(BaseModel):
    gameCode: str