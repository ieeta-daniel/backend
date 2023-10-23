from typing import Optional

from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str = "OK"


class PaginationMetadata(BaseModel):
    total: int
    total_pages: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None
