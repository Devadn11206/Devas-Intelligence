import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select

os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://deva_user:deva_password@localhost:5433/deva_test"

from app.main import app
from app.core.config import get_settings
from app.db.models.tenant import User, UserRole, Bookmark, UserPreference, BookmarkEntityType, DigestFrequency, AuditLog
from app.db.session import set_db_current_user_id, engine, async_session_factory

from sqlalchemy.pool import NullPool

# Non-superuser connection string to strictly test Row-Level Security enforcement
APP_USER_DATABASE_URL = "postgresql+asyncpg://deva_app_user:deva_app_password@localhost:5433/deva_test"


@pytest_asyncio.fixture
async def app_engine():
    app_eng = create_async_engine(APP_USER_DATABASE_URL, poolclass=NullPool)
    yield app_eng
    await app_eng.dispose()


@pytest_asyncio.fixture
async def app_session_factory(app_engine):
    return async_sessionmaker(bind=app_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_auth_registration_login_refresh_and_reuse_revocation(client):
    """Exit Gate 1: Test user registration, login, /auth/me, refresh token rotation, and reuse-detection revocation."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"analyst_{unique_suffix}@deva.intel"
    password = "SuperSecurePassword2026!"
    full_name = "Deva Intelligence Analyst"

    # 1. Register
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg_resp.status_code == 201, reg_resp.text
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert "refresh_token" in reg_data
    first_refresh = reg_data["refresh_token"]

    # 2. Get /auth/me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {reg_data['access_token']}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == email
    assert me_data["role"] == "user"

    # 3. Rotate Refresh Token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert refresh_resp.status_code == 200
    refreshed_data = refresh_resp.json()
    second_refresh = refreshed_data["refresh_token"]
    assert second_refresh != first_refresh

    # 4. Token Reuse Detection Attack: Attempt to use the already-revoked first_refresh token again
    reuse_attack_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert reuse_attack_resp.status_code == 401
    assert "reuse detected" in reuse_attack_resp.json()["detail"].lower()

    # 5. Verify that second_refresh was also revoked due to the detected attack
    second_attempt_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert second_attempt_resp.status_code == 401


@pytest.mark.asyncio
async def test_postgresql_row_level_security_isolation_proof(client, app_session_factory):
    """
    Exit Gate 2: PostgreSQL RLS Isolation Proof:
    Create User A and User B, insert bookmarks and preferences for both.
    Under a database session connected as non-superuser `deva_app_user` with `app.current_user_id = User A`,
    verify that zero rows belonging to User B are returned or modifiable.
    """
    suffix = uuid.uuid4().hex[:8]
    # Register User A
    resp_a = await client.post(
        "/api/v1/auth/register",
        json={"email": f"user_a_{suffix}@deva.intel", "password": "Password123!", "full_name": "User Alpha"},
    )
    assert resp_a.status_code == 201
    user_a_token = resp_a.json()["access_token"]

    me_a = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_a_token}"})
    user_a_id = uuid.UUID(me_a.json()["id"])

    # Register User B
    resp_b = await client.post(
        "/api/v1/auth/register",
        json={"email": f"user_b_{suffix}@deva.intel", "password": "Password123!", "full_name": "User Beta"},
    )
    assert resp_b.status_code == 201
    user_b_token = resp_b.json()["access_token"]

    me_b = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_b_token}"})
    user_b_id = uuid.UUID(me_b.json()["id"])

    # User A creates a bookmark
    entity_a = uuid.uuid4()
    bm_a_resp = await client.post(
        "/api/v1/users/me/bookmarks",
        headers={"Authorization": f"Bearer {user_a_token}"},
        json={"entity_type": "paper", "entity_id": str(entity_a), "notes": "User A Private Research Paper"},
    )
    assert bm_a_resp.status_code == 201

    # User B creates a bookmark
    entity_b = uuid.uuid4()
    bm_b_resp = await client.post(
        "/api/v1/users/me/bookmarks",
        headers={"Authorization": f"Bearer {user_b_token}"},
        json={"entity_type": "repo", "entity_id": str(entity_b), "notes": "User B Proprietary Repo"},
    )
    assert bm_b_resp.status_code == 201

    # DIRECT DATABASE RLS PROOF:
    # Connect as non-superuser `deva_app_user`
    async with app_session_factory() as db_session:
        # Set session context to User A
        await set_db_current_user_id(db_session, user_a_id)

        # 1. Query all bookmarks: RLS must ONLY return User A's bookmark
        res = await db_session.execute(select(Bookmark))
        bookmarks_visible = res.scalars().all()
        assert len(bookmarks_visible) == 1
        assert bookmarks_visible[0].user_id == user_a_id
        assert bookmarks_visible[0].notes == "User A Private Research Paper"

        # 2. Query all preferences: RLS must ONLY return User A's preferences
        pref_res = await db_session.execute(select(UserPreference))
        prefs_visible = pref_res.scalars().all()
        assert len(prefs_visible) == 1
        assert prefs_visible[0].user_id == user_a_id

        # 3. Attempt to update User B's bookmark while running as User A: RLS prevents this (0 rows updated)
        update_res = await db_session.execute(
            text("UPDATE tenant.bookmarks SET notes = 'Hacked' WHERE user_id = :b_id"),
            {"b_id": str(user_b_id)},
        )
        assert update_res.rowcount == 0

        # Switch context to User B: RLS must now show ONLY User B's bookmark
        await set_db_current_user_id(db_session, user_b_id)
        res_b = await db_session.execute(select(Bookmark))
        bookmarks_b = res_b.scalars().all()
        assert len(bookmarks_b) == 1
        assert bookmarks_b[0].user_id == user_b_id
        assert bookmarks_b[0].notes == "User B Proprietary Repo"


@pytest.mark.asyncio
async def test_rbac_enforcement_and_audit_logging(client, app_session_factory):
    """
    Exit Gate 3: RBAC enforcement:
    Regular `user` receives 403 Forbidden on `/api/v1/admin/users`,
    while `platform_admin` receives 200 OK and generates an entry in `tenant.audit_logs`.
    """
    suffix = uuid.uuid4().hex[:8]
    # 1. Register normal user
    reg_u = await client.post(
        "/api/v1/auth/register",
        json={"email": f"normie_{suffix}@deva.intel", "password": "Password123!", "full_name": "Normal User"},
    )
    user_token = reg_u.json()["access_token"]

    # 2. Try to access /api/v1/admin/users -> Expect 403 Forbidden
    forbidden_resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert forbidden_resp.status_code == 403

    # 3. Create platform_admin directly in DB
    admin_id = uuid.uuid4()
    admin_email = f"admin_{suffix}@deva.intel"
    async with app_session_factory() as db_session:
        from app.core.security import get_password_hash
        admin_user = User(
            id=admin_id,
            email=admin_email,
            hashed_password=get_password_hash("AdminPass2026!"),
            full_name="Platform Admin",
            role=UserRole.PLATFORM_ADMIN,
            is_active=True,
            is_verified=True,
        )
        db_session.add(admin_user)
        await db_session.commit()

    # Login as admin
    login_adm = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass2026!"},
    )
    admin_token = login_adm.json()["access_token"]

    # 4. Access /api/v1/admin/users as platform_admin -> Expect 200 OK
    admin_resp = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_resp.status_code == 200
    user_list = admin_resp.json()
    assert len(user_list) >= 2

    # 5. Access /api/v1/admin/audit-logs -> Confirm audit log recorded
    audit_resp = await client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    actions = [l["action"] for l in logs]
    assert "admin_list_users" in actions
    assert "privilege_escalation_denied" in actions


@pytest.mark.asyncio
async def test_organization_creation_and_membership_enforcement(client):
    """Exit Gate 4: Organization creation and membership authorization (SEC-004)."""
    suffix = uuid.uuid4().hex[:8]

    # Create Org Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"org_owner_{suffix}@deva.intel", "password": "Password123!", "full_name": "Org Owner"},
    )
    owner_token = owner_reg.json()["access_token"]

    # Create Member User
    member_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"org_worker_{suffix}@deva.intel", "password": "Password123!", "full_name": "Org Worker"},
    )
    member_token = member_reg.json()["access_token"]
    member_id = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {member_token}"})).json()["id"]

    # Create Unrelated User
    stranger_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": f"stranger_{suffix}@deva.intel", "password": "Password123!", "full_name": "Stranger"},
    )
    stranger_token = stranger_reg.json()["access_token"]

    # 1. Owner creates Organization
    create_org_resp = await client.post(
        "/api/v1/orgs",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "DeepMind Lab", "slug": f"deepmind-lab-{suffix}"},
    )
    assert create_org_resp.status_code == 201
    org_id = create_org_resp.json()["id"]

    # 2. Stranger tries to view the Org -> Expect 403 Forbidden
    stranger_view = await client.get(
        f"/api/v1/orgs/{org_id}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert stranger_view.status_code == 403

    # 3. Stranger tries to add members -> Expect 403 Forbidden
    stranger_add = await client.post(
        f"/api/v1/orgs/{org_id}/members",
        headers={"Authorization": f"Bearer {stranger_token}"},
        json={"user_id": member_id, "role": "org_member"},
    )
    assert stranger_add.status_code == 403

    # 4. Owner adds Member -> Expect 201 Created
    owner_add = await client.post(
        f"/api/v1/orgs/{org_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"user_id": member_id, "role": "org_member"},
    )
    assert owner_add.status_code == 201

    # 5. Member now views the Org -> Expect 200 OK
    member_view = await client.get(
        f"/api/v1/orgs/{org_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_view.status_code == 200
    assert member_view.json()["members_count"] == 2
