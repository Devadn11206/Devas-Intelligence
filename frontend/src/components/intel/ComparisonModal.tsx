import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../api/client';
import { useComparison } from '../../lib/comparison';
import {
  X,
  Copy,
  Check,
  Columns,
  ExternalLink,
  Award,
  AlertCircle,
  Download,
  Bot,
  RefreshCw,
  GitBranch,
} from 'lucide-react';

interface ComparisonItemMeta {
  id: string;
  title: string;
  content_type: string;
  source_name: string;
  canonical_url: string;
  published_at: string;
  arxiv_id?: string;
  stars?: number;
  downloads?: number;
  linked_repos_count: number;
  linked_papers_count: number;
}

interface ComparisonRow {
  attribute: string;
  values: Record<string, string>;
}

interface ComparisonMatrixResponse {
  document_ids: string[];
  items: ComparisonItemMeta[];
  executive_verdict: string;
  comparison_rows: ComparisonRow[];
  markdown_export: string;
}

export const ComparisonModal: React.FC = () => {
  const { selectedDocs, isModalOpen, setIsModalOpen } = useComparison();
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  const docIds = selectedDocs.map((d) => d.id);

  const { data, isLoading, error, refetch, isFetching } = useQuery<ComparisonMatrixResponse>({
    queryKey: ['intel_compare', docIds.sort().join(',')],
    queryFn: async () => {
      const res = await apiClient.post('/v1/intel/compare', {
        document_ids: docIds,
      });
      return res.data;
    },
    enabled: isModalOpen && docIds.length >= 2,
    staleTime: 300000,
    retry: 1,
  });

  if (!isModalOpen) return null;

  const handleCopyMarkdown = () => {
    if (!data?.markdown_export) return;
    navigator.clipboard.writeText(data.markdown_export);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    if (!data?.markdown_export) return;
    const blob = new Blob([data.markdown_export], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `deva-comparison-${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleAskAnalyst = () => {
    if (!data?.items || data.items.length === 0) return;
    const titles = data.items.map((it) => it.title);
    const prompt = titles.length === 2
      ? `Compare the technical architectures, benchmarks, and practical trade-offs between: ${titles[0]} vs ${titles[1]}`
      : `Compare the technical architectures, benchmarks, and practical trade-offs between: ${titles.map((t, idx) => `[${idx + 1}] ${t}`).join(' vs ')}`;
    setIsModalOpen(false);
    navigate(`/analyst?q=${encodeURIComponent(prompt)}`);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-5xl glass-panel-elevated rounded-2xl border border-[rgba(212,175,55,0.25)] shadow-2xl p-6 relative flex flex-col max-h-[90vh] overflow-hidden bg-[rgba(19,22,29,0.96)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between pb-4 border-b border-[rgba(212,175,55,0.16)] shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl btn-gold-glow flex items-center justify-center text-[#08090C]">
              <Columns className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#F8FAFC]">
                Side-by-Side Comparison Matrix
              </h2>
              <p className="text-xs text-[#94A3B8] font-mono">
                Comparative technical breakdown across {selectedDocs.length} candidates
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {data?.markdown_export && (
              <>
                <button
                  onClick={handleCopyMarkdown}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-mono bg-[rgba(212,175,55,0.15)] text-[#F3D06B] border border-[rgba(212,175,55,0.25)] hover:border-[#D4AF37] hover:text-[#F8FAFC] transition"
                  title="Copy comparative matrix as Markdown"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy MD'}</span>
                </button>

                <button
                  onClick={handleDownloadMarkdown}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-mono bg-white/[0.04] text-[#94A3B8] border border-white/10 hover:text-[#F8FAFC] hover:border-[rgba(212,175,55,0.4)] transition"
                  title="Download .md file"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Download .MD</span>
                </button>
              </>
            )}

            <button
              onClick={() => setIsModalOpen(false)}
              className="p-1.5 rounded-xl text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/[0.08] transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-5">
          {isLoading || isFetching ? (
            <div className="py-20 text-center space-y-3 font-mono text-xs text-[#94A3B8]">
              <div className="w-7 h-7 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin mx-auto" />
              <div>Generating comparative matrix synthesis...</div>
            </div>
          ) : error || !data ? (
            <div className="p-6 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs font-mono flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
                <span>Failed to compile comparison matrix. The server may be busy or records temporarily unavailable.</span>
              </div>
              <button
                onClick={() => refetch()}
                className="px-3.5 py-1.5 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center gap-1.5 shrink-0 text-[#08090C]"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Analysis</span>
              </button>
            </div>
          ) : (
            <>
              {/* Executive Verdict Banner (Pattern 08 Citation/Verdict Callout) */}
              <div className="p-4 rounded-xl bg-[rgba(212,175,55,0.12)] border-l-3 border-[#D4AF37] border-y border-r border-[rgba(212,175,55,0.2)] space-y-1.5">
                <div className="flex items-center space-x-1.5 text-xs font-mono font-bold text-[#F3D06B]">
                  <Award className="w-4 h-4 text-[#D4AF37]" />
                  <span>EXECUTIVE COMPARATIVE VERDICT</span>
                </div>
                <p className="text-xs leading-relaxed text-[#F8FAFC] font-sans">
                  {data.executive_verdict}
                </p>
              </div>

              {/* Pattern 09 Glassmorphic Comparison Matrix Grid */}
              <div className="overflow-x-auto rounded-xl border border-[rgba(212,175,55,0.16)] glass-panel bg-[rgba(10,12,16,0.6)]">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-[rgba(15,18,24,0.95)] border-b border-[rgba(212,175,55,0.16)]">
                      <th className="p-3 font-mono font-semibold text-[#64748B] uppercase text-[10px] w-48 shrink-0">
                        Attribute
                      </th>
                      {data.items.map((item) => (
                        <th key={item.id} className="p-3 font-sans font-bold text-[#F8FAFC] min-w-[220px]">
                          <div className="space-y-1.5">
                            <div className="line-clamp-2 text-xs font-semibold leading-snug">
                              {item.title}
                            </div>
                            <div className="flex items-center gap-1.5 text-[10px] font-mono text-[#F3D06B] flex-wrap">
                              <span className="uppercase px-1.5 py-0.5 rounded bg-[rgba(212,175,55,0.15)] border border-[rgba(212,175,55,0.3)]">
                                {item.content_type}
                              </span>
                              <span className="text-[#64748B]">•</span>
                              <span className="text-[#94A3B8] truncate max-w-[100px]">{item.source_name}</span>
                              {item.canonical_url && (
                                <a
                                  href={item.canonical_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[#D4AF37] hover:text-[#F3D06B] inline-flex items-center gap-0.5 ml-0.5"
                                  title="Open canonical source link"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                            {item.linked_repos_count > 0 && (
                              <div className="inline-flex items-center gap-1 text-[9px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                <GitBranch className="w-2.5 h-2.5" />
                                <span>Code Linked ({item.linked_repos_count})</span>
                              </div>
                            )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(212,175,55,0.1)]">
                    {data.comparison_rows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-white/[0.03] transition">
                        <td className="p-3 font-mono text-[11px] font-semibold text-[#F3D06B] bg-[rgba(15,18,24,0.5)] align-top">
                          {row.attribute}
                        </td>
                        {data.items.map((item) => (
                          <td key={item.id} className="p-3 text-xs text-[#94A3B8] leading-relaxed align-top">
                            {row.values[item.id] || '—'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer with Actions */}
        {data && (
          <div className="pt-3 border-t border-[rgba(212,175,55,0.14)] flex items-center justify-between flex-wrap gap-2 shrink-0">
            <div className="text-[11px] font-mono text-[#64748B]">
              Compared {data.items.length} records • Grounded in DEVA Intelligence DB
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleAskAnalyst}
                className="px-3.5 py-1.5 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center gap-1.5 transition shadow-lg text-[#08090C]"
              >
                <Bot className="w-3.5 h-3.5 text-[#08090C]" />
                <span>Ask AI Analyst About Trade-Offs →</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
