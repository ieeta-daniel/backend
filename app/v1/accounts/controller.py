import os
import pickle
import uuid
from typing import Optional

import aiofiles as aiofiles
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.config import settings
from app.dependencies import get_auth_service, cache
from app.v1.accounts.schemas import UserRead, UserCreate, Token
from app.v1.accounts.service import AccountsService
from app.v1.accounts.utils import set_cookies, create_access_token, create_refresh_token, \
    unset_cookies, generate_image_resolutions

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/accounts/login")


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(response: Response, background_tasks: BackgroundTasks, user: UserCreate = Depends(), redis_client: cache = Depends(cache),
                   auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
    existing_user = await auth_service.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    existing_email = await auth_service.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    file = user.avatar
    file_url = ''

    print(file)

    if file and file.size > 0:
        _, ext = os.path.splitext(file.filename)
        img_dir = os.path.join(settings.media, 'accounts/avatars')
        print(img_dir)
        os.makedirs(img_dir, exist_ok=True)
        content = await file.read()
        if file.content_type not in ['image/jpeg', 'image/png', 'image/gif']:
            raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                detail="Only .jpeg, .png, or .gif  files allowed")
        file_name = f'{uuid.uuid4().hex}-avatar{ext}'

        print(file_name)
        file_url = os.path.join(img_dir, file_name)

        async with aiofiles.open(file_url, mode='wb') as f:
            await f.write(content)

        print(file_url + "hello")

        background_tasks.add_task(generate_image_resolutions, file_url=file_url, sizes=settings.avatar_sizes)


    print(file_url + "jambo")
    user = await auth_service.create_user(user, file_url)

    print(user)

    access_token = create_access_token(user.id)

    refresh_token = create_refresh_token(user.id)

    redis_key = f"refresh_tokens:{user.id}"

    redis_client.setex(redis_key, settings.refresh_token_expire_minutes * 60, refresh_token)

    set_cookies(response, access_token, refresh_token)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(response: Response, redis_client: cache = Depends(cache),
                form_data: OAuth2PasswordRequestForm = Depends(),
                auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
    user = await auth_service.authenticate_user(form_data.username, form_data.password)

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token = create_access_token(user.id)

    refresh_token = create_refresh_token(user.id)

    redis_key = f"refresh_tokens:{user.id}"
    redis_client.setex(redis_key, settings.refresh_token_expire_minutes * 60, refresh_token)

    set_cookies(response, access_token, refresh_token)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get('/refresh', response_model=Token, status_code=status.HTTP_200_OK)
async def refresh(response: Response, refresh_token: Optional[str] = Cookie(None),
                  accounts_service: AccountsService = Depends(get_auth_service(AccountsService))):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Please provide refresh token')

    user = await accounts_service.get_current_user_by_refresh_token(refresh_token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    set_cookies(response, access_token, refresh_token)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get('/logout', status_code=status.HTTP_200_OK)
def logout(response: Response, token: str = Depends(oauth2_scheme)):
    unset_cookies(response)
    return {'message': 'Logout successful'}


@router.get("/", response_model=list[UserRead])
async def read_users(auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
    return await auth_service.get_all_users()


@router.get('/me', response_model=UserRead)
async def read_me(token: str = Depends(oauth2_scheme),
                  auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
    user = await auth_service.get_current_user(token)
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
        redis_client: cache = Depends(cache),
        auth_service: AccountsService = Depends(get_auth_service(AccountsService))
):
    cached_user = redis_client.get(f"user:{username}")

    if cached_user:
        return pickle.loads(cached_user)

    user = await auth_service.get_user_by_username(username)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_json = pickle.dumps(user)

    redis_client.setex(f"user:{username}", 3600, user_json)

    return user
