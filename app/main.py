from fastapi import FastAPI, status
from app.config import settings
from app.auth import controller
from app.database import create_db_and_tables
from app.schemas import HealthCheck
from app.auth import models

app = FastAPI(
    title=settings.title,
    version=settings.version,
    description=settings.description,
)

app.include_router(controller.router, prefix="/users", tags=["users"])


@app.on_event("startup")
async def startup():
    await create_db_and_tables()


@app.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
async def get_health():
    return HealthCheck(status="OK")
