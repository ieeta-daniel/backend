import os
import time

from fastapi import APIRouter, status, Depends, HTTPException

from app.config import settings
from app.dependencies import get_accounts_service, cache
from app.v1.accounts.service import AccountsService
from app.v1.accounts.utils import verify_blacklisted_token
from app.v1.models.schemas import ModelRepositoryCreate
from app.v1.accounts.controller import oauth2_scheme

router = APIRouter()

@router.post("/create", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_model_repository(
        model: ModelRepositoryCreate,
        redis_client: cache = Depends(cache),
        token: str = Depends(oauth2_scheme),
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

    model_repository_dir = os.path.join(settings.models_dir, user.username, model.name)
    static_model_repository_dir = os.path.join(settings.static_dir, model_repository_dir)

    os.makedirs(static_model_repository_dir, exist_ok=True)

    

    return "Model created"
