from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    user_id: int
    username: Optional[str]
    portfolio: str
    team_id: Optional[int] = None


class Tag(BaseModel):
    user_id: int
    tag: str


class Team(BaseModel):
    id: Optional[int]
    name: str
