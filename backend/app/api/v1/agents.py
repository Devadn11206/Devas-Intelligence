import asyncio
import json
import logging
from typing import AsyncIterator, List, Literal, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.agents.fast_analyst import AnalystAnswer, CitationItem, FastAnalystService
from app.modules.agents.deep_swarm import DeepResearchSwarm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Autonomous Technical Analysts & Swarms"])


class AgentAskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: Literal["fast", "deep"] = Field(default="fast", description="Analyst mode: 'fast' cited Q&A or 'deep' research swarm")
    content_type: Optional[str] = Field(default=None, description="Optional filter: 'paper', 'repo', 'model', 'article', or None for all")
    stream: bool = Field(default=False, description="Whether to stream response via Server-Sent Events (SSE)")


class AgentAskResponse(BaseModel):
    answer: str
    citations: List[CitationItem]
    evidence_sufficient: bool
    mode: str
    latency_ms: float
    model_name: str


@router.post("/ask", response_model=AgentAskResponse)
async def ask_agent(
    payload: AgentAskRequest,
    db: AsyncSession = Depends(get_db),
):
    """Answers technical queries with grounded multi-chunk extractive synthesis and citations.
    Supports both JSON and SSE streaming formats.
    """
    if payload.mode == "deep":
        swarm = DeepResearchSwarm(db)
        result: AnalystAnswer = await swarm.execute_swarm_research(
            query=payload.query,
            content_type=payload.content_type,
        )
    else:
        analyst = FastAnalystService(db)
        result: AnalystAnswer = await analyst.answer_query(
            query=payload.query,
            mode="fast",
            content_type=payload.content_type,
        )

    if not payload.stream:
        return AgentAskResponse(
            answer=result.answer,
            citations=result.citations,
            evidence_sufficient=result.evidence_sufficient,
            mode=result.mode,
            latency_ms=result.latency_ms,
            model_name=result.model_name,
        )

    # SSE streaming response
    async def sse_event_stream() -> AsyncIterator[str]:
        # Step 1: Search event
        yield f"event: step\ndata: {json.dumps({'step': 1, 'message': 'Searching Hybrid Vector + BM25 Index...'})}\n\n"
        await asyncio.sleep(0.08)

        # Step 2: Verification event
        num_cit = len(result.citations)
        yield f"event: step\ndata: {json.dumps({'step': 2, 'message': f'Verifying [{num_cit}] Provenance Citations & CitationGuard...'})}\n\n"
        await asyncio.sleep(0.08)

        # Step 3: Stream answer chunks
        words = result.answer.split(" ")
        for i in range(0, len(words), 4):
            chunk = " ".join(words[i : i + 4]) + " "
            yield f"event: chunk\ndata: {json.dumps({'chunk': chunk})}\n\n"
            await asyncio.sleep(0.02)

        # Step 4: Final complete payload with citations
        final_payload = {
            "answer": result.answer,
            "citations": [c.model_dump() for c in result.citations],
            "evidence_sufficient": result.evidence_sufficient,
            "mode": result.mode,
            "latency_ms": result.latency_ms,
            "model_name": result.model_name,
        }
        yield f"event: done\ndata: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
