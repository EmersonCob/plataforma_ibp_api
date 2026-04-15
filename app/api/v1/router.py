from fastapi import APIRouter

from app.api.v1 import auth, clients, contracts, dashboard, notifications, public_signatures

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(clients.router)
api_router.include_router(contracts.router)
api_router.include_router(public_signatures.router)
api_router.include_router(dashboard.router)
api_router.include_router(notifications.router)

