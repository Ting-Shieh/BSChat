from fastapi import APIRouter

from app.api.v1 import (
    auth,
    capture,
    companies,
    contacts,
    enterprise,
    me,
    ops_enterprise,
    orgs,
    public_cards,
    search,
    teams,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(teams.router)
api_router.include_router(enterprise.router)
api_router.include_router(ops_enterprise.router)
api_router.include_router(orgs.router)
api_router.include_router(public_cards.router)
api_router.include_router(capture.router, tags=["capture"])
api_router.include_router(contacts.router, tags=["contacts"])
api_router.include_router(companies.router, tags=["companies"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
