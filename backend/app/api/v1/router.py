from fastapi import APIRouter

from app.api.v1.endpoints import upload
from app.api.v1.endpoints import auth, categorization, dashboard, transactions

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(upload.router)
api_router.include_router(transactions.router)
api_router.include_router(categorization.router)
api_router.include_router(dashboard.router)
