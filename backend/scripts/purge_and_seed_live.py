"""Purges synthetic test records from deva_db and seeds 8 real production intelligence sources."""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from app.core.config import get_settings
from app.db.models.intel import Source, SourceCategory, SourceHealthStatus
from app.db.models.tenant import User, UserRole
from app.core.security import get_password_hash

DATABASE_URL = "postgresql+asyncpg://deva_user:deva_password@localhost:5433/deva_db"

REAL_SOURCES = [
    {
        "name": "arXiv Scientific ML & PINNs",
        "slug": "arxiv-sciml-pinns",
        "category": SourceCategory.RESEARCH,
        "adapter_key": "arxiv",
        "base_url": "https://export.arxiv.org",
        "config": {
            "search_query": 'cat:cs.LG AND (abs:"physics-informed" OR abs:"neural operator" OR abs:"PDE")',
            "max_results": 25,
            "sort_by": "submittedDate",
            "sort_order": "descending",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 20,
        "attribution_text": "arXiv.org e-Print archive",
        "license_terms": "arXiv Non-exclusive distribution license",
    },
    {
        "name": "arXiv Efficient AI & LLM Systems",
        "slug": "arxiv-efficient-llm-systems",
        "category": SourceCategory.RESEARCH,
        "adapter_key": "arxiv",
        "base_url": "https://export.arxiv.org",
        "config": {
            "search_query": 'cat:cs.CL OR cat:cs.LG AND (abs:"inference" OR abs:"quantization" OR abs:"transformer")',
            "max_results": 25,
            "sort_by": "submittedDate",
            "sort_order": "descending",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 20,
        "attribution_text": "arXiv.org e-Print archive",
        "license_terms": "arXiv Non-exclusive distribution license",
    },
    {
        "name": "GitHub Scientific ML & PINNs",
        "slug": "github-sciml-pinns",
        "category": SourceCategory.CODE,
        "adapter_key": "github",
        "base_url": "https://api.github.com",
        "config": {
            "query": "physics-informed-neural-networks OR deepxde OR neural-operator stars:>50",
            "sort": "updated",
            "order": "desc",
            "per_page": 20,
        },
        "refresh_interval_minutes": 240,
        "rate_limit_rpm": 30,
        "attribution_text": "GitHub Open Source Ecosystem",
        "license_terms": "Standard Open Source Licenses (MIT/Apache-2.0)",
    },
    {
        "name": "GitHub Open-Source LLM & Inference",
        "slug": "github-opensource-llm-inference",
        "category": SourceCategory.CODE,
        "adapter_key": "github",
        "base_url": "https://api.github.com",
        "config": {
            "query": "llm-inference OR vllm OR quantization stars:>200",
            "sort": "updated",
            "order": "desc",
            "per_page": 20,
        },
        "refresh_interval_minutes": 240,
        "rate_limit_rpm": 30,
        "attribution_text": "GitHub Open Source Ecosystem",
        "license_terms": "Standard Open Source Licenses (MIT/Apache-2.0)",
    },
    {
        "name": "Hugging Face Top Text & Multimodal Models",
        "slug": "hf-top-models",
        "category": SourceCategory.MODEL_ECOSYSTEM,
        "adapter_key": "huggingface",
        "base_url": "https://huggingface.co/api",
        "config": {
            "sort": "downloads",
            "limit": 25,
            "direction": -1,
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "Hugging Face Model Hub",
        "license_terms": "Open Model Weights Licenses",
    },
    {
        "name": "Semantic Scholar SciML Citations",
        "slug": "semantic-scholar-sciml",
        "category": SourceCategory.ACADEMIC_METADATA,
        "adapter_key": "semantic_scholar",
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "config": {
            "query": "physics informed neural networks",
            "limit": 20,
            "fields": "title,abstract,authors,year,citationCount,openAccessPdf,url,externalIds",
        },
        "refresh_interval_minutes": 720,
        "rate_limit_rpm": 15,
        "attribution_text": "Semantic Scholar Academic Graph",
        "license_terms": "Semantic Scholar Academic Terms",
    },
    {
        "name": "PyTorch Official Engineering Blog",
        "slug": "pytorch-engineering-blog",
        "category": SourceCategory.COMPANY_BLOG,
        "adapter_key": "rss",
        "base_url": "https://pytorch.org",
        "config": {
            "feed_url": "https://pytorch.org/blog/feed.xml",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "Linux Foundation / PyTorch Foundation",
        "license_terms": "PyTorch Open Blog Terms",
    },
    {
        "name": "Hugging Face Official Blog",
        "slug": "huggingface-engineering-blog",
        "category": SourceCategory.COMPANY_BLOG,
        "adapter_key": "rss",
        "base_url": "https://huggingface.co",
        "config": {
            "feed_url": "https://huggingface.co/blog/feed.xml",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "Hugging Face Official Engineering",
        "license_terms": "Hugging Face Blog Terms",
    },
    # Multi-Domain Additions: Healthcare, Music, Gaming, Science & Space
    {
        "name": "STAT News Healthcare & Biotech",
        "slug": "stat-news-biotech",
        "category": SourceCategory.TECH_NEWS,
        "adapter_key": "rss",
        "base_url": "https://www.statnews.com",
        "config": {
            "feed_url": "https://www.statnews.com/feed/",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "STAT News Healthcare Intelligence",
        "license_terms": "STAT News RSS Terms",
    },
    {
        "name": "MusicTech Audio Engineering & AI",
        "slug": "musictech-audio-ai",
        "category": SourceCategory.TECH_NEWS,
        "adapter_key": "rss",
        "base_url": "https://musictech.com",
        "config": {
            "feed_url": "https://musictech.com/feed/",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "MusicTech Magazine",
        "license_terms": "MusicTech RSS Terms",
    },
    {
        "name": "Ars Technica Gaming & Tech Culture",
        "slug": "arstechnica-gaming-tech",
        "category": SourceCategory.TECH_NEWS,
        "adapter_key": "rss",
        "base_url": "https://arstechnica.com",
        "config": {
            "feed_url": "https://feeds.arstechnica.com/arstechnica/index",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "Ars Technica Condé Nast",
        "license_terms": "Ars Technica RSS Terms",
    },
    {
        "name": "NASA Breaking Space & Aeronautics",
        "slug": "nasa-space-science",
        "category": SourceCategory.TECH_NEWS,
        "adapter_key": "rss",
        "base_url": "https://www.nasa.gov",
        "config": {
            "feed_url": "https://www.nasa.gov/news-release/feed/",
        },
        "refresh_interval_minutes": 360,
        "rate_limit_rpm": 30,
        "attribution_text": "NASA Public Domain Communications",
        "license_terms": "NASA Open Media Terms",
    },
]


async def main():
    print(f"Connecting to live database at: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Purge all test pollution from live intel schema
        print("Purging all mock/test data from intel tables...")
        await session.execute(text("""
            TRUNCATE TABLE 
                intel.entity_links,
                intel.document_chunks,
                intel.documents,
                intel.event_clusters,
                intel.ingestion_jobs,
                intel.quarantined_records,
                intel.sources
            CASCADE;
        """))
        await session.commit()
        print("✓ Intel schema tables cleared.")

        # 2. Seed 8 Real Production Sources
        print("Seeding 8 high-signal live production sources...")
        for src_data in REAL_SOURCES:
            src = Source(
                name=src_data["name"],
                slug=src_data["slug"],
                category=src_data["category"],
                adapter_key=src_data["adapter_key"],
                base_url=src_data["base_url"],
                config=src_data["config"],
                refresh_interval_minutes=src_data["refresh_interval_minutes"],
                rate_limit_rpm=src_data["rate_limit_rpm"],
                is_enabled=True,
                health_status=SourceHealthStatus.HEALTHY,
                attribution_text=src_data["attribution_text"],
                license_terms=src_data["license_terms"],
            )
            session.add(src)
        await session.commit()
        print(f"✓ {len(REAL_SOURCES)} real sources registered.")

        # 3. Create or ensure default Platform Admin
        admin_email = "admin@devaintelligence.local"
        admin_res = await session.execute(select(User).where(User.email == admin_email))
        admin = admin_res.scalars().first()

        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash("Admin@Deva2026!"),
                full_name="DEVA Platform Administrator",
                role=UserRole.PLATFORM_ADMIN,
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            await session.commit()
            print(f"✓ Created Platform Admin account: {admin_email} (password: Admin@Deva2026!)")
        else:
            admin.hashed_password = get_password_hash("Admin@Deva2026!")
            admin.role = UserRole.PLATFORM_ADMIN
            admin.is_active = True
            admin.is_verified = True
            await session.commit()
            print(f"✓ Updated Platform Admin account: {admin_email}")

    await engine.dispose()
    print("\nPurge and seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
