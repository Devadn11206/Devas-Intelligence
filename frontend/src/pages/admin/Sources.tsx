import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  Server,
  Activity,
  AlertTriangle,
  Play,
  Plus,
  RefreshCw,
  CheckCircle,
  XCircle,
} from 'lucide-react';

export interface Source {
  id: string;
  name: string;
  slug: string;
  category: string;
  adapter_key: string;
  base_url: string;
  config: Record<string, any>;
  refresh_interval_minutes: number;
  rate_limit_rpm: number;
  is_enabled: boolean;
  health_status: 'healthy' | 'degraded' | 'failing' | 'disabled';
  attribution_text: string;
  license_terms: string;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error: string | null;
  created_at: string;
}

export const SourcesPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [triggeringId, setTriggeringId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // New source form state
  const [form, setForm] = useState({
    name: '',
    slug: '',
    category: 'research',
    adapter_key: 'arxiv',
    base_url: '',
    refresh_interval_minutes: 360,
    rate_limit_rpm: 30,
    config_json: '{}',
    attribution_text: '',
    license_terms: '',
  });

  // Fetch sources
  const { data: sources = [], isLoading, refetch } = useQuery<Source[]>({
    queryKey: ['admin_sources'],
    queryFn: async () => {
      const res = await apiClient.get<Source[]>('/v1/admin/sources');
      return res.data;
    },
  });

  // Toggle Source Status
  const toggleMutation = useMutation({
    mutationFn: async ({ id, is_enabled }: { id: string; is_enabled: boolean }) => {
      await apiClient.patch(`/v1/admin/sources/${id}`, { is_enabled });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin_sources'] });
    },
  });

  // Trigger Source Ingestion
  const triggerMutation = useMutation({
    mutationFn: async (id: string) => {
      setTriggeringId(id);
      const res = await apiClient.post(`/v1/admin/sources/${id}/trigger`, {});
      return res.data;
    },
    onSuccess: (data: any) => {
      setToast({
        type: data.status === 'completed' ? 'success' : 'error',
        message: data.status === 'completed'
          ? `Sync successful! Fetched ${data.records_fetched || 0}, created/updated ${data.records_inserted || 0} records.`
          : `Sync completed with status: ${data.status}. ${data.error_summary || ''}`,
      });
    },
    onError: (err: any) => {
      setToast({
        type: 'error',
        message: err?.response?.data?.detail || err?.message || 'Sync failed. Please check network/adapter status.',
      });
    },
    onSettled: () => {
      setTriggeringId(null);
      queryClient.invalidateQueries({ queryKey: ['admin_sources'] });
      queryClient.invalidateQueries({ queryKey: ['admin_jobs'] });
      setTimeout(() => setToast(null), 6000);
    },
  });

  // Create Source
  const createMutation = useMutation({
    mutationFn: async () => {
      let parsedConfig = {};
      try {
        parsedConfig = JSON.parse(form.config_json);
      } catch (e) {
        throw new Error('Config must be valid JSON');
      }

      await apiClient.post('/v1/admin/sources', {
        name: form.name,
        slug: form.slug,
        category: form.category,
        adapter_key: form.adapter_key,
        base_url: form.base_url,
        refresh_interval_minutes: Number(form.refresh_interval_minutes),
        rate_limit_rpm: Number(form.rate_limit_rpm),
        config: parsedConfig,
        attribution_text: form.attribution_text,
        license_terms: form.license_terms,
      });
    },
    onSuccess: () => {
      setShowModal(false);
      queryClient.invalidateQueries({ queryKey: ['admin_sources'] });
    },
  });

  const totalSources = sources.length;
  const activeSources = sources.filter((s) => s.is_enabled).length;
  const failingSources = sources.filter((s) => s.health_status === 'failing').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Server className="w-6 h-6 text-brand-primary" />
            Intelligence Source Registry
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage multi-source scraping targets, adapters, polling frequencies, and health statuses.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-brand-primary hover:bg-emerald-600 text-white font-medium rounded-lg transition"
          >
            <Plus className="w-4 h-4" />
            Add Source
          </button>
        </div>
      </div>

      {/* Real-time Toast Feedback Banner */}
      {toast && (
        <div
          className={`p-4 rounded-xl border text-xs font-mono flex items-center justify-between shadow-lg animate-in fade-in duration-200 ${
            toast.type === 'success'
              ? 'bg-emerald-950/70 border-emerald-700/80 text-emerald-300'
              : 'bg-rose-950/70 border-rose-700/80 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {toast.type === 'success' ? (
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            )}
            <span>{toast.message}</span>
          </div>
          <button
            onClick={() => setToast(null)}
            className="text-slate-400 hover:text-slate-200 ml-4 font-bold"
          >
            ×
          </button>
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase text-slate-400 font-semibold tracking-wider">Total Sources</div>
            <div className="text-2xl font-bold text-slate-100 mt-1">{totalSources}</div>
          </div>
          <Server className="w-8 h-8 text-blue-500 opacity-80" />
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase text-slate-400 font-semibold tracking-wider">Active Polling</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{activeSources}</div>
          </div>
          <Activity className="w-8 h-8 text-emerald-500 opacity-80" />
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <div className="text-xs uppercase text-slate-400 font-semibold tracking-wider">Failing Sources</div>
            <div className="text-2xl font-bold text-rose-400 mt-1">{failingSources}</div>
          </div>
          <AlertTriangle className="w-8 h-8 text-rose-500 opacity-80" />
        </div>
      </div>

      {/* Sources Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800/60 text-xs uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Source Name</th>
                <th className="py-3 px-4">Adapter</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Health</th>
                <th className="py-3 px-4">Interval</th>
                <th className="py-3 px-4">Last Success</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500">
                    Loading source registry...
                  </td>
                </tr>
              ) : sources.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500">
                    No intelligence sources registered yet.
                  </td>
                </tr>
              ) : (
                sources.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-200">{s.name}</div>
                      <div className="text-xs text-slate-500">{s.slug}</div>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-emerald-400">
                      {s.adapter_key}
                    </td>
                    <td className="py-3 px-4 text-xs">
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                        {s.category}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {s.health_status === 'healthy' && (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                          <CheckCircle className="w-3 h-3" /> Healthy
                        </span>
                      )}
                      {s.health_status === 'failing' && (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-rose-950/60 text-rose-400 border border-rose-800" title={s.last_error || 'Error'}>
                          <XCircle className="w-3 h-3" /> Failing
                        </span>
                      )}
                      {s.health_status === 'degraded' && (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-800">
                          <AlertTriangle className="w-3 h-3" /> Degraded
                        </span>
                      )}
                      {s.health_status === 'disabled' && (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          Disabled
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-400">
                      {s.refresh_interval_minutes}m
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-400">
                      {s.last_success_at
                        ? new Date(s.last_success_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'Never'}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() =>
                          toggleMutation.mutate({ id: s.id, is_enabled: !s.is_enabled })
                        }
                        className={`text-xs px-2 py-1 rounded font-medium transition ${
                          s.is_enabled
                            ? 'bg-emerald-900/40 text-emerald-300 hover:bg-emerald-800/40'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        {s.is_enabled ? 'Enabled' : 'Disabled'}
                      </button>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => triggerMutation.mutate(s.id)}
                        disabled={triggeringId === s.id}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-slate-800 hover:bg-brand-primary text-slate-200 hover:text-white rounded text-xs font-medium transition disabled:opacity-50"
                        title="Trigger Ingestion Now"
                      >
                        <Play className={`w-3 h-3 ${triggeringId === s.id ? 'animate-spin' : ''}`} />
                        Sync Now
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Source Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
            <h2 className="text-xl font-bold text-slate-100">Add New Source</h2>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. arXiv SciML Papers"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-primary"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Slug</label>
                  <input
                    type="text"
                    value={form.slug}
                    onChange={(e) => setForm({ ...form, slug: e.target.value })}
                    placeholder="e.g. arxiv-sciml"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Adapter</label>
                  <select
                    value={form.adapter_key}
                    onChange={(e) => setForm({ ...form, adapter_key: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-primary"
                  >
                    <option value="arxiv">arXiv</option>
                    <option value="github">GitHub</option>
                    <option value="huggingface">Hugging Face</option>
                    <option value="semantic_scholar">Semantic Scholar</option>
                    <option value="rss">RSS / Atom</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Base URL</label>
                <input
                  type="text"
                  value={form.base_url}
                  onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                  placeholder="https://export.arxiv.org/api/query"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-primary"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Configuration (JSON)</label>
                <textarea
                  rows={3}
                  value={form.config_json}
                  onChange={(e) => setForm({ ...form, config_json: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 font-mono text-xs text-slate-200 focus:outline-none focus:border-brand-primary"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition"
              >
                Cancel
              </button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!form.name || !form.slug || !form.base_url || createMutation.isPending}
                className="px-4 py-2 bg-brand-primary hover:bg-emerald-600 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
              >
                {createMutation.isPending ? 'Saving...' : 'Register Source'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
