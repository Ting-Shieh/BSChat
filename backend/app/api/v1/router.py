from fastapi import APIRouter

from app.api.v1 import auth, capture, companies, contacts, me, orgs, search

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(orgs.router)
api_router.include_router(capture.router, tags=["capture"])
api_router.include_router(contacts.router, tags=["contacts"])
api_router.include_router(companies.router, tags=["companies"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
