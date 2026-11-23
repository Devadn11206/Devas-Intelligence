import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.db.session import async_session_factory
from sqlalchemy import text

async def purge():
    async with async_session_factory() as session:
        res = await session.execute(text("SELECT id, name, slug FROM intel.sources WHERE slug = 'eval-golden-source' OR name ILIKE '%Golden%'"))
        sources = res.fetchall()
        print("Found eval sources:", sources)
        
        for src in sources:
            src_id = src[0]
            print(f"Purging source {src_id} ({src[1]})...")
            
            doc_res = await session.execute(text("SELECT id FROM intel.documents WHERE source_id = :sid"), {"sid": src_id})
            doc_ids = [r[0] for r in doc_res.fetchall()]
            print(f"Found {len(doc_ids)} documents to purge.")
            
            if doc_ids:
                # 1. Delete entity links
                await session.execute(text("DELETE FROM intel.entity_links WHERE source_entity_id = ANY(:dids) OR target_entity_id = ANY(:dids)"), {"dids": doc_ids})
                await session.commit()
                
                # 2. Delete document chunks
                await session.execute(text("DELETE FROM intel.document_chunks WHERE document_id = ANY(:dids)"), {"dids": doc_ids})
                await session.commit()
                
                # 3. Delete documents
                await session.execute(text("DELETE FROM intel.documents WHERE id = ANY(:dids)"), {"dids": doc_ids})
                await session.commit()
            
            # 4. Delete source
            await session.execute(text("DELETE FROM intel.sources WHERE id = :sid"), {"sid": src_id})
            await session.commit()
            print("Purge committed successfully.")

        res2 = await session.execute(text("SELECT count(*) FROM intel.documents"))
        print("Remaining documents in deva_db:", res2.scalar())

        res3 = await session.execute(text("SELECT title, content_type, canonical_url FROM intel.documents ORDER BY published_at DESC LIMIT 5"))
        print("\nTop 5 Real Documents in deva_db:")
        for r in res3.fetchall():
            print(f"- [{r[1]}] {r[0][:60]}... ({r[2]})")

if __name__ == "__main__":
    asyncio.run(purge())
