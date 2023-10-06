from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse

from app.config import settings
from app.v1.api import router as v1_router
from app.database import create_db_and_tables
from app.schemas import HealthCheck

app = FastAPI(
    title=settings.title,
    version=settings.version,
    description=settings.description,
)

app.include_router(v1_router, prefix="/v1", include_in_schema=True)

@app.on_event("startup")
async def startup():
    await create_db_and_tables()

@app.get('/', response_class=RedirectResponse, include_in_schema=False)
async def docs():
    return RedirectResponse(url='/docs')

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
