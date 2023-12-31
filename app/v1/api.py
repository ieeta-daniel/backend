from fastapi import APIRouter
from app.v1.accounts.controller import router as accounts_router
from app.v1.models.controller import router as models_router
from app.v1.repositories.controller import router as repositories_router

router = APIRouter()

router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])

# router.include_router(repositories_router, prefix="/repositories", tags=["repositories"])

router.include_router(models_router, prefix="/models", tags=["models"])
