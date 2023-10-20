import os
import time
import uuid

import aiofiles as aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.dependencies import get_accounts_service, cache
from app.v1.accounts.schedulers import scheduler
from app.v1.accounts.schemas import UserRead, UserCreate, Token, RefreshTokenRequest, LogoutRequest
from app.v1.accounts.service import AccountsService
from app.v1.accounts.utils import set_cookies, create_access_token, create_refresh_token, \
    unset_cookies, generate_image_resolutions, encrypt_refresh_token, verify_refresh_token, verify_blacklisted_token

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/accounts/login")

scheduler.start()

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(response: Response, background_tasks: BackgroundTasks, user: UserCreate = Depends(),
                   redis_client: cache = Depends(cache),
                   accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    existing_user = await accounts_service.get_user_by_username(user.username)

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    existing_email = await accounts_service.get_user_by_email(user.email)

    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    file = user.avatar
    media_img_url = ''

    if file and file.size > 0:
        if file.content_type not in ['image/jpeg', 'image/png', 'image/gif']:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                detail="Only .jpeg, .png, or .gif  files allowed")

        if file.size > settings.max_avatar_size:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                detail=f"File size should not exceed {settings.max_avatar_size} bytes")

        _, ext = os.path.splitext(file.filename)

        media_img_dir = os.path.join(settings.media_dir, 'accounts/avatars')
        static_img_dir = os.path.join(settings.static_dir, media_img_dir)

        os.makedirs(static_img_dir, exist_ok=True)
        content = await file.read()
        file_name = f'{uuid.uuid4().hex}-avatar{ext}'

        static_img_file = os.path.join(static_img_dir, file_name)
        media_img_url = os.path.join(media_img_dir, file_name)

        async with aiofiles.open(static_img_file, mode='wb') as f:
            await f.write(content)

        background_tasks.add_task(generate_image_resolutions, file_path=static_img_file, sizes=settings.avatar_sizes)

    user = await accounts_service.create_user(user, media_img_url)

    access_token = create_access_token(user.id)

    refresh_token = create_refresh_token()

    encrypted_refresh_token = encrypt_refresh_token(refresh_token)
    expire_timestamp = int(time.time()) + (settings.refresh_token_expire_minutes * 60)
    redis_key = f"refresh_tokens:{user.id}"
    redis_client.zadd(redis_key, {encrypted_refresh_token: expire_timestamp})

    set_cookies(response, access_token, refresh_token)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(response: Response, redis_client: cache = Depends(cache),
                form_data: OAuth2PasswordRequestForm = Depends(),
                accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):

    if form_data.username is None or form_data.password is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or password not provided")

    if form_data.grant_type != 'password':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grant type")

    user = await accounts_service.authenticate_user(form_data.username, form_data.password)

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(user.id)

    refresh_token = create_refresh_token()

    encrypted_refresh_token = encrypt_refresh_token(refresh_token)

    expire_timestamp = int(time.time()) + (settings.refresh_token_expire_minutes * 60)
    redis_key = f"refresh_tokens:{user.id}"
    redis_client.zadd(redis_key, {encrypted_refresh_token: expire_timestamp})

    set_cookies(response, access_token, refresh_token)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get('/refresh', response_model=Token, status_code=status.HTTP_200_OK)
async def refresh(response: Response, request: RefreshTokenRequest, redis_client: cache = Depends(cache),
                  token: str = Depends(oauth2_scheme),
                  accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    refresh_token = request.refresh_token
    grant_type = request.grant_type

    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token not provided")

    if grant_type != 'refresh_token':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grant type")

    user = await accounts_service.get_current_user(token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_timestamp = int(time.time())

    access_token_blacklist_redis_key = f"blacklisted_access_tokens:{user.id}"

    redis_client.zremrangebyscore(access_token_blacklist_redis_key, '-inf', current_timestamp)

    blacklisted_tokens = redis_client.zrange(access_token_blacklist_redis_key, 0, -1)

    if verify_blacklisted_token(token, blacklisted_tokens):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    refresh_tokens_redis_key = f"refresh_tokens:{user.id}"

    redis_client.zremrangebyscore(refresh_tokens_redis_key, '-inf', current_timestamp)

    encrypted_refresh_tokens = redis_client.zrange(refresh_tokens_redis_key, 0, -1)

    encrypted_refresh_token = verify_refresh_token(refresh_token, encrypted_refresh_tokens)

    if not encrypted_refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    redis_client.zrem(refresh_tokens_redis_key, encrypted_refresh_token)

    access_token_expire_timestamp = current_timestamp + (settings.access_token_expire_minutes * 60)
    redis_client.zadd(access_token_blacklist_redis_key, {token: access_token_expire_timestamp})

    new_access_token = create_access_token(user.id)

    new_refresh_token = create_refresh_token()

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token not provided")

    user = await accounts_service.get_current_user(token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_timestamp = int(time.time())

    access_token_blacklist_redis_key = f"blacklisted_access_tokens:{user.id}"

    redis_client.zremrangebyscore(access_token_blacklist_redis_key, '-inf', current_timestamp)

    blacklisted_tokens = redis_client.zrange(access_token_blacklist_redis_key, 0, -1)

    if verify_blacklisted_token(token, blacklisted_tokens):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    refresh_tokens_redis_key = f"refresh_tokens:{user.id}"

    redis_client.zremrangebyscore(refresh_tokens_redis_key, '-inf', current_timestamp)

    encrypted_refresh_tokens = redis_client.zrange(refresh_tokens_redis_key, 0, -1)

    encrypted_refresh_token = verify_refresh_token(refresh_token, encrypted_refresh_tokens)

    if not encrypted_refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    redis_client.zrem(refresh_tokens_redis_key, encrypted_refresh_token)

    access_token_expire_timestamp = current_timestamp + (settings.access_token_expire_minutes * 60)
    redis_client.zadd(access_token_blacklist_redis_key, {token: access_token_expire_timestamp})

    unset_cookies(response)
    return {'message': 'Logout successful'}


@router.get("/", response_model=list[UserRead])
async def read_users(accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    return await accounts_service.get_all_users()


@router.get('/me', response_model=UserRead)
async def read_me(token: str = Depends(oauth2_scheme),
                  redis_client: cache = Depends(cache),
                  accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    user = await accounts_service.get_current_user(token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_timestamp = int(time.time())

    access_token_blacklist_redis_key = f"blacklisted_access_tokens:{user.id}"

    redis_client.zremrangebyscore(access_token_blacklist_redis_key, '-inf', current_timestamp)

    blacklisted_tokens = redis_client.zrange(access_token_blacklist_redis_key, 0, -1)

    if verify_blacklisted_token(token, blacklisted_tokens):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    return user


@router.get("/{username}/", response_model=UserRead)
async def read_user(
        username: str, accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    user = await accounts_service.get_user_by_username(username)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
