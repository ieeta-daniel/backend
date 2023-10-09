import os
import time
import uuid

import aiofiles as aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.dependencies import get_accounts_service, cache
from app.v1.accounts.schedulers import clear_expired_refresh_token_scheduler
from app.v1.accounts.schemas import UserRead, UserCreate, Token, RefreshTokenRequest
from app.v1.accounts.service import AccountsService
from app.v1.accounts.utils import set_cookies, create_access_token, create_refresh_token, \
    unset_cookies, generate_image_resolutions, encrypt_refresh_token, verify_refresh_token

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/accounts/login")

clear_expired_refresh_token_scheduler.start()


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
    file_url = ''

    if file and file.size > 0:
        if file.content_type not in ['image/jpeg', 'image/png', 'image/gif']:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                detail="Only .jpeg, .png, or .gif  files allowed")

        if file.size > settings.max_avatar_size:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                detail=f"File size should not exceed {settings.max_avatar_size} bytes")

        _, ext = os.path.splitext(file.filename)
        img_dir = os.path.join(settings.media, 'accounts/avatars')

        os.makedirs(img_dir, exist_ok=True)
        content = await file.read()
        file_name = f'{uuid.uuid4().hex}-avatar{ext}'

        file_url = os.path.join(img_dir, file_name)

        async with aiofiles.open(file_url, mode='wb') as f:
            await f.write(content)

        background_tasks.add_task(generate_image_resolutions, file_url=file_url, sizes=settings.avatar_sizes)

    user = await accounts_service.create_user(user, file_url)

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
async def refresh(response: Response, request: RefreshTokenRequest = Depends(), redis_client: cache = Depends(cache),
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

    redis_key = f"refresh_tokens:{user.id}"

    current_timestamp = int(time.time())
    redis_client.zremrangebyscore(redis_key, '-inf', current_timestamp)

    encrypted_refresh_tokens = redis_client.zrange(redis_key, 0, -1)

    if not encrypted_refresh_tokens:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token not found")

    encrypted_refresh_token = verify_refresh_token(refresh_token, encrypted_refresh_tokens)

    if not encrypted_refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token")

    redis_client.zrem(redis_key, encrypted_refresh_token)

    new_access_token = create_access_token(user.id)

    new_refresh_token = create_refresh_token()

    new_encrypted_refresh_token = encrypt_refresh_token(new_refresh_token)
    expire_timestamp = int(time.time()) + (settings.refresh_token_expire_minutes * 60)
    redis_client.zadd(redis_key, {new_encrypted_refresh_token: expire_timestamp})

    set_cookies(response, new_access_token, new_refresh_token)

    return {'access_token': new_access_token, 'token_type': 'bearer'}


@router.get('/logout', status_code=status.HTTP_200_OK)
def logout(response: Response, token: str = Depends(oauth2_scheme)):
    unset_cookies(response)
    return {'message': 'Logout successful'}


@router.get("/", response_model=list[UserRead])
async def read_users(accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    return await accounts_service.get_all_users()


@router.get('/me', response_model=UserRead)
async def read_me(token: str = Depends(oauth2_scheme),
                  accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    user = await accounts_service.get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get("/{username}/", response_model=UserRead)
async def read_user(
        username: str,
        accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))
):
    user = await accounts_service.get_user_by_username(username)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
