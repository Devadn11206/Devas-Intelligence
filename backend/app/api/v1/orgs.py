import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.tenant import Organization, OrganizationMember, OrgMemberRole, User, UserRole
from app.api.deps import get_current_user, log_audit_event
from app.schemas.tenant import OrgCreateRequest, OrgMemberAddRequest, OrgResponse

router = APIRouter(prefix="/orgs", tags=["Organizations & Multi-Tenancy"])


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    req: OrgCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgResponse:
    # Check slug availability
    existing = await db.execute(select(Organization).where(Organization.slug == req.slug.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this slug already exists",
        )

    # 1. Create Organization
    org = Organization(
        name=req.name,
        slug=req.slug.lower(),
        owner_id=current_user.id,
    )
    db.add(org)
    await db.flush()

    # 2. Add creator as org_admin
    membership = OrganizationMember(
        org_id=org.id,
        user_id=current_user.id,
        role=OrgMemberRole.ORG_ADMIN,
    )
    db.add(membership)
    await db.flush()

    # 3. Audit Log
    await log_audit_event(
        db=db,
        action="org_created",
        resource_type="organization",
        resource_id=str(org.id),
        actor_user_id=current_user.id,
        metadata={"name": org.name, "slug": org.slug},
        ip_address=request.client.host if request.client else None,
    )

    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        owner_id=org.owner_id,
        created_at=org.created_at,
        members_count=1,
    )


@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgResponse:
    res = await db.execute(select(Organization).where(Organization.id == org_id))
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Verify user is a member or platform admin
    is_platform_admin = current_user.role in (UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)
    if not is_platform_admin:
        mem_res = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.org_id == org_id,
                OrganizationMember.user_id == current_user.id,
            )
        )
        if not mem_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this organization",
            )

    # Count members
    count_res = await db.execute(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.org_id == org_id)
    )
    members_count = count_res.scalar_one() or 1

    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        owner_id=org.owner_id,
        created_at=org.created_at,
        members_count=members_count,
    )


@router.post("/{org_id}/members", status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    org_id: uuid.UUID,
    req: OrgMemberAddRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # 1. Verify organization exists
    res = await db.execute(select(Organization).where(Organization.id == org_id))
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # 2. Check caller permission: must be org_admin or platform_admin/super_admin
    is_platform_admin = current_user.role in (UserRole.PLATFORM_ADMIN, UserRole.SUPER_ADMIN)
    if not is_platform_admin:
        admin_membership = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.org_id == org_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role == OrgMemberRole.ORG_ADMIN,
            )
        )
        if not admin_membership.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization admins or platform admins can add members",
            )

    # 3. Check target user exists
    target_res = await db.execute(select(User).where(User.id == req.user_id))
    target_user = target_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    # 4. Check not already a member
    mem_check = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == req.user_id,
        )
    )
    if mem_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization",
        )

    # 5. Add Member
    new_mem = OrganizationMember(
        org_id=org_id,
        user_id=req.user_id,
        role=req.role,
    )
    db.add(new_mem)
    await db.flush()

    # 6. Audit Log
    await log_audit_event(
        db=db,
        action="org_member_added",
        resource_type="organization",
        resource_id=str(org_id),
        actor_user_id=current_user.id,
        metadata={"added_user_id": str(req.user_id), "role": req.role.value},
        ip_address=request.client.host if request.client else None,
    )

    return {"status": "success", "message": "User added to organization successfully"}
