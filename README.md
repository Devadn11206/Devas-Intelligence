<div align="center">

# 🌌 DEVA INTELLIGENCE
### *Autonomous Technology Radar, Entity-Linked Research Graph & Citation-Guarded AI Analyst*

[![CI/CD Quality Pipeline](https://github.com/Devadn11206/Devas-Intelligence/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Devadn11206/Devas-Intelligence/actions)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 17 + pgvector](https://img.shields.io/badge/PostgreSQL-17%20%2B%20pgvector-336791?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![React 18 + Vite](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%205-61DAFB?logo=react&logoColor=black)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Design_System-Champagne_Gold_%26_Obsidian-D4AF37?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <strong>Continuous multi-stream ingestion from arXiv, GitHub, Hugging Face, and engineering RSS feeds, cross-stream paper↔code entity linking, structured 350-word RAG executive briefings, 7-day velocity hype tracking, and an autonomous citation-guarded AI Analyst.</strong>
</p>

[Key Features](#-core-architecture--features) • [Architecture](#-system-architecture) • [Quick Start](#-quick-start) • [Verification Gates](#-verification--quality-gates) • [License](#-license)

---

</div>

## 💡 Overview

**DEVA Intelligence** is an enterprise-grade AI research intelligence, cross-stream entity linking, and provenance-guarded synthesis platform. Built from the ground up for researchers, quantitative developers, and engineering executives, DEVA continuously monitors frontier science and open-source ecosystems, bridges preprints to reproducible code repositories, filters hype from empirical breakthroughs, and provides a conversational technical analyst backed by mathematical Citation-Guard guarantees.

---

## ⚡ Core Architecture & Features

### 1. Multi-Source Ingestion & Bidirectional Entity Graph
* **Unified Multi-Domain Connectors:** Ingests live preprints and updates across **arXiv** (`cs.AI`, `cs.LG`, `cs.CV`, `cs.CL`, `math-ph`, `q-bio`), **GitHub Trending & Core Repositories**, **Hugging Face Models/Tools**, and **Engineering & Biotech RSS** feeds.
* **Bidirectional Paper↔Code Entity Linking (`intel.entity_links`):** Automatically detects arXiv IDs, GitHub URLs, model repository cards, and semantic method links to associate preprints with executable implementations—visualized in real-time on our radial **Knowledge Graph Explorer**.
* **Automated 350-Word RAG Executive Briefings:** Every ingested artifact is automatically synthesized into a high-density, 4-section executive briefing (*Core Problem & Motivation*, *Technical Architecture & Methodology*, *Empirical Benchmarks & Adoption*, *Limitations & Frontier Trajectory*) with instant segmented toggling between **Source Abstract** and **AI Breakdown**.

### 2. Hybrid Retrieval Engine (`pgvector` + Full-Text + RRF Re-Ranking)
* **Domain-Aware Technical Query Expansion (`query_expander.py`):** Deterministic `< 5ms` bidirectional acronym glossary mapping across AI, Scientific Machine Learning (SciML), and Systems Engineering (`PINNs` ↔ *Physics-Informed Neural Networks*, `FNO` ↔ *Fourier Neural Operator*, `NLSE/HNLS` ↔ *Nonlinear Schrödinger Equation*, `ST-GNN`, `vLLM` ↔ *PagedAttention / KV Cache*, `MoE`, `RLHF/DPO/GRPO`, `IMU/HAR`).
* **Reciprocal Rank Fusion (RRF) & Authority Boosting (`reranker.py`):** Fuses dense `pgvector` cosine similarity ($r_{\text{vec}}$) with PostgreSQL `websearch_to_tsquery` lexical ranks ($r_{\text{lex}}$) via:
  $$\text{score}_{\text{RRF}}(d) = \frac{1}{60 + r_{\text{vec}}(d)} + \frac{1}{60 + r_{\text{lex}}(d)}$$
* **Calibrated Domain Authority Boosts:**
  * **Exact Title / Tag Match Boost (`+0.008`)** for primary keyword alignment.
  * **Verified Code-Backed Boost (`+0.004`)** prioritizing peer-reviewed work with reproducible GitHub implementations.
  * **Chunk Deduplication:** Enforces $\le 2$ distinct chunks per document to prevent single-paper monopolization and guarantee diverse cross-source citations.

### 3. Citation-Guarded AI Technical Analyst (`Fast Analyst` & `Deep Swarm`)
* **Strict Provenance Enforcement (`CITATION-GUARD`):** Every synthesized claim is strictly grounded in retrieved vector/lexical chunks with interactive inline citations (`[1]`, `[2]`, `[3]`) linked directly to an inspector drawer. Unsubstantiated claims trigger strict factual verification fail-safes.
* **Dual Reasoning Modes:**
  * **Fast Analyst:** Low-latency single-hop synthesis for instant architecture comparisons and speed-read briefings.
  * **Deep Research Swarm:** Multi-hop iterative planner that orchestrates multi-agent decomposition across papers, repositories, and engineering benchmarks.
* **Side-by-Side Comparison Matrix:** Compare up to 4 papers, repositories, or models across 6 structured dimensions, export to Markdown (`.md`), or hand off directly to the AI Analyst for architectural trade-off synthesis.

### 4. Trend Velocity Radar, Executive Dossiers & Semantic Watchlists
* **7-Day Momentum & Hype Ratio Radar (`/trends`):** Measures acceleration across technical disciplines, correlating paper momentum against repository stars/commits to flag **Verified Consensus** vs. **Hype Spikes**.
* **RLS-Isolated Executive Reports (`/reports`):** Creates persistent, multi-source dossiers strictly isolated per tenant through PostgreSQL **Row-Level Security (RLS)** with Markdown export.
* **Semantic Watchlists & Proactive Alerts (`/preferences`):** Embeds custom natural-language radar queries into 768-dimensional vector space, scanning real-time ingestion against cosine-similarity thresholds with notifications.
* **3-Minute AI Voice Digest:** Floating executive audio player capsule with TTS voice selector, speed control (`1.0x` / `1.25x` / `1.5x`), dynamic equalizer, and 5-story briefing queue.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph INGESTION ["1. Autonomous Ingestion & Entity Linking"]
        A1[arXiv API] --> S[Ingestion Engine]
        A2[GitHub API] --> S
        A3[Hugging Face API] --> S
        A4[Engineering RSS] --> S
        S --> L[Bilingual Entity Linker]
        L --> G[Cross-Stream Graph intel.entity_links]
    end

    subgraph PROCESSING ["2. Processing & Vector Embeddings"]
        S --> CH[Semantic Chunker]
        CH --> EMB[SentenceTransformers bge-base-en-v1.5]
        EMB --> PG[(PostgreSQL 17 + pgvector)]
        CH --> GIN[(GIN tsvector Full-Text)]
    end

    subgraph RETRIEVAL ["3. Hybrid Retrieval & Re-Ranking"]
        Q[User Query / Analyst] --> QE[Domain-Aware Query Expander]
        QE -->|Semantic Query| VEC[pgvector Cosine Search]
        QE -->|Lexical Query| LEX[tsvector websearch_to_tsquery]
        VEC --> RRF[Reciprocal Rank Fusion k=60]
        LEX --> RRF
        RRF --> BOOST[Exact Match + Code-Backed Boosts]
        BOOST --> DEDUP[Chunk Deduplication <= 2 per doc]
    end

    subgraph REASONING ["4. Citation-Guarded Synthesis"]
        DEDUP --> CG[CitationGuard Verifier]
        CG --> FA[Fast Analyst Single-Hop]
        CG --> DS[Deep Research Swarm Multi-Hop]
        CG --> DOS[Executive Dossier Generator]
    end

    subgraph PRESENTATION ["5. Presentation Layer"]
        FA --> UI[React 18 Obsidian Gold Workspace]
        DS --> UI
        DOS --> UI
        G --> UI
    end
```

---

## 🚀 Quick Start

### Prerequisites
* **Docker & Docker Compose** (Recommended) or **Python 3.10+**, **Node.js 20+**, **PostgreSQL 16+** with `pgvector`, and **Redis**.

### 1. Clone & Configure
```bash
git clone https://github.com/Devadn11206/Devas-Intelligence.git
cd Devas-Intelligence
cp .env.example .env
```

Configure your `.env` settings:
```ini
DATABASE_URL=postgresql+asyncpg://deva_admin:deva_secure_admin_pass@localhost:5432/deva_db
DATABASE_URL_SYNC=postgresql://deva_admin:deva_secure_admin_pass@localhost:5432/deva_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your_super_secret_jwt_key
OPENROUTER_API_KEY=your_key_here  # Optional: Zero-key deterministic fallback active by default
```

### 2. Run with Docker Compose (Recommended)
```bash
docker-compose up --build -d
```
* **Frontend Application:** [http://localhost:5173](http://localhost:5173) (or [http://localhost:8000](http://localhost:8000))
* **FastAPI Backend & Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Backend Health Check:** [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

### 3. Local Development Setup

#### Backend (FastAPI + Celery)
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head

# Start FastAPI Server:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Start Celery Worker (in a separate terminal):
celery -A app.workers.celery_app worker --pool=solo --loglevel=info -Q ingestion,processing,agents
```

#### Frontend (React + Vite + Tailwind)
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Verification & Quality Gates

DEVA strictly isolates synthetic benchmark data to `deva_test` to keep live production knowledge bases clean. Execute the verification suite:

```bash
cd backend
# Run focused hybrid re-ranker & query expander test suite
pytest tests/test_hybrid_reranker.py -v -s

# Run full Phases 0-9 verification suite
pytest tests/
```

### Verified Invariants:
* **Sub-5ms Query Expansion:** Tests bidirectional technical expansion for `PINNs`, `FNO`, `vLLM`, `MoE`, and `RLHF`.
* **RRF Rank Inversion:** Confirms exact title/tag matches (`+0.008`) and verified Paper↔Code links (`+0.004`) successfully elevate authoritative implementations.
* **Chunk Diversity Guarantee:** Validates that retrieved citations never exceed 2 chunks per document.
* **Sub-50ms Cache Retrieval:** Confirms Redis/memory cache hits respond in `< 50ms`.
* **Multi-Tenant RLS Isolation:** Validates PostgreSQL Row-Level Security across tenant watchlists, reports, and preferences.

---

## 📂 Repository Layout

```text
DEVA_Intelligence/
├── .github/workflows/          # CI/CD Quality Pipeline (Lint, Pytest, MLflow Gates, Docker)
├── backend/
│   ├── app/
│   │   ├── api/v1/             # Endpoints (auth, intel, agents, trends, reports, search, admin)
│   │   ├── core/               # Security, embeddings, LLM provider, config, metrics
│   │   ├── db/                 # PostgreSQL models (intel, tenant) & Alembic migrations
│   │   ├── modules/
│   │   │   ├── ingestion/      # arXiv, GitHub, Hugging Face, RSS adapters & linker
│   │   │   ├── retrieval/      # HybridRetrievalService, query_expander.py, reranker.py
│   │   │   ├── agents/         # FastAnalyst, DeepResearchSwarm, CitationGuard
│   │   │   └── analytics/      # Trend velocity calculator and hype ratio engine
│   │   └── workers/            # Celery async ingestion and processing tasks
│   ├── evals/                  # Golden dataset evaluations and MLflow release gates
│   └── tests/                  # Pytest verification suites (Phases 0-9)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── intel/          # IntelCard, DocumentDetailDrawer, ComparisonModal, AudioDigestBar
│   │   │   ├── layout/         # AppShell, Sidebar, SystemHealthBadge
│   │   │   └── search/         # CommandPalette (Ctrl+K)
│   │   ├── pages/              # Overview, Analyst, Trends, Reports, GraphExplorer, Preferences
│   │   └── index.css           # 6-Color Luxury Obsidian & Gold Glassmorphic styles
│   └── tailwind.config.js      # Custom theme extensions and color tokens
└── docker-compose.yml          # Container orchestration (FastAPI, Postgres+pgvector, Redis)
```

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details. Built for autonomous scientific intelligence, open-source transparency, and verified technical research.
