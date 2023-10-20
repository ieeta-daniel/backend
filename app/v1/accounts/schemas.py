import datetime
import uuid
from typing import Optional
from fastapi import UploadFile
from pydantic import BaseModel
from app.utils import as_form


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    grant_type: str = 'refresh_token'


class LogoutRequest(BaseModel):
    refresh_token: str


@as_form
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    name: str
    avatar: Optional[UploadFile] = None
    github_username: Optional[str] = None
    twitter_username: Optional[str] = None
    homepage_url: Optional[str] = None


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    name: str
    avatar: str
    github_username: Optional[str] = None
    twitter_username: Optional[str] = None
    homepage_url: Optional[str] = None
    created_at: datetime.datetime


class UserLogin(BaseModel):
    username: str
    password: str
    grant_type: str = 'password'
