import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.db.models.tenant import BriefingType


class ReportGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=500)
    briefing_type: BriefingType = Field(default=BriefingType.DEEP_DOSSIER)
    domain: Optional[str] = Field(default=None, max_length=100)


class ReportResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    briefing_type: BriefingType
    domain: Optional[str]
    executive_summary: str
    content_markdown: str
    source_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
