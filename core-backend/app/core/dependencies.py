from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Query, Request
from typing import Annotated, AsyncGenerator, Optional
from core.security import verify_token, get_token_from_header
from typing import Annotated, AsyncGenerator, Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_async_db
from db.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current authenticated user information.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        User object with current user data
    """
    subject = verify_token(token.credentials)

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Get user from database using UserService
    from services.user_service import UserService

    user_service = UserService(db)
    user = await user_service.get_user_by_id(int(subject))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user
