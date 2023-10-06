from fastapi import HTTPException, status
from passlib.context import CryptContext
import secrets
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt
from pydantic import ValidationError

from app.config import settings
from app.v1.accounts.schemas import TokenPayload


class AuthenticationHandler:
    def __init__(self):
        self.password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_hashed_password(self, password: str) -> str:
        return self.password_context.hash(password)

    def verify_password(self, password: str, hashed_pass: str) -> bool:
        return self.password_context.verify(password, hashed_pass)

    @staticmethod
    def create_access_token(subject: Union[str, Any], expires_delta: int = None) -> str:
        if expires_delta is not None:
            expires_delta = datetime.utcnow() + timedelta(minutes=expires_delta)
        else:
            expires_delta = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

        to_encode = {"exp": expires_delta, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, settings.password_hash_algorithm)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(subject: Union[str, Any], expires_delta: int = None) -> str:
        if expires_delta is not None:
            expires_delta = datetime.utcnow() + timedelta(minutes=expires_delta)
        else:
            expires_delta = datetime.utcnow() + timedelta(minutes=settings.refresh_token_expire_minutes)

        to_encode = {"exp": expires_delta, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, settings.jwt_refresh_secret_key, settings.password_hash_algorithm)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> TokenPayload:
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.password_hash_algorithm]
            )
            token_data = TokenPayload(**payload)

            if datetime.fromtimestamp(token_data.exp) < datetime.now():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return token_data
        except(jwt.JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def generate_secret_key(mode='hex', n=32):
        if mode == 'hex':
            return secrets.token_hex(n)
        if mode == 'urlsafe':
            return secrets.token_urlsafe(n)
        if mode == 'ascii':
            return secrets.token_bytes(n).decode('ascii')
        if mode == 'base64':
            return secrets.token_bytes(n).decode('base64')
        if mode == 'base32':
            return secrets.token_bytes(n).decode('base32')
        if mode == 'base16':
            return secrets.token_bytes(n).decode('base16')
        raise ValueError('mode must be one of hex, urlsafe, ascii, base64, base32, base16')