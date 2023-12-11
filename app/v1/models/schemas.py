import datetime
import uuid
from typing import Optional, List

from fastapi import UploadFile, File
from pydantic import BaseModel

from app.schemas import PaginationMetadata
from app.utils import as_form
from app.v1.accounts.schemas import UserRead


@as_form
class ModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    endpoint: Optional[str] = None
    private: bool = False
    readme: Optional[bool] = False


class ModelRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    endpoint: Optional[str] = None
    type: str
    private: bool
    created_at: datetime.datetime
    path: str
    owner_id: uuid.UUID


class ModelReadWithUser(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    private: bool
    created_at: datetime.datetime
    path: str
    endpoint: Optional[str] = None
    type: str
    owner: UserRead

    class Config:
        from_attributes = True


class PaginatedModelResponse(BaseModel):
    models: List[ModelReadWithUser]
    metadata: Optional[PaginationMetadata] = None


@as_form
class UploadFilesResponse(BaseModel):
    files: List[UploadFile] = File(...)
    model_id: uuid.UUID
