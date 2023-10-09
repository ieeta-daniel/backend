import datetime
import inspect
import uuid
from typing import Optional, Annotated
from fastapi import Form, UploadFile
from pydantic import BaseModel


def as_form(cls):
    new_params = [
        inspect.Parameter(
            field_name,
            inspect.Parameter.POSITIONAL_ONLY,
            default=model_field.default,
            annotation=Annotated[model_field.annotation, *model_field.metadata, Form()],
        )
        for field_name, model_field in cls.model_fields.items()
    ]

    cls.__signature__ = cls.__signature__.replace(parameters=new_params)

    return cls


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    grant_type: str = 'refresh_token'


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
