import uuid
from typing import Any, Callable, Optional, Sequence
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db, set_db_current_user_id
from app.db.models.tenant import User, UserRole, AuditLog

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload invalid: missing subject",
            )
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account removed",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Configure PostgreSQL session variable for Row-Level Security
    await set_db_current_user_id(db, user.id)

    # Attach to request state for audit logs
    request.state.current_user = user
    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        await set_db_current_user_id(db, None)
        return None
    try:
        return await get_current_user(request=request, credentials=credentials, db=db)
    except HTTPException:
        await set_db_current_user_id(db, None)
        return None


def require_roles(*allowed_roles: str | UserRole) -> Callable:
    """Dependency factory checking that the authenticated user possesses one of the allowed roles."""
    normalized_roles = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    async def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_role_str = (
            current_user.role.value
            if isinstance(current_user.role, UserRole)
            else str(current_user.role)
        )

        if user_role_str not in normalized_roles:
            # Audit log failed privilege escalation attempt
            await log_audit_event(
                db=db,
                action="privilege_escalation_denied",
                resource_type="rbac_gate",
                resource_id=request.url.path,
                actor_user_id=current_user.id,
                metadata={
                    "user_role": user_role_str,
                    "required_roles": normalized_roles,
                    "method": request.method,
                },
                ip_address=request.client.host if request.client else None,
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires one of roles: {normalized_roles}",
            )
        return current_user

    return role_checker


async def log_audit_event(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Helper to record security and administrative actions in tenant.audit_logs."""
    audit = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_=metadata or {},
        ip_address=ip_address,
    )
    db.add(audit)
    await db.flush()
    return audit
