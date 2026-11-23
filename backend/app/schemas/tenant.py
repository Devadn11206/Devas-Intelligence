import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.db.models.tenant import UserRole, OrgMemberRole, BookmarkEntityType, DigestFrequency


# Auth Schemas
class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in: int


class OrgMembershipResponse(BaseModel):
    org_id: uuid.UUID
    org_name: str
    role: OrgMemberRole


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    orgs: List[OrgMembershipResponse] = []


# Preferences Schemas
class UserPreferencesResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    followed_topics: List[str]
    followed_technologies: List[str]
    followed_repos: List[str]
    digest_frequency: DigestFrequency
    updated_at: datetime


class UserPreferencesUpdate(BaseModel):
    followed_topics: Optional[List[str]] = None
    followed_technologies: Optional[List[str]] = None
    followed_repos: Optional[List[str]] = None
    digest_frequency: Optional[DigestFrequency] = None


# Bookmarks Schemas
class BookmarkCreate(BaseModel):
    entity_type: BookmarkEntityType
    entity_id: uuid.UUID
    notes: Optional[str] = None


class BookmarkResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    entity_type: BookmarkEntityType
    entity_id: uuid.UUID
    notes: Optional[str] = None
    created_at: datetime


# Organization Schemas
class OrgCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)


class OrgMemberAddRequest(BaseModel):
    user_id: uuid.UUID
    role: OrgMemberRole = OrgMemberRole.ORG_MEMBER


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    created_at: datetime
    members_count: int = 1


# Semantic Watchlists Schemas (Phase 7 Module 7)
class WatchlistCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    query_text: str = Field(..., min_length=3, max_length=1000)
    min_similarity: float = Field(default=0.78, ge=0.5, le=1.0)
    is_active: bool = True


class WatchlistResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    query_text: str
    min_similarity: float
    is_active: bool
    created_at: datetime
    initial_matches_count: Optional[int] = 0


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    watchlist_id: Optional[uuid.UUID] = None
    document_id: uuid.UUID
    title: str
    message: str
    is_read: bool
    created_at: datetime



# Audit Log Response
class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    metadata: dict[str, Any]
    ip_address: Optional[str]
    created_at: datetime
