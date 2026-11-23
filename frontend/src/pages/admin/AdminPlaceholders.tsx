import React from 'react';
import { PhasePlaceholder } from '../../components/common/PhasePlaceholder';

export const AdminOverviewPage: React.FC = () => (
  <PhasePlaceholder
    title="Admin System Control Plane"
    moduleKey="infrastructure"
    phaseNumber={8}
    phaseName="Phase 8: Production Hardening, Evals & Monitoring"
    responsibilities={[
      'Cluster health inspection, database size tracking, and cache hit metrics.',
      'Worker queue backlog telemetry and failure dead-letter queues.',
      'API rate-limit configuration and tenant license management.',
    ]}
    dataContracts={[
      'tenant.tenant_subscriptions (tenant_id, tier, max_seats, api_quota)',
      'intel.audit_logs (id, actor, action, target, timestamp)',
    ]}
    techStack={['FastAPI Admin', 'Prometheus / Grafana', 'OpenTelemetry']}
  />
);

export const SourcesPage: React.FC = () => (
  <PhasePlaceholder
    title="Intelligence Source Management"
    moduleKey="ingestion"
    phaseNumber={1}
    phaseName="Phase 1: Multi-Source Data Ingestion Engine"
    responsibilities={[
      'CRUD registry for RSS feeds, arXiv categories, GitHub topics, and blogs.',
      'Polling frequency tuning, rate limits, and custom HTTP header configurations.',
      'Source health scoring and broken feed detection.',
    ]}
    dataContracts={[
      'intel.source_registry (id, name, url, connector_type, is_active, last_polled_at)',
    ]}
    techStack={['Celery Beat Scheduler', 'PostgreSQL', 'httpx']}
  />
);

export const IngestionJobsPage: React.FC = () => (
  <PhasePlaceholder
    title="Ingestion Job Monitor"
    moduleKey="ingestion"
    phaseNumber={1}
    phaseName="Phase 1: Multi-Source Data Ingestion Engine"
    responsibilities={[
      'Real-time tracking of active scraper runs and document ingestion pipelines.',
      'Task status inspection, item yield counts, and error tracebacks.',
      'Manual trigger and retry controls for individual ingestion batches.',
    ]}
    dataContracts={[
      'intel.ingestion_runs (id, source_id, status, items_ingested, error_log, started_at, completed_at)',
    ]}
    techStack={['Celery Flower / Redis', 'Server-Sent Events (SSE)']}
  />
);

export const AgentRunsPage: React.FC = () => (
  <PhasePlaceholder
    title="Agent Runs & LLM Cost Analytics"
    moduleKey="agents"
    phaseNumber={5}
    phaseName="Phase 5: Autonomous Intelligence Agents & Analyst"
    responsibilities={[
      'Telemetry on multi-agent execution graphs, step traces, and tool invocations.',
      'Token consumption auditing and dollar cost tracking by LLM provider.',
      'Prompt eval logging via MLflow tracking integration.',
    ]}
    dataContracts={[
      'intel.agent_runs (id, agent_type, prompt_tokens, completion_tokens, cost_usd, latency_ms)',
    ]}
    techStack={['MLflow Tracking', 'LangSmith / Tracing Client', 'OpenAICompatible API']}
  />
);

export const SystemHealthAdminPage: React.FC = () => (
  <PhasePlaceholder
    title="Deep System Health & Telemetry"
    moduleKey="infrastructure"
    phaseNumber={8}
    phaseName="Phase 8: Production Hardening, Evals & Monitoring"
    responsibilities={[
      'Detailed component telemetry for Postgres, pgvector index status, and Redis memory.',
      'Celery worker node ping status, memory consumption, and active tasks.',
      'Embedding model memory footprint and inference latency metrics.',
    ]}
    dataContracts={[
      'Diagnostics via /api/v1/health/ready and system.ping_worker task dispatch',
    ]}
    techStack={['FastAPI Health Telemetry', 'AsyncPG', 'Redis', 'Celery Inspect']}
  />
);
