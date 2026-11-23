import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  Layers,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Search,
} from 'lucide-react';

export interface IngestionJob {
  id: string;
  source_id: string;
  source_name: string | null;
  status: 'queued' | 'running' | 'completed' | 'partial_success' | 'failed';
  triggered_by: string;
  records_fetched: number;
  records_inserted: number;
  records_updated: number;
  records_quarantined: number;
  error_summary: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface QuarantinedRecord {
  id: string;
  source_id: string;
  job_id: string;
  external_id: string | null;
  raw_payload: Record<string, any>;
  validation_error: string;
  created_at: string;
}

export const IngestionJobsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'jobs' | 'quarantine'>('jobs');
  const [filterSource, setFilterSource] = useState<string>('');

  // Jobs Query with polling
  const {
    data: jobs = [],
    isLoading: isLoadingJobs,
    refetch: refetchJobs,
  } = useQuery<IngestionJob[]>({
    queryKey: ['admin_jobs'],
    queryFn: async () => {
      const res = await apiClient.get<IngestionJob[]>('/v1/admin/ingestion-jobs?limit=100');
      return res.data;
    },
    refetchInterval: (query) => {
      // Poll every 5s if there is any active running or queued job
      const hasActive = query.state.data?.some(
        (j) => j.status === 'running' || j.status === 'queued'
      );
      return hasActive ? 5000 : false;
    },
  });

  // Quarantine Query
  const {
    data: quarantine = [],
    isLoading: isLoadingQuarantine,
    refetch: refetchQuarantine,
  } = useQuery<QuarantinedRecord[]>({
    queryKey: ['admin_quarantine'],
    queryFn: async () => {
      const res = await apiClient.get<QuarantinedRecord[]>('/v1/admin/quarantine?limit=100');
      return res.data;
    },
    enabled: activeTab === 'quarantine',
  });

  const filteredJobs = jobs.filter(
    (j) =>
      !filterSource ||
      (j.source_name && j.source_name.toLowerCase().includes(filterSource.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Layers className="w-6 h-6 text-brand-primary" />
            Ingestion Pipeline Monitor
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time execution telemetry, item yields, error logs, and dead-letter quarantine store.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => (activeTab === 'jobs' ? refetchJobs() : refetchQuarantine())}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-4">
        <button
          onClick={() => setActiveTab('jobs')}
          className={`pb-3 text-sm font-medium border-b-2 transition ${
            activeTab === 'jobs'
              ? 'border-brand-primary text-emerald-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Execution History & Status ({jobs.length})
        </button>
        <button
          onClick={() => setActiveTab('quarantine')}
          className={`pb-3 text-sm font-medium border-b-2 transition ${
            activeTab === 'quarantine'
              ? 'border-rose-500 text-rose-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Dead-Letter Quarantine
        </button>
      </div>

      {activeTab === 'jobs' ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 w-full max-w-sm">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by source name..."
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="bg-transparent text-sm text-slate-200 placeholder-slate-500 focus:outline-none w-full"
            />
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-800/60 text-xs uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Source</th>
                    <th className="py-3 px-4">Triggered By</th>
                    <th className="py-3 px-4">Fetched</th>
                    <th className="py-3 px-4">Inserted</th>
                    <th className="py-3 px-4">Updated</th>
                    <th className="py-3 px-4">Quarantined</th>
                    <th className="py-3 px-4">Started At</th>
                    <th className="py-3 px-4">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {isLoadingJobs ? (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-slate-500">
                        Loading ingestion runs...
                      </td>
                    </tr>
                  ) : filteredJobs.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-slate-500">
                        No ingestion runs recorded yet.
                      </td>
                    </tr>
                  ) : (
                    filteredJobs.map((j) => {
                      const duration =
                        j.finished_at && j.started_at
                          ? `${Math.round(
                              (new Date(j.finished_at).getTime() -
                                new Date(j.started_at).getTime()) /
                                1000
                            )}s`
                          : j.status === 'running'
                          ? 'Running...'
                          : '-';

                      return (
                        <tr key={j.id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 px-4">
                            {j.status === 'completed' && (
                              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                                <CheckCircle2 className="w-3 h-3" /> Completed
                              </span>
                            )}
                            {j.status === 'running' && (
                              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-blue-950/60 text-blue-400 border border-blue-800 animate-pulse">
                                <Clock className="w-3 h-3" /> Running
                              </span>
                            )}
                            {j.status === 'failed' && (
                              <span
                                className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-rose-950/60 text-rose-400 border border-rose-800"
                                title={j.error_summary || 'Error'}
                              >
                                <XCircle className="w-3 h-3" /> Failed
                              </span>
                            )}
                            {j.status === 'queued' && (
                              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                                <Clock className="w-3 h-3" /> Queued
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 font-medium text-slate-200">
                            {j.source_name || j.source_id.slice(0, 8)}
                          </td>
                          <td className="py-3 px-4 text-xs text-slate-400">{j.triggered_by}</td>
                          <td className="py-3 px-4 font-mono text-xs">{j.records_fetched}</td>
                          <td className="py-3 px-4 font-mono text-xs text-emerald-400 font-semibold">
                            +{j.records_inserted}
                          </td>
                          <td className="py-3 px-4 font-mono text-xs text-amber-400">
                            ~{j.records_updated}
                          </td>
                          <td className="py-3 px-4 font-mono text-xs text-rose-400">
                            {j.records_quarantined}
                          </td>
                          <td className="py-3 px-4 text-xs text-slate-400">
                            {new Date(j.started_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })}
                          </td>
                          <td className="py-3 px-4 text-xs text-slate-400">{duration}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/60 text-xs uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">External ID</th>
                  <th className="py-3 px-4">Validation Failure</th>
                  <th className="py-3 px-4">Raw Payload Preview</th>
                  <th className="py-3 px-4">Quarantined At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {isLoadingQuarantine ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-slate-500">
                      Loading quarantine store...
                    </td>
                  </tr>
                ) : quarantine.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-slate-500">
                      Clean slate: zero quarantined dead-letter records.
                    </td>
                  </tr>
                ) : (
                  quarantine.map((q) => (
                    <tr key={q.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono text-xs text-slate-400">
                        {q.external_id || 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-xs text-rose-400 font-medium">
                        {q.validation_error}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-slate-500 max-w-xs truncate">
                        {JSON.stringify(q.raw_payload)}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-400">
                        {new Date(q.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
