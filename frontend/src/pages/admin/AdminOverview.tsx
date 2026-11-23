import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient } from '../../api/client';
import {
  ShieldCheck,
  Users,
  Database,
  Layers,
  Share2,
  RefreshCw,
  Activity,
  Clock,
  ArrowRight,
} from 'lucide-react';

interface AdminOverviewData {
  timestamp: string;
  total_users: number;
  active_organizations: number;
  sources_summary: {
    healthy: number;
    degraded: number;
    failing: number;
    disabled: number;
    total: number;
  };
  total_documents: number;
  documents_by_content_type: Record<string, number>;
  total_chunks: number;
  total_entity_links: number;
  total_event_clusters: number;
  recent_ingestion_jobs_24h: number;
  recent_agent_runs_24h: number;
}

interface AuditLogItem {
  id: string;
  actor_user_id: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  metadata: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export const AdminOverviewPage: React.FC = () => {
  const { data: overview, refetch, isFetching } = useQuery<AdminOverviewData>({
    queryKey: ['admin_overview'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/admin/overview');
      return res.data;
    },
    refetchInterval: 30000,
  });

  const { data: auditLogs } = useQuery<AuditLogItem[]>({
    queryKey: ['admin_audit_logs'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/admin/audit-logs');
      return res.data;
    },
    refetchInterval: 30000,
  });

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto bg-transparent p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[rgba(212, 175, 55,0.12)]">
        <div>
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="w-6 h-6 text-[#D4AF37]" />
            <h1 className="text-xl font-bold text-[#F8FAFC] tracking-wide">Admin System Control Plane</h1>
          </div>
          <p className="text-xs text-[#94A3B8] mt-1 font-mono">
            Platform observability, database metrics, source health telemetry, and tenant security audit logs.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[rgba(19, 22, 29,0.7)] hover:bg-[rgba(19, 22, 29,0.9)] border border-[rgba(212, 175, 55,0.16)] text-xs font-mono text-[#94A3B8] hover:text-[#F8FAFC] transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-[#D4AF37]' : ''}`} />
          <span>{isFetching ? 'Refreshing...' : 'Refresh KPIs'}</span>
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Documents */}
        <div className="p-4 rounded-xl border border-[rgba(212, 175, 55,0.14)] glass-card space-y-2">
          <div className="flex items-center justify-between text-xs font-mono uppercase text-[#64748B]">
            <span>Total Documents</span>
            <Database className="w-4 h-4 text-[#D4AF37]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#F8FAFC]">
            {overview?.total_documents.toLocaleString() ?? '...'}
          </div>
          <div className="text-[11px] font-mono text-[#94A3B8] flex items-center justify-between pt-1 border-t border-[rgba(212, 175, 55,0.1)]">
            <span>Chunks: {overview?.total_chunks.toLocaleString() ?? '...'}</span>
            <span className="text-[#F3D06B]">Vectors 768d</span>
          </div>
        </div>

        {/* Knowledge Graph Edges */}
        <div className="p-4 rounded-xl border border-[rgba(212, 175, 55,0.14)] glass-card space-y-2">
          <div className="flex items-center justify-between text-xs font-mono uppercase text-[#64748B]">
            <span>Knowledge Graph</span>
            <Share2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            {overview?.total_entity_links.toLocaleString() ?? '...'}
          </div>
          <div className="text-[11px] font-mono text-[#94A3B8] flex items-center justify-between pt-1 border-t border-[rgba(212, 175, 55,0.1)]">
            <span>Clusters: {overview?.total_event_clusters.toLocaleString() ?? '...'}</span>
            <span className="text-emerald-400">Relational Links</span>
          </div>
        </div>

        {/* Source Health */}
        <div className="p-4 rounded-xl border border-[rgba(212, 175, 55,0.14)] glass-card space-y-2">
          <div className="flex items-center justify-between text-xs font-mono uppercase text-[#64748B]">
            <span>Sources Monitored</span>
            <Activity className="w-4 h-4 text-[#F3D06B]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#F3D06B]">
            {overview?.sources_summary.total ?? '...'}
          </div>
          <div className="text-[11px] font-mono text-[#94A3B8] flex items-center justify-between pt-1 border-t border-[rgba(212, 175, 55,0.1)]">
            <span className="text-emerald-400">Healthy: {overview?.sources_summary.healthy ?? 0}</span>
            <span className="text-rose-400">Failing: {overview?.sources_summary.failing ?? 0}</span>
          </div>
        </div>

        {/* Platform Tenants */}
        <div className="p-4 rounded-xl border border-[rgba(212, 175, 55,0.14)] glass-card space-y-2">
          <div className="flex items-center justify-between text-xs font-mono uppercase text-slate-400">
            <span>Tenants & Users</span>
            <Users className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {overview?.total_users ?? '...'}
          </div>
          <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between pt-1 border-t border-slate-800">
            <span>Orgs: {overview?.active_organizations ?? 0}</span>
            <span className="text-amber-400">RLS Enforced</span>
          </div>
        </div>
      </div>

      {/* Content Breakdown & Navigation Shortcuts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Content Type Breakdown */}
        <div className="p-5 rounded-xl border border-slate-800 bg-surface-100/30 space-y-3 lg:col-span-1">
          <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Documents by Content Type</span>
          </h2>
          <div className="space-y-2 pt-1 font-mono text-xs">
            {overview && Object.entries(overview.documents_by_content_type).map(([ctype, count]) => (
              <div key={ctype} className="flex items-center justify-between p-2 rounded bg-surface-200/40 border border-slate-800/80">
                <span className="uppercase text-slate-300 font-semibold">{ctype}</span>
                <span className="text-cyan-400 font-bold">{count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Admin Navigation Cards */}
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link
            to="/admin/sources"
            className="p-5 rounded-xl border border-slate-800 bg-surface-100/30 hover:border-cyan-500/50 transition group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-semibold text-cyan-400 uppercase">Ingestion Engine</span>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-1 transition" />
              </div>
              <h3 className="text-sm font-semibold text-white">Source Registry & Live Triggers</h3>
              <p className="text-xs text-slate-400 mt-1">Manage arXiv, GitHub, HF, STAT, MusicTech & Semantic Scholar feeds.</p>
            </div>
            <span className="text-[10px] font-mono text-slate-500 mt-4">24h Ingestion Jobs: {overview?.recent_ingestion_jobs_24h ?? 0}</span>
          </Link>

          <Link
            to="/admin/agents"
            className="p-5 rounded-xl border border-slate-800 bg-surface-100/30 hover:border-purple-500/50 transition group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-semibold text-purple-400 uppercase">Multi-Agent Swarm</span>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 group-hover:translate-x-1 transition" />
              </div>
              <h3 className="text-sm font-semibold text-white">Agent Runs & Node Traces</h3>
              <p className="text-xs text-slate-400 mt-1">Inspect execution traces, token consumption, and analyst runs.</p>
            </div>
            <span className="text-[10px] font-mono text-slate-500 mt-4">24h Agent Runs: {overview?.recent_agent_runs_24h ?? 0}</span>
          </Link>

          <Link
            to="/admin/health"
            className="p-5 rounded-xl border border-slate-800 bg-surface-100/30 hover:border-emerald-500/50 transition group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-semibold text-emerald-400 uppercase">Infrastructure</span>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition" />
              </div>
              <h3 className="text-sm font-semibold text-white">Deep System Telemetry</h3>
              <p className="text-xs text-slate-400 mt-1">Postgres pool, pgvector HNSW index, Redis memory, and Celery queues.</p>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 mt-4">Database: PostgreSQL 5433</span>
          </Link>

          <Link
            to="/admin/ingestion-jobs"
            className="p-5 rounded-xl border border-slate-800 bg-surface-100/30 hover:border-amber-500/50 transition group flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-semibold text-amber-400 uppercase">Background Workers</span>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-1 transition" />
              </div>
              <h3 className="text-sm font-semibold text-white">Ingestion Job Monitor</h3>
              <p className="text-xs text-slate-400 mt-1">Inspect live scraper tasks, fetched records, and quarantine logs.</p>
            </div>
            <span className="text-[10px] font-mono text-slate-500 mt-4">Queue: ingestion, processing</span>
          </Link>
        </div>
      </div>

      {/* Security Audit Logs Feed */}
      <div className="p-5 rounded-xl border border-slate-800 bg-surface-100/30 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase font-mono text-slate-300">
            <Clock className="w-4 h-4 text-cyan-400" />
            <span>Platform Security Audit Log Feed</span>
          </div>
          <span className="text-xs font-mono text-slate-500">Last 10 Actions</span>
        </div>

        <div className="space-y-1.5 font-mono text-xs">
          {(!auditLogs || auditLogs.length === 0) ? (
            <div className="text-center py-4 text-slate-500">No recent audit events logged.</div>
          ) : (
            auditLogs.slice(0, 8).map((log) => (
              <div key={log.id} className="flex items-center justify-between p-2.5 rounded bg-surface-200/30 border border-slate-800/60">
                <div className="flex items-center space-x-3">
                  <span className="text-cyan-400 font-semibold">{log.action}</span>
                  <span className="text-slate-400 text-[11px]">[{log.resource_type}]</span>
                  {log.ip_address && <span className="text-slate-500 text-[10px] hidden sm:inline">{log.ip_address}</span>}
                </div>
                <span className="text-[10px] text-slate-500">
                  {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
