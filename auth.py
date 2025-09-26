"""Authentication and authorization routes."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from config import settings
from models import (
    User,
    Role,
    Permission,
    RBACAction,
    UserRole,
    RolePermission,
    RefreshToken,
    get_db,
)
from security import security_utils, RBACManager
from schemas import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    PasswordChange,
    RoleResponse,
    RoleCreate,
    RoleUpdate,
    PermissionResponse,
    UserListResponse,
    PaginationParams,
    SearchParams,
)
from dependencies import (
    get_current_user,
    get_current_active_user,
    require_admin,
    get_rate_limiter,
    rate_limit,
    audit_log,
    get_request_context,
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    rate_limiter=Depends(get_rate_limiter),
    request_context: dict = Depends(get_request_context),
):
    """Register a new user."""
    # Rate limiting
    client_ip = request_context.get("ip_address", "unknown")
    key = await rate_limiter.get_rate_limit_key("register", client_ip)
    is_allowed, _ = await rate_limiter.check_rate_limit(
        key, 5, 3600
    )  # 5 registrations per hour
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )

    # Check if user already exists
    existing_user_query = select(User).where(
        and_(
            (User.username == user_data.username.lower())
            | (User.email == user_data.email.lower())
        )
    )
    existing_user_result = await db.execute(existing_user_query)
    if existing_user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # Validate password strength
    password_issues = security_utils.validate_password_strength(user_data.password)
    if password_issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {'; '.join(password_issues)}",
        )

    # Create user
    hashed_password = security_utils.hash_password(user_data.password)
    user = User(
        username=user_data.username.lower(),
        email=user_data.email.lower(),
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_verified=False,  # Email verification required
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Assign default viewer role
    rbac_manager = RBACManager(db)
    await rbac_manager.assign_role_to_user(user.id, "viewer")

    # Get user roles for response
    user_roles = await rbac_manager.get_user_roles(user.id)

    # Audit log
    await audit_log(
        action="user_registered",
        resource_type="user",
        resource_id=str(user.id),
        details=f"New user registered: {user.username}",
        current_user=None,
        request_context=request_context,
        db=db,
    )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login=user.last_login,
        created_at=user.created_at,
        roles=user_roles,
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    rate_limiter=Depends(get_rate_limiter),
    request_context: dict = Depends(get_request_context),
):
    """Login user and return access token."""
    # Rate limiting
    client_ip = request_context.get("ip_address", "unknown")
    key = await rate_limiter.get_rate_limit_key(
        "login", f"{client_ip}:{form_data.username}"
    )
    is_allowed, _ = await rate_limiter.check_rate_limit(
        key, 10, 900
    )  # 10 attempts per 15 minutes
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    # Find user
    user_query = select(User).where(
        and_(
            (User.username == form_data.username.lower())
            | (User.email == form_data.username.lower()),
            User.is_active == True,
        )
    )
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user or not security_utils.verify_password(
        form_data.password, user.password_hash
    ):
        # Audit failed login
        await audit_log(
            action="login_failed",
            resource_type="user",
            details=f"Failed login attempt for: {form_data.username}",
            current_user=None,
            request_context=request_context,
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = security_utils.create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    refresh_token_raw, refresh_token_hash = security_utils.create_refresh_token()

    # Store refresh token
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=expires_at,
        device_info=request_context.get("user_agent", "unknown"),
    )
    db.add(refresh_token_obj)

    # Update last login
    user.last_login = datetime.utcnow()

    await db.commit()

    # Audit successful login
    await audit_log(
        action="login_success",
        resource_type="user",
        resource_id=str(user.id),
        details=f"User logged in: {user.username}",
        current_user=user,
        request_context=request_context,
        db=db,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token_raw,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
    request_context: dict = Depends(get_request_context),
):
    """Refresh access token using refresh token."""
    # Hash the provided refresh token
    token_hash = security_utils.generate_file_hash(refresh_token.encode())

    # Find valid refresh token
    token_query = select(RefreshToken).where(
        and_(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    token_result = await db.execute(token_query)
    refresh_token_obj = token_result.scalar_one_or_none()

    if not refresh_token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user
    user_query = select(User).where(
        and_(User.id == refresh_token_obj.user_id, User.is_active == True)
    )
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token = security_utils.create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    new_refresh_token_raw, new_refresh_token_hash = (
        security_utils.create_refresh_token()
    )

    # Revoke old refresh token
    refresh_token_obj.revoked_at = datetime.utcnow()

    # Store new refresh token
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token_obj = RefreshToken(
        user_id=user.id,
        token_hash=new_refresh_token_hash,
        expires_at=expires_at,
        device_info=request_context.get("user_agent", "unknown"),
    )
    db.add(new_refresh_token_obj)

    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token_raw,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    request_context: dict = Depends(get_request_context),
):
    """Logout user by revoking all refresh tokens."""
    # Revoke all user's refresh tokens
    await db.execute(
        select(RefreshToken)
        .where(
            and_(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        .update({"revoked_at": datetime.utcnow()})
    )

    await db.commit()

    # Audit logout
    await audit_log(
        action="logout",
        resource_type="user",
        resource_id=str(current_user.id),
        details=f"User logged out: {current_user.username}",
        current_user=current_user,
        request_context=request_context,
        db=db,
    )

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user information."""
    rbac_manager = RBACManager(db)
    user_roles = await rbac_manager.get_user_roles(current_user.id)

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        roles=user_roles,
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    request_context: dict = Depends(get_request_context),
):
    """Update current user information."""
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user_query = select(User).where(
            and_(User.email == user_update.email.lower(), User.id != current_user.id)
        )
        existing_user_result = await db.execute(existing_user_query)
        if existing_user_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = user_update.email.lower()
        current_user.is_verified = False  # Require re-verification

    # Update other fields
    if user_update.first_name is not None:
        current_user.first_name = user_update.first_name
    if user_update.last_name is not None:
        current_user.last_name = user_update.last_name

    current_user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    # Get updated roles
    rbac_manager = RBACManager(db)
    user_roles = await rbac_manager.get_user_roles(current_user.id)

    # Audit update
    await audit_log(
        action="user_updated",
        resource_type="user",
        resource_id=str(current_user.id),
        details=f"User updated profile: {current_user.username}",
        current_user=current_user,
        request_context=request_context,
        db=db,
    )

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        roles=user_roles,
    )


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    request_context: dict = Depends(get_request_context),
):
    """Change user password."""
    # Verify current password
    if not security_utils.verify_password(
        password_change.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    password_issues = security_utils.validate_password_strength(
        password_change.new_password
    )
    if password_issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {'; '.join(password_issues)}",
        )

    # Update password
    current_user.password_hash = security_utils.hash_password(
        password_change.new_password
    )
    current_user.updated_at = datetime.utcnow()

    # Revoke all refresh tokens (force re-login)
    await db.execute(
        select(RefreshToken)
        .where(
            and_(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        .update({"revoked_at": datetime.utcnow()})
    )

    await db.commit()

    # Audit password change
    await audit_log(
        action="password_changed",
        resource_type="user",
        resource_id=str(current_user.id),
        details=f"User changed password: {current_user.username}",
        current_user=current_user,
        request_context=request_context,
        db=db,
    )

    return {"message": "Password changed successfully. Please login again."}


# Admin-only endpoints
@router.get("/users", response_model=UserListResponse)
async def list_users(
    pagination: PaginationParams = Depends(),
    search: SearchParams = Depends(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    query = select(User)

    # Apply search filter
    if search.query:
        query = query.where(
            User.username.ilike(f"%{search.query}%")
            | User.email.ilike(f"%{search.query}%")
            | User.first_name.ilike(f"%{search.query}%")
            | User.last_name.ilike(f"%{search.query}%")
        )

    # Apply sorting
    if search.sort_by:
        sort_column = getattr(User, search.sort_by, None)
        if sort_column:
            if search.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(User.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset(pagination.offset).limit(pagination.size)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Get roles for each user
    rbac_manager = RBACManager(db)
    user_responses = []
    for user in users:
        user_roles = await rbac_manager.get_user_roles(user.id)
        user_responses.append(
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                last_login=user.last_login,
                created_at=user.created_at,
                roles=user_roles,
            )
        )

    return UserListResponse(
        users=user_responses, total=total, page=pagination.page, size=pagination.size
    )


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """List all roles (admin only)."""
    query = select(Role).order_by(Role.name)
    result = await db.execute(query)
    roles = result.scalars().all()

    role_responses = []
    for role in roles:
        # Get permissions for each role
        permissions_query = (
            select(Permission)
            .join(RolePermission)
            .where(RolePermission.role_id == role.id)
        )
        permissions_result = await db.execute(permissions_query)
        permissions = permissions_result.scalars().all()

        role_responses.append(
            RoleResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system_role=role.is_system_role,
                permissions=[
                    PermissionResponse(
                        id=perm.id,
                        resource=perm.resource,
                        action=perm.action.value,
                        description=perm.description,
                    )
                    for perm in permissions
                ],
            )
        )

    return role_responses
