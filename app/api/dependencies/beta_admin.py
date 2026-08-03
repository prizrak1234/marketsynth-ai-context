"""Beta admin dashboard access (Phase AI.89)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.api.dependencies.auth import require_active_user_unrestricted
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.schemas.contracts import UserRole


async def require_beta_admin_access(
    current_user: Annotated[UserTable, Depends(require_active_user_unrestricted)],
) -> UserTable:
    settings = get_settings()
    if not settings.beta_admin_access_allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if settings.is_production and current_user.role not in (
        UserRole.ADMIN,
        UserRole.OWNER,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Beta admin dashboard requires admin or owner role in production",
        )
    return current_user
