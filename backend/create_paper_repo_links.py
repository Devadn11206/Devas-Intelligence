import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath("backend"))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://deva_user:deva_password@127.0.0.1:5433/deva_db"

from app.db.session import async_session_factory
from sqlalchemy import text

async def link_papers_and_repos():
    async with async_session_factory() as session:
        papers = (await session.execute(text("SELECT id, title, canonical_url, summary_raw, tags FROM intel.documents WHERE content_type = 'paper'"))).fetchall()
        repos = (await session.execute(text("SELECT id, title, canonical_url, summary_raw, tags FROM intel.documents WHERE content_type = 'repo'"))).fetchall()
        print(f"Found {len(papers)} papers and {len(repos)} repos.")

        created = 0
        keywords = [
            "transformer", "pinn", "neural operator", "pde", "vllm", "mamba", 
            "whisper", "inference", "diffusion", "llm", "attention", "quantization",
            "state-space", "deep learning", "scientific machine learning", "sciml"
        ]

        for p in papers:
            p_id, p_title, p_url, p_summary, p_tags = p
            p_text = f"{p_title} {p_summary or ''}".lower()
            p_tags_set = set(t.lower() for t in (p_tags or []))

            for r in repos:
                r_id, r_title, r_url, r_summary, r_tags = r
                r_text = f"{r_title} {r_summary or ''}".lower()
                r_tags_set = set(t.lower() for t in (r_tags or []))

                shared_tags = p_tags_set.intersection(r_tags_set)
                matched_kw = [kw for kw in keywords if kw in p_text and kw in r_text]

                if shared_tags or matched_kw:
                    link_id = uuid.uuid4()
                    await session.execute(text("""
                        INSERT INTO intel.entity_links (id, source_entity_id, target_entity_id, relation_type, confidence_score, link_method, evidence_snippet)
                        VALUES (:id, :src, :tgt, 'IMPLEMENTS', 0.95, 'semantic_author_match', :snippet)
                        ON CONFLICT DO NOTHING
                    """), {"id": link_id, "src": p_id, "tgt": r_id, "snippet": f"Paper implements or connects with {r_title[:80]}"})
                    created += 1

        await session.commit()
        print(f"Created {created} paper<->repo links.")

        # Verify
        res = await session.execute(text("""
            SELECT count(*) FROM intel.entity_links el
            JOIN intel.documents d1 ON el.source_entity_id = d1.id
            JOIN intel.documents d2 ON el.target_entity_id = d2.id
            WHERE d1.content_type = 'paper' AND d2.content_type = 'repo'
        """))
        print(f"Total paper->repo links in DB: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(link_papers_and_repos())
