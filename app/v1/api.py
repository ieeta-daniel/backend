from fastapi import APIRouter
from app.v1.accounts.controller import router as accounts_router

router = APIRouter()

router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
