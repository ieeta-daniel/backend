import os
import time
from typing import Optional

import aiofiles
from fastapi import APIRouter, status, Depends, Query
from app.config import settings
from app.dependencies import get_accounts_service, cache, get_repositories_service
from app.schemas import PaginationMetadata
from app.v1.accounts.exceptions import InvalidCredentialsException
from app.v1.accounts.service import AccountsService
from app.v1.accounts.utils import verify_access_token
from app.v1.repositories.exceptions import RepositoryNotFoundException, UnauthorizedRepositoryAccessException
from app.v1.repositories.schemas import RepositoryCreate, RepositoryRead, RepositoryReadWithUser, \
    PaginatedRepositoryResponse, UploadFilesResponse
from app.v1.accounts.controller import oauth2_scheme, optional_oauth2_scheme
from app.v1.repositories.service import RepositoriesService

router = APIRouter()


@router.post("/create", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def create_repository(
        model: RepositoryCreate,
        redis_client: cache = Depends(cache),
        token: str = Depends(oauth2_scheme),
        repositories_service: RepositoriesService = Depends(get_repositories_service(RepositoriesService)),
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
        raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN, detail="Token revoked", headers={"WWW-Authenticate": "Bearer"})

    model_repository_dir = os.path.join(settings.models_dir, user.username, model.name)
    static_model_repository_dir = os.path.join(settings.static_dir, model_repository_dir)

    os.makedirs(static_model_repository_dir, exist_ok=True)

    repository = await repositories_service.create_repository(model, owner=user, path=model_repository_dir)

    return repository


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
        response: UploadFilesResponse = Depends(),
        token: str = Depends(oauth2_scheme),
        repositories_service: RepositoriesService = Depends(get_repositories_service(RepositoriesService)),
        accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):

    user = await accounts_service.get_current_user(token)

    if user is None:
        raise InvalidCredentialsException(status_code=status.HTTP_403_FORBIDDEN,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

    repository = await repositories_service.get_repository(response.repository_id)

    if not repository:
        raise RepositoryNotFoundException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if repository.owner_id != user.id:
        raise UnauthorizedRepositoryAccessException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this repository")

    static_repository_dir = os.path.join(settings.static_dir, repository.path)

    os.makedirs(static_repository_dir, exist_ok=True)

    for file in response.files:
        file_path = os.path.join(static_repository_dir, file.filename)
        async with aiofiles.open(file_path, "wb") as buffer:
            while content := await file.read(1024):
                await buffer.write(content)

    return {"detail": "File uploaded successfully"}


@router.get("/",
            response_model=PaginatedRepositoryResponse,
            status_code=status.HTTP_200_OK)
async def read_repositories(
        token: str | None = Depends(optional_oauth2_scheme),
        include_count: bool = Query(False, description="Include total count of repositories"),
        page: Optional[int] = Query(None, description="Page number", ge=1),
        per_page: Optional[int] = Query(None, description="Items per page", le=100),
        repositories_service: RepositoriesService = Depends(get_repositories_service(RepositoriesService)),
        accounts_service: AccountsService = Depends(get_accounts_service(AccountsService))):
    if token is not None and (user := await accounts_service.get_current_user(token)) is not None:
        repositories, total = await repositories_service.get_all_repositories(
            page, per_page, include_count, only_public=True, owner_id=user.id)
    else:
        repositories, total = await repositories_service.get_all_repositories(
            page, per_page, include_count, only_public=True)

    pagination_metadata = (
        PaginationMetadata(total=total, page=page, per_page=per_page, total_pages=total // per_page + 1)
        if include_count and total
        else PaginationMetadata(total=total) if include_count else None)

    repositories = [RepositoryReadWithUser.model_validate(repository) for repository in repositories]

    response_data = PaginatedRepositoryResponse(repositories=repositories, metadata=pagination_metadata)

    return response_data
