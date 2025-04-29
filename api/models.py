"""
Models for game endpoints.
"""
from pydantic import BaseModel

class GetGameModel(BaseModel):
    """Model for GetGame endpoint"""
    uuid: str
