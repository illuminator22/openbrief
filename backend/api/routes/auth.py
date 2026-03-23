"""Authentication dependencies for OpenBrief.

DEV PLACEHOLDER — Phase 6 will replace this with real auth
(JWT tokens, password hashing via python-jose + passlib).
The current implementation auto-creates a single dev user
so that endpoints requiring a user can function during development.
"""

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import User

# Email used for the auto-created dev user
_DEV_USER_EMAIL = "dev@openbrief.local"


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the current authenticated user.

    DEV PLACEHOLDER — Returns a real user record from the database.
    Creates a default dev user on first call, reuses it after.
    Replace with real auth in Phase 6.
    """
    result = await db.execute(
        select(User).where(User.email == _DEV_USER_EMAIL)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=_DEV_USER_EMAIL)
        db.add(user)
        await db.flush()

    return user
