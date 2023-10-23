import datetime
import uuid
from typing import Optional, Union, List

from fastapi import UploadFile, File
from pydantic import BaseModel

from app.schemas import PaginationMetadata
from app.utils import as_form
from app.v1.accounts.schemas import UserRead


@as_form
class RepositoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    private: bool = False


class RepositoryRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    private: bool
    created_at: datetime.datetime
    path: str
    owner_id: uuid.UUID


class RepositoryReadWithUser(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    private: bool
    created_at: datetime.datetime
    path: str
    owner: UserRead

    class Config:
        from_attributes = True


class PaginatedRepositoryResponse(BaseModel):
    repositories: List[RepositoryReadWithUser]
    metadata: Optional[PaginationMetadata] = None


@as_form
class UploadFilesResponse(BaseModel):
    files: List[UploadFile] = File(...)
    repository_id: uuid.UUID
