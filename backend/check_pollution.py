import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.db.session import async_session_factory
from sqlalchemy import text

async def main():
    async with async_session_factory() as session:
        # Check sources
        res = await session.execute(text("SELECT id, name, slug FROM intel.sources WHERE name ILIKE '%Golden%' OR slug ILIKE '%eval%'"))
        sources = res.fetchall()
        print("Benchmark sources found:", sources)

        # Count documents
        res2 = await session.execute(text("SELECT count(*) FROM intel.documents WHERE source_name ILIKE '%Golden%' OR canonical_url ILIKE '%2601%'"))
        count = res2.scalar()
        print("Polluted documents count:", count)

        # Check real documents count
        res3 = await session.execute(text("SELECT count(*) FROM intel.documents WHERE source_name NOT ILIKE '%Golden%' AND canonical_url NOT ILIKE '%2601%'"))
        real_count = res3.scalar()
        print("Real documents count:", real_count)

if __name__ == "__main__":
    asyncio.run(main())
