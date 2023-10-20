from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.v1.api import router as v1_router
from app.database import create_db_and_tables
from app.schemas import HealthCheck

app = FastAPI(
    title=settings.title,
    version=settings.version,
    description=settings.description,
)

origins = [
    'localhost',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(settings.media_path, StaticFiles(directory=settings.static_dir + settings.media_dir), name="media")
app.mount(settings.models_path, StaticFiles(directory=settings.static_dir + settings.models_dir), name="models")

app.include_router(v1_router, prefix="/v1", include_in_schema=True)


@app.on_event("startup")
async def startup():
    await create_db_and_tables()


@app.on_event("shutdown")
async def shutdown():
    pass


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
