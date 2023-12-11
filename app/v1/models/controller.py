import os
import time
from typing import Optional

import aiofiles
from fastapi import APIRouter, status, Depends, Query
from app.config import settings
from app.dependencies import get_accounts_service, cache, get_models_service
from app.schemas import PaginationMetadata
from app.v1.accounts.exceptions import InvalidCredentialsException
from app.v1.accounts.service import AccountsService
from app.v1.accounts.utils import verify_access_token
from app.v1.models.exceptions import ModelNotFoundException, UnauthorizedModelAccessException
from app.v1.models.schemas import ModelCreate, ModelRead, ModelReadWithUser, \
    PaginatedModelResponse, UploadFilesResponse
from app.v1.accounts.controller import oauth2_scheme, optional_oauth2_scheme
from app.v1.models.service import ModelsService

router = APIRouter()


@router.post("/create", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
async def create_model(
        model: ModelCreate,
        redis_client: cache = Depends(cache),
        token: str = Depends(oauth2_scheme),
        models_service: ModelsService = Depends(get_models_service(ModelsService)),
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
        raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN, detail="Token revoked",
                                          headers={"WWW-Authenticate": "Bearer"})

    model_model_dir = os.path.join(settings.models_dir, user.username, model.name)
    static_model_model_dir = os.path.join(settings.static_dir, model_model_dir)

    os.makedirs(static_model_model_dir, exist_ok=True)

    model = await models_service.create_model(model, owner=user, path=model_model_dir)

    return model


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
        response: UploadFilesResponse = Depends(),
        token: str = Depends(oauth2_scheme),
        models_service: ModelsService = Depends(get_models_service(ModelsService)),
        accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    user = await accounts_service.get_current_user(token)

    if user is None:
        raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

    model = await models_service.get_model(response.model_id)

    if not model:
        raise ModelNotFoundException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    if model.owner_id != user.id:
        raise UnauthorizedModelAccessException(status_code=status.HTTP_403_FORBIDDEN,
                                               detail="You do not have permission to access this model")

    static_model_dir = os.path.join(settings.static_dir, model.path)

    os.makedirs(static_model_dir, exist_ok=True)

    for file in response.files:
        file_path = os.path.join(static_model_dir, file.filename)
        async with aiofiles.open(file_path, "wb") as buffer:
            while content := await file.read(1024):
                await buffer.write(content)

    return {"detail": "File uploaded successfully"}


@router.get("/",
            response_model=PaginatedModelResponse,
            status_code=status.HTTP_200_OK)
async def read_models(
        token: str | None = Depends(optional_oauth2_scheme),
        include_count: bool = Query(False, description="Include total count of models"),
        page: Optional[int] = Query(None, description="Page number", ge=1),
        per_page: Optional[int] = Query(None, description="Items per page", le=100),
        models_service: ModelsService = Depends(get_models_service(ModelsService)),
        accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    if token is not None and (user := await accounts_service.get_current_user(token)) is not None:
        models, total = await models_service.get_all_models(
            page, per_page, include_count, only_public=True, owner_id=user.id)
    else:
        models, total = await models_service.get_all_models(
            page, per_page, include_count, only_public=True)

    pagination_metadata = (
        PaginationMetadata(total=total, page=page, per_page=per_page, total_pages=total // per_page + 1)
        if include_count and total
        else PaginationMetadata(total=total) if include_count else None)

    models = [ModelReadWithUser.model_validate(model) for model in models]

    response_data = PaginatedModelResponse(models=models, metadata=pagination_metadata)

    return response_data


@router.get("/{username}/{model_name}",
            response_model=ModelReadWithUser,
            status_code=status.HTTP_200_OK)
async def read_user_model(
        username: str,
        model_name: str,
        token: str | None = Depends(optional_oauth2_scheme),
        models_service: ModelsService = Depends(get_models_service(ModelsService)),
        accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    user = await accounts_service.get_user_by_username(username)

    if user is None:
        raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

    model = await models_service.get_model_by_name(user.id, model_name)

    if model is None:
        raise ModelNotFoundException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    if model.private:
        if token is None:
            raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN,
                                              detail="Could not validate credentials",
                                              headers={"WWW-Authenticate": "Bearer"})

        if not (user := await accounts_service.get_current_user(token)):
            raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN,
                                              detail="Could not validate credentials",
                                              headers={"WWW-Authenticate": "Bearer"})

        if model.owner_id != user.id:
            raise UnauthorizedModelAccessException(status_code=status.HTTP_403_FORBIDDEN,
                                                   detail="You do not have permission to access this model")

    # for some reason, I can't call model.validate() in the return statement
    model = ModelReadWithUser.model_validate(model)

    return model
