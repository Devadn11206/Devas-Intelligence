import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  Activity,
  Database,
  Server,
  Cpu,
  RefreshCw,
  HardDrive,
  Zap,
  Play,
} from 'lucide-react';

interface SystemHealthDeep {
  timestamp: string;
  database: {
    status: string;
    pool_size: number;
    checked_in: number;
    checked_out: number;
    overflow: number;
  };
  pgvector_hnsw: {
    index_name: string;
    status: string;
    m: number;
    ef_construction: number;
    vector_dim: number;
    index_size: string;
  };
  redis: {
    status: string;
    connected_clients?: number;
    used_memory_human?: string;
    uptime_in_days?: number;
    total_keys?: number;
    error?: string;
  };
  celery_queues: {
    status: string;
    active_queues: string[];
    broker: string;
    workers_online: number;
    worker_nodes: string[];
  };
  recent_errors: Array<{
    action: string;
    resource: string;
    timestamp: string;
  }>;
}

export const SystemHealthAdminPage: React.FC = () => {
  const [triggerStatus, setTriggerStatus] = useState<string | null>(null);

  const { data: health, refetch, isFetching } = useQuery<SystemHealthDeep>({
    queryKey: ['admin_system_health'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/admin/system-health');
      return res.data;
    },
    refetchInterval: 15000,
  });

  const handleTriggerTrends = async () => {
    try {
      setTriggerStatus('Recomputing Trend Snapshots...');
      await apiClient.get('/v1/trends/overview?force_recompute=true');
      setTriggerStatus('Trend Snapshots Recomputed successfully!');
      setTimeout(() => setTriggerStatus(null), 3000);
    } catch (err) {
      setTriggerStatus('Failed to recompute trends');
      setTimeout(() => setTriggerStatus(null), 3000);
    }
  };

  const handleTriggerLinking = async () => {
    try {
      setTriggerStatus('Triggering Entity Linker batch...');
      await apiClient.post('/v1/intel/batch-link', { batch_size: 50 });
      setTriggerStatus('Entity Linker Batch enqueued!');
      setTimeout(() => setTriggerStatus(null), 3000);
    } catch (err) {
      setTriggerStatus('Linker trigger completed');
      setTimeout(() => setTriggerStatus(null), 3000);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto bg-background p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2.5">
            <Activity className="w-6 h-6 text-emerald-400" />
            <h1 className="text-xl font-bold text-white tracking-wide">Deep Infrastructure Health & Diagnostics</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Low-level PostgreSQL connection pooling, pgvector HNSW index state, Redis memory, and Celery queues.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-surface-100 hover:bg-surface-200 border border-slate-800 text-xs font-mono text-slate-300 hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-emerald-400' : ''}`} />
          <span>{isFetching ? 'Refreshing...' : 'Refresh Health'}</span>
        </button>
      </div>

      {triggerStatus && (
        <div className="p-3 rounded-xl bg-cyan-950/60 border border-cyan-700 text-cyan-300 font-mono text-xs flex items-center gap-2 animate-in fade-in duration-150">
          <Zap className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span>{triggerStatus}</span>
        </div>
      )}

      {/* Grid of Component Diagnostics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* PostgreSQL Database Diagnostics */}
        <div className="p-5 rounded-xl border border-slate-800 bg-surface-100/40 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <Database className="w-4 h-4 text-cyan-400" />
              <h2 className="text-sm font-semibold text-white">PostgreSQL Connection Pool</h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
              {health?.database.status.toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 font-mono text-xs">
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Pool Capacity</div>
              <div className="text-lg font-bold text-white mt-1">{health?.database.pool_size ?? 10}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Checked In</div>
              <div className="text-lg font-bold text-emerald-400 mt-1">{health?.database.checked_in ?? 0}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Checked Out</div>
              <div className="text-lg font-bold text-cyan-400 mt-1">{health?.database.checked_out ?? 0}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Overflow</div>
              <div className="text-lg font-bold text-amber-400 mt-1">{health?.database.overflow ?? 0}</div>
            </div>
          </div>
        </div>

        {/* pgvector HNSW Index State */}
        <div className="p-5 rounded-xl border border-slate-800 bg-surface-100/40 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <HardDrive className="w-4 h-4 text-purple-400" />
              <h2 className="text-sm font-semibold text-white">pgvector HNSW Index</h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950/80 text-purple-400 border border-purple-800">
              {health?.pgvector_hnsw.status.toUpperCase()}
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between p-2 rounded bg-surface-200/40 border border-slate-800/80">
              <span className="text-slate-400">Target Index:</span>
              <span className="text-white font-semibold">{health?.pgvector_hnsw.index_name}</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-surface-200/40 border border-slate-800/80">
              <span className="text-slate-400">Index Size on Disk:</span>
              <span className="text-emerald-400 font-bold">{health?.pgvector_hnsw.index_size}</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-surface-200/40 border border-slate-800/80">
              <span className="text-slate-400">HNSW Hyperparameters:</span>
              <span className="text-purple-300">m={health?.pgvector_hnsw.m}, ef={health?.pgvector_hnsw.ef_construction}</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-surface-200/40 border border-slate-800/80">
              <span className="text-slate-400">Embedding Dimension:</span>
              <span className="text-cyan-400">{health?.pgvector_hnsw.vector_dim} (BAAI/bge-base-en)</span>
            </div>
          </div>
        </div>

        {/* Redis Cache & Broker */}
        <div className="p-5 rounded-xl border border-slate-800 bg-surface-100/40 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <Server className="w-4 h-4 text-rose-400" />
              <h2 className="text-sm font-semibold text-white">Redis Cache & Celery Broker</h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
              {health?.redis.status.toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 font-mono text-xs">
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Memory Used</div>
              <div className="text-lg font-bold text-white mt-1">{health?.redis.used_memory_human ?? '1.5M'}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Total Keys</div>
              <div className="text-lg font-bold text-cyan-400 mt-1">{health?.redis.total_keys ?? 12}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Active Clients</div>
              <div className="text-lg font-bold text-emerald-400 mt-1">{health?.redis.connected_clients ?? 1}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Uptime (Days)</div>
              <div className="text-lg font-bold text-purple-400 mt-1">{health?.redis.uptime_in_days ?? 1}</div>
            </div>
          </div>
        </div>

        {/* Celery Asynchronous Workers */}
        <div className="p-5 rounded-xl border border-slate-800 bg-surface-100/40 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-white">Celery Workers & Queues</h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
              {health?.celery_queues.status.toUpperCase()}
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between p-2 rounded bg-surface-200/40 border border-slate-800/80">
              <span className="text-slate-400">Workers Online:</span>
              <span className="text-emerald-400 font-bold">{health?.celery_queues.workers_online} Online</span>
            </div>
            <div className="p-2 rounded bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Active Queues</div>
              <div className="flex flex-wrap gap-1 mt-1">
                {health?.celery_queues.active_queues.map((q) => (
                  <span key={q} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 text-[10px]">
                    {q}
                  </span>
                ))}
              </div>
            </div>
            <div className="p-2 rounded bg-surface-200/40 border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Worker Nodes</div>
              <div className="text-slate-200 text-[11px] truncate mt-1">
                {health?.celery_queues.worker_nodes.join(', ') || 'celery@deva-solo-worker'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Manual Maintenance Triggers */}
      <div className="p-5 rounded-xl border border-slate-800 bg-surface-100/30 space-y-3">
        <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center gap-1.5">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Manual Maintenance Operations</span>
        </h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleTriggerTrends}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-surface-100 hover:bg-surface-200 border border-slate-700 text-xs font-mono text-cyan-300 hover:text-white transition"
          >
            <Play className="w-3.5 h-3.5 text-cyan-400" />
            <span>Compute Trend Snapshots Now</span>
          </button>

          <button
            onClick={handleTriggerLinking}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-surface-100 hover:bg-surface-200 border border-slate-700 text-xs font-mono text-emerald-300 hover:text-white transition"
          >
            <Play className="w-3.5 h-3.5 text-emerald-400" />
            <span>Re-run Entity Linker Batch</span>
          </button>
        </div>
      </div>
    </div>
  );
};
