import datetime
import uuid
from typing import Optional

from fastapi import UploadFile
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str

class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    name: str
    # avatar: Optional[UploadFile]
    github_username: Optional[str] = None
    twitter_username: Optional[str] = None
    homepage_url: Optional[str] = None

class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    name: str
    # avatar: str
    github_username: Optional[str] = None
    twitter_username: Optional[str] = None
    homepage_url: Optional[str] = None
    created_at: datetime.datetime
