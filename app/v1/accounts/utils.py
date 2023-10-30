import json
import os
import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import Union, Any, List
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from PIL import Image
from app.config import settings
from app.v1.accounts.exceptions import InvalidCredentialsException
from app.v1.accounts.schemas import TokenPayload

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)


def create_token(secret_key: str, algorithm: str, subject: Union[str, Any], identifier: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + timedelta(minutes=expires_delta)
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"exp": expires_delta, "sub": str(subject), "id": str(identifier)}

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm)

    return encoded_jwt


def create_access_token(subject: Union[str, Any], identifier: Union[str, Any], expires_delta: int = None) -> str:
    return create_token(settings.jwt_secret_key, settings.password_hash_algorithm, subject, identifier, expires_delta)


def create_refresh_token(subject: Union[str, Any], identifier: Union[str, Any], expires_delta: int = None) -> str:
    return create_token(settings.jwt_refresh_secret_key, settings.password_hash_algorithm, subject, identifier, expires_delta)


def encrypt_refresh_token(refresh_token):
    cipher_suite = Fernet(settings.jwt_refresh_encryption_secret_key)
    encrypted_refresh_token = cipher_suite.encrypt(refresh_token.encode('utf-8'))
    return encrypted_refresh_token


def decrypt_refresh_token(encrypted_refresh_token):
    cipher_suite = Fernet(settings.jwt_refresh_encryption_secret_key)
    decrypted_refresh_token = cipher_suite.decrypt(encrypted_refresh_token).decode('utf-8')
    return decrypted_refresh_token


def verify_refresh_token(given_refresh_token, encrypted_refresh_tokens):
    for encrypted_refresh_token in encrypted_refresh_tokens:
        decrypted_refresh_token = decrypt_refresh_token(encrypted_refresh_token)
        if given_refresh_token == decrypted_refresh_token:
            return encrypted_refresh_token
    return None


def verify_access_token(given_access_token, access_tokens):
    for access_token in access_tokens:
        if given_access_token == access_token.decode('utf-8'):
            return True
    return False


def decode_token(token: str, secret_key: str, algorithms: List[str]) -> TokenPayload:
    try:
        payload = jwt.decode(
            token, secret_key, algorithms=algorithms
        )
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise InvalidCredentialsException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data
    except(jwt.JWTError, ValidationError):
        raise InvalidCredentialsException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_access_token(token: str) -> TokenPayload:
    return decode_token(token, settings.jwt_secret_key, [settings.password_hash_algorithm])


def decode_refresh_token(token: str) -> TokenPayload:
    return decode_token(token, settings.jwt_refresh_secret_key, [settings.password_hash_algorithm])


def set_cookies(response, access_token, refresh_token):
    response.set_cookie('access_token', access_token, max_age=settings.access_token_expire_minutes * 60, path='/',
                        secure=True, httponly=True, samesite='Lax')
    response.set_cookie('refresh_token', refresh_token, max_age=settings.refresh_token_expire_minutes * 60, path='/',
                        secure=True, httponly=True, samesite='Lax')
    response.set_cookie('logged_in', 'true', max_age=settings.access_token_expire_minutes * 60, path='/', secure=True,
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
    if mode == 'aes':
        return Fernet.generate_key()
    raise ValueError('mode must be one of hex, urlsafe, ascii, base64, base32, base16')


def generate_image_resolutions(file_path: str, sizes=None) -> None:
    if sizes is None:
        return

    for size in sizes:
        if isinstance(size, tuple) and len(size) == 2:
            width, height = size
        elif isinstance(size, int):
            width = height = size
        else:
            continue

        image = Image.open(file_path, mode='r')
        image = image.resize((width, height), Image.LANCZOS)

        filename, ext = os.path.splitext(file_path)

        image.save(f'{filename}-{width}x{height}{ext}')


if __name__ == '__main__':
    print(generate_secret_key(mode='hex', n=32))
