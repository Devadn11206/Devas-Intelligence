from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.db.session import get_db, set_db_current_user_id
from app.db.models.tenant import (
    User,
    UserRole,
    RefreshToken,
    UserPreference,
    OrganizationMember,
    DigestFrequency,
)
from app.api.deps import get_current_user, log_audit_event
from app.schemas.tenant import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    OrgMembershipResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # 1. Check if email already exists
    existing = await db.execute(select(User).where(User.email == req.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # 2. Create User
    new_user = User(
        email=req.email.lower(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db.add(new_user)
    await db.flush()

    # 3. Create default UserPreference row under current_user RLS context
    await set_db_current_user_id(db, new_user.id)
    default_pref = UserPreference(
        user_id=new_user.id,
        followed_topics=["AI Agents", "LLM Inference", "Open Source AI"],
        followed_technologies=["vLLM", "PyTorch", "Transformers"],
        followed_repos=["vllm-project/vllm", "huggingface/transformers"],
        digest_frequency=DigestFrequency.WEEKLY,
    )
    db.add(default_pref)

    # 4. Issue Tokens
    access_token = create_access_token(
        subject=new_user.id,
        role=new_user.role.value if isinstance(new_user.role, UserRole) else str(new_user.role),
    )
    raw_refresh, refresh_hash, refresh_exp = generate_refresh_token()
    token_row = RefreshToken(
        user_id=new_user.id,
        token_hash=refresh_hash,
        expires_at=refresh_exp,
        revoked=False,
    )
    db.add(token_row)

    # 5. Audit Log
    await log_audit_event(
        db=db,
        action="user_registered",
        resource_type="user",
        resource_id=str(new_user.id),
        actor_user_id=new_user.id,
        metadata={"email": new_user.email, "role": "user"},
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # 1. Lookup user
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # 2. Issue Tokens
    user_role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
    access_token = create_access_token(subject=user.id, role=user_role)
    raw_refresh, refresh_hash, refresh_exp = generate_refresh_token()

    token_row = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=refresh_exp,
        revoked=False,
    )
    db.add(token_row)

    # 3. Audit Log
    await log_audit_event(
        db=db,
        action="user_login",
        resource_type="auth",
        resource_id=str(user.id),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    req: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    token_hash = hash_token(req.refresh_token)

    # 1. Query token record
    res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token_record = res.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # 2. Reuse Detection: If token is already revoked, breach suspected! Revoke all tokens for this user.
    if token_record.revoked:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_record.user_id)
            .values(revoked=True)
        )
        await db.commit()
        await log_audit_event(
            db=db,
            action="refresh_token_reuse_detected",
            resource_type="auth",
            resource_id=str(token_record.user_id),
            actor_user_id=token_record.user_id,
            metadata={"token_hash": token_hash, "action_taken": "revoked_all_user_tokens"},
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected. All sessions revoked for security.",
        )

    # Check expiration
    if token_record.expires_at < datetime.now(timezone.utc):
        token_record.revoked = True
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )

    # 3. Rotate token: revoke current token
    token_record.revoked = True

    # 4. Fetch user
    user_res = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account disabled")

    # 5. Issue new access + rotated refresh token
    user_role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
    new_access_token = create_access_token(subject=user.id, role=user_role)
    raw_refresh, new_refresh_hash, refresh_exp = generate_refresh_token()

    new_token_row = RefreshToken(
        user_id=user.id,
        token_hash=new_refresh_hash,
        expires_at=refresh_exp,
        revoked=False,
    )
    db.add(new_token_row)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    req: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    token_hash = hash_token(req.refresh_token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.user_id == current_user.id)
        .values(revoked=True)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    # Query org memberships
    org_res = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    memberships = org_res.scalars().all()

    org_list: list[OrgMembershipResponse] = []
    for m in memberships:
        await db.refresh(m, ["organization"])
        org_list.append(
            OrgMembershipResponse(
                org_id=m.org_id,
                org_name=m.organization.name if m.organization else "Unknown Org",
                role=m.role,
            )
        )

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        orgs=org_list,
    )
