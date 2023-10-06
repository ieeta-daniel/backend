import pickle

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.dependencies import get_auth_service, cache
from app.v1.accounts.schemas import UserRead, UserCreate, Token
from app.v1.accounts.service import AccountsService

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/accounts/login", scheme_name="JWT")

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
    existing_user = await auth_service.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    existing_email = await auth_service.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    _, (access_token, refresh_token) = await auth_service.create_user(user)
    return {'access_token': access_token, 'refresh_token': refresh_token}


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
    user, (access_token, refresh_token) = await auth_service.authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {'access_token': access_token, 'refresh_token': refresh_token}


@router.get("/", response_model=list[UserRead])
async def read_users(auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
    return await auth_service.get_all_users()


@router.get('/me', response_model=UserRead)
async def read_me(token: str = Depends(oauth2_scheme), auth_service: AccountsService = Depends(get_auth_service(AccountsService))):
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
