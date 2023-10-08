import os
import secrets
from datetime import datetime, timedelta
from typing import Union, Any

from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from PIL import Image
from app.config import settings
from app.v1.accounts.schemas import TokenPayload

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)


def create_token(subject: Union[str, Any], expires_delta: int = None, secret_key: str = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + timedelta(minutes=expires_delta)
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, secret_key, settings.password_hash_algorithm)
    return encoded_jwt


def create_access_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    return create_token(subject, expires_delta, settings.jwt_secret_key)


def create_refresh_token(subject: Union[str, Any], expires_delta: int = None) -> str:
    return create_token(subject, expires_delta, settings.jwt_refresh_secret_key)


def decode_token(token: str, secret_key: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token, secret_key, algorithms=[settings.password_hash_algorithm]
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


def decode_access_token(token: str) -> TokenPayload:
    return decode_token(token, settings.jwt_secret_key)


def decode_refresh_token(token: str) -> TokenPayload:
    return decode_token(token, settings.jwt_refresh_secret_key)


def set_cookies(response, access_token, refresh_token):
    response.set_cookie('access_token', access_token, max_age=settings.access_token_expire_minutes * 60, path='/',
                        secure=True, httponly=True, samesite='Lax')
    response.set_cookie('refresh_token', refresh_token, max_age=settings.refresh_token_expire_minutes * 60, path='/',
                        secure=True, httponly=True, samesite='Lax')
    response.set_cookie('logged_in', 'True', max_age=settings.access_token_expire_minutes * 60, path='/', secure=True,
                        httponly=False, samesite='Lax')


def unset_cookies(response):
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    response.set_cookie('logged_in', '', -1)


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


def generate_image_resolutions(file_url: str, sizes=None) -> None:
    if sizes is None:
        return

    for size in sizes:
        if isinstance(size, tuple) and len(size) == 2:
            width, height = size
        elif isinstance(size, int):
            width = height = size
        else:
            continue

        image = Image.open(file_url, mode='r')
        image = image.resize((width, height), Image.LANCZOS)

        filename, ext = os.path.splitext(file_url)

        image.save(f'{filename}-{width}x{height}{ext}')


if __name__ == '__main__':
    print(generate_secret_key('hex', 32))
