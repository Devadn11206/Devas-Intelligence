import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../api/client';
import {
  Zap,
  Flame,
  Activity,
  Snowflake,
  RefreshCw,
  BarChart3,
  Radar,
  ArrowUpRight,
  Radio,
  CheckCircle2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

interface TrendSnapshot {
  id: string;
  topic_tag: string;
  domain: string;
  window_date: string;
  paper_count_7d: number;
  repo_count_7d: number;
  news_count_7d: number;
  velocity_growth_pct: number;
  hype_to_substance_ratio: number;
  signal_classification: 'breakthrough_momentum' | 'hype_spike' | 'steady_adoption' | 'cooling';
}

interface TrendsOverview {
  computed_at: string;
  total_tracked_topics: number;
  signal_counts: {
    breakthrough_momentum: number;
    hype_spikes: number;
    steady_adoption: number;
    cooling: number;
  };
  breakthrough_momentum: TrendSnapshot[];
  hype_spikes: TrendSnapshot[];
  steady_adoption: TrendSnapshot[];
  cooling: TrendSnapshot[];
  all_snapshots: TrendSnapshot[];
}

// Clean mapping of arXiv & raw topic tags to human-readable names
export const formatTopicLabel = (tag: string): string => {
  const t = (tag || '').toLowerCase().trim();
  const map: Record<string, string> = {
    'cs.lg': 'Machine Learning (cs.LG)',
    'cs.cl': 'NLP & LLMs (cs.CL)',
    'cs.ai': 'Artificial Intelligence (cs.AI)',
    'cs.cv': 'Computer Vision (cs.CV)',
    'cs.ne': 'Neural & Evolutionary (cs.NE)',
    'cs.cr': 'Cryptography & Security (cs.CR)',
    'stat.ml': 'Statistical ML (stat.ML)',
    'q-bio.nc': 'Neuroscience & Biotech (q-bio.NC)',
    'q-bio.bm': 'Biomolecules (q-bio.BM)',
    'q-bio.gn': 'Genomics (q-bio.GN)',
    'eess.as': 'Audio & Speech (eess.AS)',
    'eess.sp': 'Signal Processing (eess.SP)',
    'physics.flu-dyn': 'Fluid Dynamics (physics.flu-dyn)',
    'physics.comp-ph': 'Computational Physics (physics.comp-ph)',
    'cond-mat.stat-mech': 'Statistical Mechanics (cond-mat)',
    'pinns': 'Physics-Informed NNs (PINNs)',
    'fno': 'Fourier Neural Operators (FNO)',
    'neural operators': 'Neural Operators (PDEs)',
    'partial differential equations': 'PDE Solvers (SciML)',
    'llm inference': 'LLM Inference Optimization',
    'benchmarks': 'Empirical Benchmarks',
    'diffusion models': 'Diffusion Transformers',
  };
  return map[t] || `#${tag}`;
};

export const TrendsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedSignal, setSelectedSignal] = useState<string>('all');
  const [selectedDomain, setSelectedDomain] = useState<string>('all');
  const [showToast, setShowToast] = useState(false);

  // 30s Real-time background sync
  const { data, isFetching, dataUpdatedAt } = useQuery<TrendsOverview>({
    queryKey: ['trends_overview'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/trends/overview');
      return res.data;
    },
    refetchInterval: 30000,
    staleTime: 15000,
  });

  // Recompute & Sync mutation
  const recomputeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/v1/trends/recompute');
      return res.data;
    },
    onSuccess: (freshData) => {
      queryClient.setQueryData(['trends_overview'], freshData);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    },
  });

  const domains = [
    { key: 'all', label: 'All Domains' },
    { key: 'AI & Software', label: 'AI & Software' },
    { key: 'Healthcare & Biotech', label: 'Healthcare & Biotech' },
    { key: 'Audio & Entertainment', label: 'Audio & Entertainment' },
    { key: 'Space & Physics', label: 'Space & Physics' },
  ];

  const filteredSnapshots = (data?.all_snapshots || []).filter((s) => {
    const matchesSignal = selectedSignal === 'all' || s.signal_classification === selectedSignal;
    const matchesDomain =
      selectedDomain === 'all' || s.domain.toLowerCase() === selectedDomain.toLowerCase();
    return matchesSignal && matchesDomain;
  });

  // Chart data: top 8 topics formatted cleanly
  const chartData = (data?.all_snapshots || []).slice(0, 8).map((s) => {
    const fullLabel = formatTopicLabel(s.topic_tag);
    const shortLabel = fullLabel.length > 18 ? fullLabel.slice(0, 16) + '…' : fullLabel;
    return {
      name: shortLabel,
      fullName: fullLabel,
      rawTag: s.topic_tag,
      Papers: s.paper_count_7d,
      Repos: s.repo_count_7d,
      News: s.news_count_7d,
    };
  });

  const getSignalBadge = (signal: string) => {
    switch (signal) {
      case 'breakthrough_momentum':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <Zap className="w-3 h-3 mr-1" />
            Momentum
          </span>
        );
      case 'hype_spike':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-amber-500/10 text-amber-300 border border-amber-500/30">
            <Flame className="w-3 h-3 mr-1" />
            Hype Spike
          </span>
        );
      case 'steady_adoption':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium pill-terracotta">
            <Activity className="w-3 h-3 mr-1" />
            Adoption
          </span>
        );
      case 'cooling':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-[rgba(19, 22, 29,0.6)] text-[#64748B] border border-[rgba(212, 175, 55,0.12)]">
            <Snowflake className="w-3 h-3 mr-1" />
            Cooling
          </span>
        );
      default:
        return null;
    }
  };

  const formattedTimestamp = data?.computed_at
    ? new Date(data.computed_at).toLocaleTimeString()
    : dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : 'Live';

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#10131A] border border-emerald-500/40 text-emerald-300 font-mono text-xs shadow-2xl animate-in slide-in-from-top-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Live 7-Day Trend Velocity Snapshots Recomputed!</span>
        </div>
      )}

      {/* Top Banner Header with Real-Time Telemetry & Sync */}
      <div className="glass-panel rounded-2xl p-6 relative overflow-hidden border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/90">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-[11px] font-mono text-[#D4AF37] mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] animate-ping"></span>
              <span>STAGE 3 COGNITIVE RADAR • VELOCITY ANALYTICS</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#F8FAFC] tracking-tight">
              Trend Velocity & Consensus Radar
            </h1>
            <p className="text-xs text-[#94A3B8] mt-1 max-w-2xl font-sans leading-relaxed">
              Real-time multi-source topic velocity analytics distinguishing verified technological breakthroughs from transient marketing hype spikes.
            </p>
          </div>

          {/* Telemetry Pill & Recompute Button */}
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-[#10131A] border border-[rgba(212, 175, 55,0.18)] text-[11px] font-mono text-[#EAD8D0]">
              <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>LIVE RADAR • {formattedTimestamp}</span>
            </div>

            <button
              onClick={() => recomputeMutation.mutate()}
              disabled={recomputeMutation.isPending || isFetching}
              className="px-3.5 py-1.5 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center gap-2 shadow-lg disabled:opacity-50 transition"
              title="Force full recompute across documents & entity links"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${
                  recomputeMutation.isPending || isFetching ? 'animate-spin' : ''
                }`}
              />
              <span>
                {recomputeMutation.isPending ? 'Recomputing...' : 'Recompute & Sync'}
              </span>
            </button>
          </div>
        </div>

        {/* 4 Summary Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
          <div className="p-3.5 rounded-xl bg-[rgba(19, 22, 29,0.7)] border border-emerald-500/30">
            <div className="flex items-center justify-between text-xs font-mono text-[#94A3B8]">
              <span>Breakthroughs</span>
              <Zap className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
              {data?.signal_counts?.breakthrough_momentum ?? 0}
            </div>
            <div className="text-[10px] text-[#64748B] mt-0.5">High Paper+Code Growth</div>
          </div>

          <div className="p-3.5 rounded-xl bg-[rgba(19, 22, 29,0.7)] border border-amber-500/30">
            <div className="flex items-center justify-between text-xs font-mono text-[#94A3B8]">
              <span>Hype Spikes</span>
              <Flame className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-xl font-bold font-mono text-amber-300 mt-1">
              {data?.signal_counts?.hype_spikes ?? 0}
            </div>
            <div className="text-[10px] text-[#64748B] mt-0.5">News &gt; 2.0x Substance</div>
          </div>

          <div className="p-3.5 rounded-xl bg-[rgba(19, 22, 29,0.7)] border border-[rgba(212, 175, 55,0.25)]">
            <div className="flex items-center justify-between text-xs font-mono text-[#94A3B8]">
              <span>Steady Adoption</span>
              <Activity className="w-4 h-4 text-[#F3D06B]" />
            </div>
            <div className="text-xl font-bold font-mono text-[#F3D06B] mt-1">
              {data?.signal_counts?.steady_adoption ?? 0}
            </div>
            <div className="text-[10px] text-[#64748B] mt-0.5">Sustained Velocity</div>
          </div>

          <div className="p-3.5 rounded-xl bg-[rgba(19, 22, 29,0.7)] border border-[rgba(212, 175, 55,0.12)]">
            <div className="flex items-center justify-between text-xs font-mono text-[#94A3B8]">
              <span>Cooling</span>
              <Snowflake className="w-4 h-4 text-[#64748B]" />
            </div>
            <div className="text-xl font-bold font-mono text-[#64748B] mt-1">
              {data?.signal_counts?.cooling ?? 0}
            </div>
            <div className="text-[10px] text-[#64748B] mt-0.5">Declining 7-day volume</div>
          </div>
        </div>
      </div>

      {/* Main Charts & Side-by-Side Highlight */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recharts Activity Bar Chart */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/80">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2 text-xs font-mono font-bold text-[#F8FAFC]">
              <BarChart3 className="w-4 h-4 text-[#D4AF37]" />
              <span>TOP TRENDING TOPICS (7-DAY ACTIVITY BREAKDOWN)</span>
            </div>
            <span className="text-[10px] font-mono text-[#64748B]">Click topic to drill down</span>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(212, 175, 55,0.08)" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#94A3B8', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  angle={-25}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }} />
                <Tooltip
                  formatter={(value: any, name: any) => [value, name]}
                  labelFormatter={(_label, payload) => {
                    if (payload && payload.length > 0) {
                      return payload[0].payload.fullName;
                    }
                    return _label;
                  }}
                  contentStyle={{
                    backgroundColor: 'rgba(19, 22, 29, 0.95)',
                    borderColor: 'rgba(212, 175, 55, 0.25)',
                    borderRadius: '0.75rem',
                    color: '#F8FAFC',
                    fontFamily: 'JetBrains Mono',
                    fontSize: '11px',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                  }}
                />
                <Legend
                  wrapperStyle={{
                    fontFamily: 'JetBrains Mono',
                    fontSize: '11px',
                    paddingTop: '10px',
                  }}
                />
                <Bar
                  dataKey="Papers"
                  fill="#D4AF37"
                  radius={[4, 4, 0, 0]}
                  className="cursor-pointer"
                  onClick={(entry: any) => navigate(`/dashboard?tag=${entry.rawTag}`)}
                />
                <Bar
                  dataKey="Repos"
                  fill="#34D399"
                  radius={[4, 4, 0, 0]}
                  className="cursor-pointer"
                  onClick={(entry: any) => navigate(`/dashboard?tag=${entry.rawTag}`)}
                />
                <Bar
                  dataKey="News"
                  fill="#FBBF24"
                  radius={[4, 4, 0, 0]}
                  className="cursor-pointer"
                  onClick={(entry: any) => navigate(`/dashboard?tag=${entry.rawTag}`)}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Breakthrough Momentum vs Hype Alert Callout */}
        <div className="space-y-4">
          <div
            onClick={() => {
              if (data?.breakthrough_momentum && data.breakthrough_momentum.length > 0) {
                navigate(`/dashboard?tag=${data.breakthrough_momentum[0].topic_tag}`);
              }
            }}
            className="glass-panel rounded-2xl p-5 border border-emerald-500/30 hover:border-emerald-400 hover:bg-[#1E1410] transition-all cursor-pointer group"
          >
            <div className="flex items-center justify-between text-xs font-mono font-bold text-emerald-400 mb-2">
              <span className="flex items-center space-x-1.5">
                <Zap className="w-4 h-4 text-emerald-400" />
                <span>BREAKTHROUGH MOMENTUM HIGHLIGHT</span>
              </span>
              <ArrowUpRight className="w-4 h-4 text-[#64748B] group-hover:text-emerald-400 transition" />
            </div>
            {data?.breakthrough_momentum && data.breakthrough_momentum.length > 0 ? (
              <div className="space-y-2">
                <div className="text-base font-bold text-[#F8FAFC] group-hover:text-emerald-300 transition-colors">
                  {formatTopicLabel(data.breakthrough_momentum[0].topic_tag)}
                </div>
                <div className="text-xs text-[#94A3B8] leading-relaxed">
                  Velocity growth at{' '}
                  <span className="text-emerald-400 font-mono font-bold">
                    +{data.breakthrough_momentum[0].velocity_growth_pct}%
                  </span>{' '}
                  with {data.breakthrough_momentum[0].paper_count_7d} research papers and{' '}
                  <span className="text-emerald-400 font-bold">{data.breakthrough_momentum[0].repo_count_7d} code repos</span>.
                </div>
                <span className="text-[10px] font-mono text-emerald-400 inline-block pt-1">
                  Click to explore matching intelligence feed →
                </span>
              </div>
            ) : (
              <div className="text-xs text-[#64748B] font-mono">No active breakthrough signals.</div>
            )}
          </div>

          <div
            onClick={() => {
              if (data?.hype_spikes && data.hype_spikes.length > 0) {
                navigate(`/dashboard?tag=${data.hype_spikes[0].topic_tag}`);
              }
            }}
            className="glass-panel rounded-2xl p-5 border border-amber-500/30 hover:border-amber-400 hover:bg-[#1E1410] transition-all cursor-pointer group"
          >
            <div className="flex items-center justify-between text-xs font-mono font-bold text-amber-400 mb-2">
              <span className="flex items-center space-x-1.5">
                <Flame className="w-4 h-4 text-amber-400" />
                <span>HYPE SPIKE ALERT</span>
              </span>
              <ArrowUpRight className="w-4 h-4 text-[#64748B] group-hover:text-amber-400 transition" />
            </div>
            {data?.hype_spikes && data.hype_spikes.length > 0 ? (
              <div className="space-y-2">
                <div className="text-base font-bold text-[#F8FAFC] group-hover:text-amber-300 transition-colors">
                  {formatTopicLabel(data.hype_spikes[0].topic_tag)}
                </div>
                <div className="text-xs text-[#94A3B8] leading-relaxed">
                  Hype-to-substance ratio at{' '}
                  <span className="text-amber-400 font-mono font-bold">
                    {data.hype_spikes[0].hype_to_substance_ratio.toFixed(2)}x
                  </span>
                  . News volume outpaces empirical verification ({data.hype_spikes[0].news_count_7d} news vs {data.hype_spikes[0].paper_count_7d} papers).
                </div>
                <span className="text-[10px] font-mono text-amber-400 inline-block pt-1">
                  Click to explore matching intelligence feed →
                </span>
              </div>
            ) : (
              <div className="text-xs text-[#64748B] font-mono">No active hype alerts.</div>
            )}
          </div>
        </div>
      </div>

      {/* Snapshots Table */}
      <div className="glass-panel rounded-2xl p-5 border border-[rgba(212, 175, 55,0.18)] bg-[#0D1017]/80 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-xs font-mono font-bold text-[#F8FAFC]">
            <Radar className="w-4 h-4 text-[#D4AF37]" />
            <span>ALL RECORDED TOPIC VELOCITY SNAPSHOTS</span>
          </div>

          <div className="flex items-center space-x-2">
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              className="bg-[rgba(10, 12, 16,0.8)] border border-[rgba(212, 175, 55,0.16)] rounded-lg px-2.5 py-1 text-xs text-[#F8FAFC] font-mono focus:outline-none focus:border-[#D4AF37] cursor-pointer"
            >
              {domains.map((d) => (
                <option key={d.key} value={d.key}>
                  {d.label}
                </option>
              ))}
            </select>
            <select
              value={selectedSignal}
              onChange={(e) => setSelectedSignal(e.target.value)}
              className="bg-[rgba(10, 12, 16,0.8)] border border-[rgba(212, 175, 55,0.16)] rounded-lg px-2.5 py-1 text-xs text-[#F8FAFC] font-mono focus:outline-none focus:border-[#D4AF37] cursor-pointer"
            >
              <option value="all">All Signals</option>
              <option value="breakthrough_momentum">Breakthrough Momentum</option>
              <option value="hype_spike">Hype Spike</option>
              <option value="steady_adoption">Steady Adoption</option>
              <option value="cooling">Cooling</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-[rgba(212, 175, 55,0.12)]">
          <table className="w-full text-left text-xs">
            <thead className="bg-[rgba(19, 22, 29,0.85)] border-b border-[rgba(212, 175, 55,0.12)] font-mono text-[10px] text-[#64748B] uppercase">
              <tr>
                <th className="p-3">Topic</th>
                <th className="p-3">Domain</th>
                <th className="p-3 text-right">Papers</th>
                <th className="p-3 text-right">Repos</th>
                <th className="p-3 text-right">News</th>
                <th className="p-3 text-right">Velocity</th>
                <th className="p-3 text-right">Hype Ratio</th>
                <th className="p-3 text-center">Classification</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(212, 175, 55,0.08)]">
              {filteredSnapshots.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => navigate(`/dashboard?tag=${s.topic_tag}`)}
                  className="hover:bg-[rgba(212, 175, 55,0.06)] transition font-mono cursor-pointer group"
                >
                  <td className="p-3 font-bold text-[#F8FAFC] group-hover:text-[#F3D06B] transition-colors">
                    {formatTopicLabel(s.topic_tag)}
                  </td>
                  <td className="p-3 text-[#94A3B8] font-sans">{s.domain}</td>
                  <td className="p-3 text-right text-[#F3D06B]">{s.paper_count_7d}</td>
                  <td className="p-3 text-right text-emerald-400 font-bold">{s.repo_count_7d}</td>
                  <td className="p-3 text-right text-amber-400">{s.news_count_7d}</td>
                  <td className="p-3 text-right">
                    <span className={s.velocity_growth_pct >= 0 ? 'text-emerald-400' : 'text-[#64748B]'}>
                      {s.velocity_growth_pct > 0 ? `+${s.velocity_growth_pct}%` : `${s.velocity_growth_pct}%`}
                    </span>
                  </td>
                  <td className="p-3 text-right text-[#94A3B8]">
                    {s.hype_to_substance_ratio.toFixed(2)}x
                  </td>
                  <td className="p-3 text-center">{getSignalBadge(s.signal_classification)}</td>
                  <td className="p-3 text-right text-[#D4AF37] group-hover:translate-x-1 transition-transform">
                    →
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
