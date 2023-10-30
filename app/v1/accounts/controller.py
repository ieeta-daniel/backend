import os
import time
import uuid
from typing import List

import aiofiles as aiofiles
from fastapi import APIRouter, Depends, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.dependencies import get_accounts_service, cache
from app.v1.accounts.schedulers import scheduler
from app.v1.accounts.schemas import UserRead, UserCreate, Token, RefreshTokenRequest, LogoutRequest
from app.v1.accounts.service import AccountsService
from app.v1.accounts.utils import set_cookies, create_access_token, create_refresh_token, \
    unset_cookies, generate_image_resolutions, encrypt_refresh_token, verify_refresh_token, verify_access_token
from app.v1.accounts.exceptions import InvalidRefreshTokenException, InvalidGrantTypeException, \
    MissingUserFieldsException, IncorrectFieldsException, UserAlreadyExistsException, InvalidFileTypeException, \
    InvalidFileSizeException, InvalidCredentialsException, UserNotFoundException

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/accounts/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/accounts/login", auto_error=False)

scheduler.start()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(response: Response, background_tasks: BackgroundTasks, user: UserCreate = Depends(),
                   redis_client: cache = Depends(cache),
                   accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    existing_user = await accounts_service.get_user_by_username(user.username)

    if existing_user:
        raise UserAlreadyExistsException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    existing_email = await accounts_service.get_user_by_email(user.email)

    if existing_email:
        raise UserAlreadyExistsException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    file = user.avatar
    media_img_url = ''

    if file and file.size > 0:
        if file.content_type not in ['image/jpeg', 'image/png', 'image/gif']:
            raise InvalidFileTypeException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                           detail="Only .jpeg, .png, or .gif  files allowed")

        if file.size > settings.max_avatar_size:
            raise InvalidFileSizeException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                           detail=f"File size should not exceed {settings.max_avatar_size} bytes")

        _, ext = os.path.splitext(file.filename)

        media_img_dir = os.path.join(settings.media_dir, 'accounts/avatars')
        static_img_dir = os.path.join(settings.static_dir, media_img_dir)

        os.makedirs(static_img_dir, exist_ok=True)

        file_name = f'{uuid.uuid4().hex}-avatar{ext}'

        static_img_file = os.path.join(static_img_dir, file_name)
        media_img_url = os.path.join(media_img_dir, file_name)

        async with aiofiles.open(static_img_file, mode='wb') as buffer:
            while content := await file.read(4096):
                await buffer.write(content)

        background_tasks.add_task(generate_image_resolutions, file_path=static_img_file, sizes=settings.avatar_sizes)

    user = await accounts_service.create_user(user, media_img_url)

    token_id = uuid.uuid4().hex

    access_token = create_access_token(user.id, identifier=token_id)
    access_token_expire_timestamp = int(time.time()) + (settings.access_token_expire_minutes * 60)
    access_token_redis_key = f"access_tokens:{user.id}"
    redis_client.zadd(access_token_redis_key, {access_token: access_token_expire_timestamp})

    refresh_token = create_refresh_token(user.id, identifier=token_id)
    encrypted_refresh_token = encrypt_refresh_token(refresh_token)
    refresh_token_expire_timestamp = int(time.time()) + (settings.refresh_token_expire_minutes * 60)
    refresh_token_redis_key = f"refresh_tokens:{user.id}"
    redis_client.zadd(refresh_token_redis_key, {encrypted_refresh_token: refresh_token_expire_timestamp})

    set_cookies(response, access_token, refresh_token)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(response: Response, redis_client: cache = Depends(cache),
                form_data: OAuth2PasswordRequestForm = Depends(),
                accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    if form_data.username is None:
        raise MissingUserFieldsException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username not provided")

    if form_data.password is None:
        raise MissingUserFieldsException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password not provided")

    if form_data.grant_type != 'password':
        raise InvalidGrantTypeException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grant type")

    user = await accounts_service.authenticate_user(form_data.username, form_data.password)

    if user is None:
        raise IncorrectFieldsException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    token_id = uuid.uuid4().hex

    access_token = create_access_token(user.id, identifier=token_id)
    access_token_expire_timestamp = int(time.time()) + (settings.access_token_expire_minutes * 60)
    access_token_redis_key = f"access_tokens:{user.id}"
    redis_client.zadd(access_token_redis_key, {access_token: access_token_expire_timestamp})

    refresh_token = create_refresh_token(user.id, identifier=token_id)
    encrypted_refresh_token = encrypt_refresh_token(refresh_token)
    refresh_token_expire_timestamp = int(time.time()) + (settings.refresh_token_expire_minutes * 60)
    refresh_token_redis_key = f"refresh_tokens:{user.id}"
    redis_client.zadd(refresh_token_redis_key, {encrypted_refresh_token: refresh_token_expire_timestamp})

    set_cookies(response, access_token, refresh_token)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/refresh', response_model=Token, status_code=status.HTTP_200_OK)
async def refresh(response: Response, request: RefreshTokenRequest, redis_client: cache = Depends(cache),
                  accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    refresh_token = request.refresh_token
    grant_type = request.grant_type

    if refresh_token is None:
        raise InvalidRefreshTokenException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token not provided")

    if grant_type != 'refresh_token':
        raise InvalidGrantTypeException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grant type")

    payload = accounts_service.get_payload(refresh_token, token_type='refresh')

    if payload is None:
        raise InvalidRefreshTokenException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    user = await accounts_service.get_user(payload.sub)

    if user is None:
        raise InvalidRefreshTokenException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid refresh token")

    current_timestamp = int(time.time())

    refresh_tokens_redis_key = f"refresh_tokens:{user.id}"

    redis_client.zremrangebyscore(refresh_tokens_redis_key, '-inf', current_timestamp)

    encrypted_refresh_tokens = redis_client.zrange(refresh_tokens_redis_key, 0, -1)

    encrypted_refresh_token = verify_refresh_token(refresh_token, encrypted_refresh_tokens)

    if not encrypted_refresh_token:
        raise InvalidRefreshTokenException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    redis_client.zrem(refresh_tokens_redis_key, encrypted_refresh_token)

    access_token_redis_key = f"access_tokens:{user.id}"

    access_tokens = redis_client.zrange(access_token_redis_key, 0, -1)
    for access_token in access_tokens:
        access_token_payload = accounts_service.get_payload(access_token)
        if access_token_payload.id == payload.id:
            redis_client.zrem(access_token_redis_key, access_token)
            break

    token_id = uuid.uuid4().hex

    new_access_token = create_access_token(user.id, identifier=token_id)
    access_token_expire_timestamp = current_timestamp + (settings.access_token_expire_minutes * 60)
    access_token_redis_key = f"access_tokens:{user.id}"
    redis_client.zadd(access_token_redis_key, {new_access_token: access_token_expire_timestamp})

    new_refresh_token = create_refresh_token(user.id, identifier=token_id)
    new_encrypted_refresh_token = encrypt_refresh_token(new_refresh_token)
    refresh_token_expire_timestamp = current_timestamp + (settings.refresh_token_expire_minutes * 60)
    redis_client.zadd(refresh_tokens_redis_key, {new_encrypted_refresh_token: refresh_token_expire_timestamp})

    set_cookies(response, new_access_token, new_refresh_token)

    return {'access_token': new_access_token, 'token_type': 'bearer'}


@router.post('/logout', status_code=status.HTTP_200_OK)
async def logout(response: Response, request: LogoutRequest, token: str = Depends(oauth2_scheme),
                 redis_client: cache = Depends(cache),
                 accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    refresh_token = request.refresh_token

    if refresh_token is None:
        raise InvalidRefreshTokenException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token not provided")

    user = await accounts_service.get_current_user(token)

    if user is None:
        raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

    current_timestamp = int(time.time())

    access_token_redis_key = f"access_tokens:{user.id}"

    redis_client.zremrangebyscore(access_token_redis_key, '-inf', current_timestamp)

    access_tokens = redis_client.zrange(access_token_redis_key, 0, -1)

    if not verify_access_token(token, access_tokens):
        raise InvalidCredentialsException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked",
                                          headers={"WWW-Authenticate": "Bearer"})

    refresh_tokens_redis_key = f"refresh_tokens:{user.id}"

    redis_client.zremrangebyscore(refresh_tokens_redis_key, '-inf', current_timestamp)

    encrypted_refresh_tokens = redis_client.zrange(refresh_tokens_redis_key, 0, -1)

    encrypted_refresh_token = verify_refresh_token(refresh_token, encrypted_refresh_tokens)

    if not encrypted_refresh_token:
        raise InvalidRefreshTokenException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    redis_client.zrem(access_token_redis_key, token)
    redis_client.zrem(refresh_tokens_redis_key, encrypted_refresh_token)

    unset_cookies(response)
    return {'message': 'Logout successful'}


@router.get("/", response_model=List[UserRead])
async def read_users(accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    return await accounts_service.get_all_users()


@router.get('/me', response_model=UserRead)
async def read_me(token: str = Depends(oauth2_scheme),
                  redis_client: cache = Depends(cache),
                  accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):

    user = await accounts_service.get_current_user(token)

    if user is None:
        raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

    current_timestamp = int(time.time())

    access_token_redis_key = f"access_tokens:{user.id}"

    redis_client.zremrangebyscore(access_token_redis_key, '-inf', current_timestamp)

    access_tokens = redis_client.zrange(access_token_redis_key, 0, -1)

    if not verify_access_token(token, access_tokens):
        raise InvalidCredentialsException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked",
                                          headers={"WWW-Authenticate": "Bearer"})

    return user


@router.get("/{username}/", response_model=UserRead)
async def read_user(
        username: str, accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    user = await accounts_service.get_user_by_username(username)

    if user is None:
        raise UserNotFoundException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user
