from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token
from app.core.db import get_db
from app.models.user import User, UserEntitlement, Workspace
from app.schemas.auth import DevLoginRequest, TokenResponse

router = APIRouter()


@router.post("/dev-login", response_model=TokenResponse, summary="M1 dev login (MVP only)")
async def dev_login(body: DevLoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Create or fetch dev user and return JWT. Disable in production."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=body.email, display_name=body.display_name)
        db.add(user)
        await db.flush()
        workspace = Workspace(owner_user_id=user.id, name="Personal")
        entitlement = UserEntitlement(user_id=user.id)
        db.add(workspace)
        db.add(entitlement)
        await db.commit()
        await db.refresh(user)
    else:
        await db.commit()

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
