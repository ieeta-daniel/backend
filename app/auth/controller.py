import pickle
from fastapi import APIRouter, Depends, HTTPException
from app.auth.models import User
from app.auth.schemas import UserRead, UserCreate
from app.auth.service import AuthService
from app.dependencies import get_auth_service, cache

router = APIRouter()


@router.post("/", response_model=UserRead)
async def create_new_user(user: UserCreate, auth_service: AuthService = Depends(get_auth_service(AuthService))):
    existing_user = await auth_service.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    existing_email = await auth_service.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    return await auth_service.create_user(user)


@router.get("/", response_model=list[UserRead])
async def read_users(auth_service: AuthService = Depends(get_auth_service(AuthService))):
    return await auth_service.get_all_users()


@router.get("/{user_id}/", response_model=UserRead)
async def read_user(
        user_id: int,
        redis_client: cache = Depends(cache),
        auth_service: AuthService = Depends(get_auth_service(AuthService))
):
    cached_user = redis_client.get(f"user:{user_id}")

    if cached_user:
        return pickle.loads(cached_user)

    user = await auth_service.get_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_json = pickle.dumps(user)

    redis_client.setex(f"user:{user_id}", 3600, user_json)

    return user
