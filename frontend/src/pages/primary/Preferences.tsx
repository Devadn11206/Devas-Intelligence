import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  Sliders,
  Plus,
  X,
  Check,
  Bell,
  Radar,
  Trash2,
  Sparkles,
  GitBranch,
  Cpu,
  ShieldCheck,
  Zap,
} from 'lucide-react';

interface PreferencesData {
  id: string;
  user_id: string;
  followed_topics: string[];
  followed_technologies: string[];
  followed_repos: string[];
  digest_frequency: 'daily' | 'weekly' | 'off';
  updated_at: string;
}

export const PreferencesPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [topicInput, setTopicInput] = useState('');
  const [techInput, setTechInput] = useState('');
  const [repoInput, setRepoInput] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [instantAlertFeedback, setInstantAlertFeedback] = useState<string | null>(null);

  // Semantic Watchlists State
  const [watchlistName, setWatchlistName] = useState('');
  const [watchlistQuery, setWatchlistQuery] = useState('');
  const [watchlistSim, setWatchlistSim] = useState(0.78);
  const [isCreatingWatchlist, setIsCreatingWatchlist] = useState(false);

  // Preset quick-add suggestions
  const suggestedTopics = [
    'PINNs',
    'Neural Operators',
    'Multimodal Agents',
    'Clinical AI',
    'Diffusion Models',
  ];

  const suggestedRepos = [
    'deepxde/deepxde',
    'pytorch/pytorch',
    'ggerganov/llama.cpp',
    'vllm-project/vllm',
  ];

  const suggestedTechs = [
    'vLLM',
    'DeepXDE',
    'TensorRT-LLM',
    'FlashAttention-3',
  ];

  // Fetch watchlists
  const { data: watchlists, refetch: refetchWatchlists } = useQuery({
    queryKey: ['my_watchlists'],
    queryFn: async () => {
      const resp = await apiClient.get('/v1/users/me/watchlists');
      return resp.data;
    },
  });

  const handleCreateWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!watchlistName || !watchlistQuery) return;
    try {
      setIsCreatingWatchlist(true);
      setInstantAlertFeedback(null);
      const res = await apiClient.post('/v1/users/me/watchlists', {
        name: watchlistName,
        query_text: watchlistQuery,
        min_similarity: watchlistSim,
        is_active: true,
      });
      const matches = res.data?.initial_matches_count || 0;
      setInstantAlertFeedback(
        `Watchlist activated! Scanned live index and triggered ${matches} immediate candidate alert(s).`
      );
      setTimeout(() => setInstantAlertFeedback(null), 5000);
      setWatchlistName('');
      setWatchlistQuery('');
      refetchWatchlists();
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    } catch (err) {
      console.error('Failed to create watchlist', err);
    } finally {
      setIsCreatingWatchlist(false);
    }
  };

  const handleDeleteWatchlist = async (id: string) => {
    try {
      await apiClient.delete(`/v1/users/me/watchlists/${id}`);
      refetchWatchlists();
    } catch (err) {
      console.error('Failed to delete watchlist', err);
    }
  };

  // Fetch current preferences (RLS enforced)
  const { data: prefs, isLoading } = useQuery<PreferencesData>({
    queryKey: ['user', 'preferences'],
    queryFn: async () => {
      const resp = await apiClient.get<PreferencesData>('/v1/users/me/preferences');
      return resp.data;
    },
  });

  // Mutation to update preferences
  const updateMutation = useMutation({
    mutationFn: async (updated: Partial<PreferencesData>) => {
      const resp = await apiClient.put<PreferencesData>('/v1/users/me/preferences', updated);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user', 'preferences'] });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    },
  });

  if (isLoading || !prefs) {
    return (
      <div className="flex items-center justify-center min-h-[40vh] font-mono text-xs text-[#64748B]">
        <div className="w-5 h-5 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin mr-2" />
        LOADING TENANT PREFERENCES (RLS ACTIVE)...
      </div>
    );
  }

  const addTag = (type: 'topics' | 'tech' | 'repos', value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;

    if (type === 'topics' && !prefs.followed_topics.includes(trimmed)) {
      updateMutation.mutate({ followed_topics: [...prefs.followed_topics, trimmed] });
      setTopicInput('');
    } else if (type === 'tech' && !prefs.followed_technologies.includes(trimmed)) {
      updateMutation.mutate({ followed_technologies: [...prefs.followed_technologies, trimmed] });
      setTechInput('');
    } else if (type === 'repos' && !prefs.followed_repos.includes(trimmed)) {
      updateMutation.mutate({ followed_repos: [...prefs.followed_repos, trimmed] });
      setRepoInput('');
    }
  };

  const removeTag = (type: 'topics' | 'tech' | 'repos', tag: string) => {
    if (type === 'topics') {
      updateMutation.mutate({ followed_topics: prefs.followed_topics.filter((t) => t !== tag) });
    } else if (type === 'tech') {
      updateMutation.mutate({ followed_technologies: prefs.followed_technologies.filter((t) => t !== tag) });
    } else if (type === 'repos') {
      updateMutation.mutate({ followed_repos: prefs.followed_repos.filter((t) => t !== tag) });
    }
  };

  const setDigest = (freq: 'daily' | 'weekly' | 'off') => {
    updateMutation.mutate({ digest_frequency: freq });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header Banner */}
      <div className="glass-panel rounded-2xl p-6 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/90 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-[11px] font-mono text-[#D4AF37]">
              <Sliders className="w-3.5 h-3.5" />
              <span>STAGE 3 COGNITIVE RADAR • TENANT PRIVACY PROFILE</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#F8FAFC] tracking-tight">
              Intelligence Feed Preferences & Alert Radar
            </h1>
            <p className="text-xs text-[#94A3B8] font-mono">
              Encrypted in PostgreSQL <code className="text-[#F3D06B]">tenant.user_preferences</code> with Row-Level Security
            </p>
          </div>

          {saveSuccess && (
            <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-mono animate-in fade-in">
              <Check className="w-3.5 h-3.5" />
              <span>SAVED (RLS SYNCED)</span>
            </div>
          )}
        </div>
      </div>

      {/* 2-Column Responsive Editorial Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        
        {/* LEFT COLUMN: Intelligence Feed Preferences & Digest Schedule */}
        <div className="space-y-6">
          
          {/* Followed Topics Card with Quick-Add Presets */}
          <div className="glass-panel rounded-2xl p-5 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/80 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-[rgba(212, 175, 55,0.1)]">
              <div>
                <h2 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#D4AF37]" />
                  <span>Followed Research Topics</span>
                </h2>
                <p className="text-[11px] text-[#64748B]">Drives neural recommendations across arXiv and research feeds</p>
              </div>
              <span className="text-xs font-mono text-[#F3D06B] font-semibold">{prefs.followed_topics.length} topics</span>
            </div>

            {/* Active Topics Pills */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {prefs.followed_topics.map((topic) => (
                <span
                  key={topic}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[rgba(212, 175, 55,0.25)] border border-[rgba(212, 175, 55,0.22)] text-[#F3D06B] text-xs font-mono"
                >
                  <span>{topic}</span>
                  <button
                    onClick={() => removeTag('topics', topic)}
                    className="hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            {/* Quick-Add Preset Chips */}
            <div className="pt-2">
              <div className="text-[10px] font-mono text-[#64748B] mb-1.5 uppercase">Quick-Add Suggested Topics:</div>
              <div className="flex flex-wrap gap-1.5">
                {suggestedTopics.map((sug) => {
                  const isAdded = prefs.followed_topics.includes(sug);
                  return (
                    <button
                      key={sug}
                      onClick={() => !isAdded && addTag('topics', sug)}
                      disabled={isAdded}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-md transition flex items-center gap-1 border ${
                        isAdded
                          ? 'bg-[rgba(19, 22, 29,0.4)] text-[#64748B] border-transparent opacity-60 cursor-default'
                          : 'bg-[rgba(19, 22, 29,0.7)] text-[#94A3B8] border-[rgba(212, 175, 55,0.14)] hover:border-[#D4AF37] hover:text-[#F8FAFC]'
                      }`}
                    >
                      <Plus className="w-2.5 h-2.5" />
                      <span>{sug}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Input Bar */}
            <div className="flex gap-2 pt-2">
              <input
                type="text"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('topics', topicInput))}
                placeholder="Add custom topic (e.g. PINNs, Neural Operators)..."
                className="flex-1 bg-[rgba(10, 12, 16,0.85)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3.5 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono"
              />
              <button
                onClick={() => addTag('topics', topicInput)}
                className="px-4 py-2 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center gap-1.5 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>
          </div>

          {/* Tracked GitHub Repositories with Quick-Add Presets */}
          <div className="glass-panel rounded-2xl p-5 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/80 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-[rgba(212, 175, 55,0.1)]">
              <div>
                <h2 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-emerald-400" />
                  <span>Tracked GitHub Repositories</span>
                </h2>
                <p className="text-[11px] text-[#64748B]">Watches releases, stars velocity, and codebase changes</p>
              </div>
              <span className="text-xs font-mono text-emerald-400 font-semibold">{prefs.followed_repos.length} repos</span>
            </div>

            {/* Active Repos Pills */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {prefs.followed_repos.map((repo) => (
                <span
                  key={repo}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono"
                >
                  <span>{repo}</span>
                  <button
                    onClick={() => removeTag('repos', repo)}
                    className="hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            {/* Quick-Add Preset Chips */}
            <div className="pt-2">
              <div className="text-[10px] font-mono text-[#64748B] mb-1.5 uppercase">Quick-Add Suggested Repos:</div>
              <div className="flex flex-wrap gap-1.5">
                {suggestedRepos.map((sug) => {
                  const isAdded = prefs.followed_repos.includes(sug);
                  return (
                    <button
                      key={sug}
                      onClick={() => !isAdded && addTag('repos', sug)}
                      disabled={isAdded}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-md transition flex items-center gap-1 border ${
                        isAdded
                          ? 'bg-[rgba(19, 22, 29,0.4)] text-[#64748B] border-transparent opacity-60 cursor-default'
                          : 'bg-[rgba(19, 22, 29,0.7)] text-[#94A3B8] border-[rgba(212, 175, 55,0.14)] hover:border-emerald-500 hover:text-emerald-300'
                      }`}
                    >
                      <Plus className="w-2.5 h-2.5" />
                      <span>{sug}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Input Bar */}
            <div className="flex gap-2 pt-2">
              <input
                type="text"
                value={repoInput}
                onChange={(e) => setRepoInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('repos', repoInput))}
                placeholder="Add repository (e.g. deepxde/deepxde)..."
                className="flex-1 bg-[rgba(10, 12, 16,0.85)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3.5 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono"
              />
              <button
                onClick={() => addTag('repos', repoInput)}
                className="px-4 py-2 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center gap-1.5 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>
          </div>

          {/* Tracked Frameworks Card */}
          <div className="glass-panel rounded-2xl p-5 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/80 space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-[rgba(212, 175, 55,0.1)]">
              <div>
                <h2 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-purple-400" />
                  <span>Tracked Technologies & Frameworks</span>
                </h2>
                <p className="text-[11px] text-[#64748B]">Monitors kernel velocity and hardware runtime acceleration</p>
              </div>
              <span className="text-xs font-mono text-purple-400 font-semibold">{prefs.followed_technologies.length} techs</span>
            </div>

            <div className="flex flex-wrap gap-1.5 pt-1">
              {prefs.followed_technologies.map((tech) => (
                <span
                  key={tech}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs font-mono"
                >
                  <span>{tech}</span>
                  <button
                    onClick={() => removeTag('tech', tech)}
                    className="hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>

            <div className="pt-2">
              <div className="text-[10px] font-mono text-[#64748B] mb-1.5 uppercase">Quick-Add Suggested Tech:</div>
              <div className="flex flex-wrap gap-1.5">
                {suggestedTechs.map((sug) => {
                  const isAdded = prefs.followed_technologies.includes(sug);
                  return (
                    <button
                      key={sug}
                      onClick={() => !isAdded && addTag('tech', sug)}
                      disabled={isAdded}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-md transition flex items-center gap-1 border ${
                        isAdded
                          ? 'bg-[rgba(19, 22, 29,0.4)] text-[#64748B] border-transparent opacity-60 cursor-default'
                          : 'bg-[rgba(19, 22, 29,0.7)] text-[#94A3B8] border-[rgba(212, 175, 55,0.14)] hover:border-purple-500 hover:text-purple-300'
                      }`}
                    >
                      <Plus className="w-2.5 h-2.5" />
                      <span>{sug}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <input
                type="text"
                value={techInput}
                onChange={(e) => setTechInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('tech', techInput))}
                placeholder="Add tech (e.g. vLLM, TensorRT-LLM)..."
                className="flex-1 bg-[rgba(10, 12, 16,0.85)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3.5 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono"
              />
              <button
                onClick={() => addTag('tech', techInput)}
                className="px-4 py-2 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center gap-1.5 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>
          </div>

          {/* Digest Frequency Delivery Schedule Card */}
          <div className="glass-panel rounded-2xl p-5 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/80 space-y-3.5">
            <div className="flex items-center space-x-2 text-sm font-bold text-[#F8FAFC]">
              <Bell className="w-4 h-4 text-[#D4AF37]" />
              <span>Intelligence Brief Delivery Frequency</span>
            </div>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Select how frequently Celery Beat compiles and delivers personalized intelligence dossiers to your tenant inbox.
            </p>

            <div className="grid grid-cols-3 gap-3 pt-1">
              {(['daily', 'weekly', 'off'] as const).map((freq) => (
                <button
                  key={freq}
                  onClick={() => setDigest(freq)}
                  className={`py-3 px-3 rounded-xl border text-xs font-mono uppercase tracking-wider transition-all flex flex-col items-center gap-1 ${
                    prefs.digest_frequency === freq
                      ? 'btn-gold-glow font-bold shadow-lg'
                      : 'bg-[rgba(19, 22, 29,0.5)] border-[rgba(212, 175, 55,0.14)] text-[#64748B] hover:text-[#F8FAFC] hover:border-[rgba(212, 175, 55,0.25)]'
                  }`}
                >
                  <span>{freq}</span>
                  <span className="text-[10px] text-[#94A3B8] lowercase">
                    {freq === 'daily' ? 'Morning brief' : freq === 'weekly' ? 'Sunday digest' : 'Disabled'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Semantic Watchlists & Proactive Alerts */}
        <div className="space-y-6">
          <div className="glass-panel rounded-2xl p-6 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/85 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[rgba(212, 175, 55,0.12)] pb-3">
              <div className="flex items-center space-x-2">
                <Radar className="w-5 h-5 text-[#D4AF37]" />
                <h2 className="text-base font-bold text-[#F8FAFC]">Semantic Watchlists & Proactive Alerts</h2>
              </div>
              <span className="text-[10px] font-mono text-[#F3D06B] bg-[rgba(212, 175, 55,0.3)] px-2.5 py-0.5 rounded-full border border-[rgba(212, 175, 55,0.2)]">
                RLS Isolated
              </span>
            </div>

            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Define natural-language alert queries embedded into 768-dim vector space. DEVA continuously scans incoming cross-stream literature and pushes immediate notification alerts when cosine similarity exceeds your threshold.
            </p>

            {/* Instant match notification toast banner */}
            {instantAlertFeedback && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-mono flex items-center gap-2 animate-in fade-in">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{instantAlertFeedback}</span>
              </div>
            )}

            {/* Existing Watchlists */}
            <div className="space-y-2.5">
              <div className="text-xs font-mono font-semibold text-[#64748B] uppercase">
                Active Radar Watchlists ({watchlists?.length || 0})
              </div>

              {!watchlists || watchlists.length === 0 ? (
                <div className="text-xs font-mono text-[#64748B] py-8 text-center border border-dashed border-[rgba(212, 175, 55,0.15)] rounded-xl space-y-1">
                  <Radar className="w-6 h-6 mx-auto opacity-40 text-[#D4AF37]" />
                  <div>No active semantic watchlists. Create your first radar query below.</div>
                </div>
              ) : (
                watchlists.map((wl: any) => (
                  <div
                    key={wl.id}
                    className="p-3.5 rounded-xl bg-[rgba(19, 22, 29,0.7)] border border-[rgba(212, 175, 55,0.14)] flex items-center justify-between hover:border-[rgba(212, 175, 55,0.3)] transition shadow-sm"
                  >
                    <div className="space-y-1 max-w-[80%]">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-[#F8FAFC]">{wl.name}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[rgba(212, 175, 55,0.35)] text-[#F3D06B] border border-[rgba(212, 175, 55,0.2)]">
                          {(wl.min_similarity * 100).toFixed(0)}% threshold
                        </span>
                      </div>
                      <p className="text-xs text-[#94A3B8] font-mono leading-relaxed line-clamp-2">
                        "{wl.query_text}"
                      </p>
                    </div>

                    <button
                      onClick={() => handleDeleteWatchlist(wl.id)}
                      className="p-2 text-[#64748B] hover:text-rose-400 hover:bg-[rgba(212, 175, 55,0.08)] rounded-lg transition"
                      title="Delete watchlist"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Watchlist Creation Form */}
            <form onSubmit={handleCreateWatchlist} className="space-y-3.5 pt-4 border-t border-[rgba(212, 175, 55,0.12)]">
              <div className="text-xs font-bold text-[#F8FAFC] uppercase font-mono flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-[#D4AF37]" />
                <span>Create New Watchlist Radar</span>
              </div>

              <div className="space-y-2.5">
                <input
                  type="text"
                  value={watchlistName}
                  onChange={(e) => setWatchlistName(e.target.value)}
                  placeholder="Watchlist Name (e.g. Physics-Informed Neural Networks, Quantum Fluid Dynamics)..."
                  required
                  className="w-full bg-[rgba(10, 12, 16,0.85)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3.5 py-2.5 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono"
                />

                <div className="flex items-center justify-between bg-[rgba(19, 22, 29,0.7)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3.5 py-2 gap-3">
                  <span className="text-xs text-[#94A3B8] font-mono shrink-0">
                    Min Similarity: <strong>{(watchlistSim * 100).toFixed(0)}%</strong>
                  </span>
                  <input
                    type="range"
                    min="0.50"
                    max="0.95"
                    step="0.02"
                    value={watchlistSim}
                    onChange={(e) => setWatchlistSim(parseFloat(e.target.value))}
                    className="w-full accent-[#D4AF37] cursor-pointer"
                  />
                </div>

                <textarea
                  rows={3}
                  value={watchlistQuery}
                  onChange={(e) => setWatchlistQuery(e.target.value)}
                  placeholder="Natural language alert query (e.g. 'Physics-informed neural networks enforcing Navier-Stokes boundary equations on GPU')..."
                  required
                  className="w-full bg-[rgba(10, 12, 16,0.85)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3.5 py-2.5 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono resize-none"
                />

                <button
                  type="submit"
                  disabled={isCreatingWatchlist}
                  className="w-full py-2.5 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-lg"
                >
                  {isCreatingWatchlist ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Scanning Live Index & Embedding Query...</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-3.5 h-3.5" />
                      <span>Activate Radar & Scan Recent Chunks</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
