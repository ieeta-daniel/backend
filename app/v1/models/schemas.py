from pydantic import BaseModel

from app.utils import as_form


@as_form
class ModelRepositoryCreate(BaseModel):
    name: str
    description: str

