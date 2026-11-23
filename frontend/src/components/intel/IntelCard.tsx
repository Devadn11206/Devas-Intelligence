import React, { useState } from 'react';
import {
  FileText,
  Code2,
  Cpu,
  Newspaper,
  Wrench,
  Bookmark,
  ChevronRight,
  Sparkles,
  CheckCircle,
  Columns,
  GitBranch,
} from 'lucide-react';
import { apiClient } from '../../api/client';
import { useComparison } from '../../lib/comparison';

export interface CorroboratingSource {
  document_id: string;
  source_name: string;
  canonical_url: string;
  published_at: string;
}

export interface IntelFeedCard {
  id: string;
  event_cluster_id: string | null;
  primary_document_id: string;
  title: string;
  content_type: 'paper' | 'repo' | 'model' | 'article' | 'tool';
  summary_raw: string;
  summary_ai: Record<string, any> | null;
  authors: string[];
  tags: string[];
  metadata: Record<string, any>;
  published_at: string;
  source_name: string;
  source_category: string;
  canonical_url: string;
  document_count: number;
  corroborating_sources: CorroboratingSource[];
  consensus_status?: string;
  consensus_summary?: string;
  linked_repos_count?: number;
  linked_papers_count?: number;
}

interface IntelCardProps {
  card: IntelFeedCard;
  onOpenDetail: (documentId: string) => void;
}

export const IntelCard: React.FC<IntelCardProps> = ({ card, onOpenDetail }) => {
  const [activeTab, setActiveTab] = useState<'raw' | 'ai'>('raw');
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [isBookmarking, setIsBookmarking] = useState(false);
  const { toggleSelectDoc, isSelected } = useComparison();

  const isDocSelected = isSelected(card.primary_document_id);

  const handleBookmark = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isBookmarked) return;

    try {
      setIsBookmarking(true);
      await apiClient.post('/v1/users/me/bookmarks', {
        entity_type: card.content_type,
        entity_id: card.primary_document_id,
        notes: `Saved from ${card.source_name}`,
      });
      setIsBookmarked(true);
    } catch (err) {
      console.error('Failed to bookmark', err);
    } finally {
      setIsBookmarking(false);
    }
  };

  const getBadge = () => {
    switch (card.content_type) {
      case 'paper':
        return {
          icon: <FileText className="w-3 h-3 text-[#60A5FA]" />,
          label: 'PAPER',
          bg: 'bg-blue-950/40 text-[#60A5FA] border-blue-500/30',
        };
      case 'repo':
        return {
          icon: <Code2 className="w-3 h-3 text-emerald-400" />,
          label: 'CODE REPO',
          bg: 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30',
        };
      case 'model':
        return {
          icon: <Cpu className="w-3 h-3 text-[#F3D06B]" />,
          label: 'AI MODEL',
          bg: 'bg-[rgba(212,175,55,0.15)] text-[#F3D06B] border-[rgba(212,175,55,0.3)]',
        };
      case 'article':
        return {
          icon: <Newspaper className="w-3 h-3 text-[#D4AF37]" />,
          label: 'NEWS / BLOG',
          bg: 'bg-[rgba(212,175,55,0.12)] text-[#F3D06B] border-[rgba(212,175,55,0.25)]',
        };
      default:
        return {
          icon: <Wrench className="w-3 h-3 text-[#94A3B8]" />,
          label: 'TOOL',
          bg: 'bg-slate-800/40 text-[#94A3B8] border-slate-700/40',
        };
    }
  };

  const badge = getBadge();

  const formatRelativeTime = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      if (diffDays <= 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 30) return `${diffDays}d ago`;
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  // Deduplicate tags cleanly
  const uniqueTags = (() => {
    const seen = new Set<string>();
    const tags: string[] = [];
    for (const tag of card.tags || []) {
      const lower = tag.toLowerCase().trim();
      if (lower && !seen.has(lower)) {
        seen.add(lower);
        tags.push(tag);
      }
    }
    return tags.slice(0, 4);
  })();

  return (
    <article
      onClick={() => onOpenDetail(card.primary_document_id)}
      className="glass-card rounded-2xl p-5 cursor-pointer relative group transition-all duration-200 border border-[rgba(212,175,55,0.15)] hover:border-[rgba(229,193,88,0.4)] bg-[rgba(19,22,29,0.78)] shadow-lg hover:shadow-2xl hover:-translate-y-0.5"
    >
      <div className="flex flex-col md:flex-row gap-5 items-stretch">
        {/* ── LEFT ZONE: Content & Editorial Summary ──────────────────── */}
        <div className="flex-1 min-w-0 flex flex-col justify-between space-y-3">
          {/* Header metadata pill strip */}
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[10px] font-mono font-semibold tracking-wider ${badge.bg}`}
            >
              {badge.icon}
              <span>{badge.label}</span>
            </span>

            <span className="text-[11px] font-mono text-[#94A3B8] truncate max-w-[220px]">
              {card.source_name}
            </span>

            <span className="text-[#64748B]">•</span>
            <span className="text-[11px] font-mono text-[#64748B]">
              {formatRelativeTime(card.published_at)}
            </span>

            {/* Verified Consensus Badge */}
            {card.consensus_status === 'verified_consensus' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[10px] font-mono text-emerald-400 font-medium">
                <CheckCircle className="w-3 h-3" />
                <span>Verified Consensus</span>
              </span>
            )}
          </div>

          {/* Title & Authors */}
          <div className="space-y-1.5">
            <h2 className="text-base sm:text-[17px] font-bold text-[#F8FAFC] tracking-tight leading-snug group-hover:text-[#F3D06B] transition-colors">
              {card.title}
            </h2>

            {card.authors && card.authors.length > 0 && (
              <div className="text-[11px] font-mono text-[#64748B] truncate">
                By {card.authors.slice(0, 3).join(', ')}
                {card.authors.length > 3 ? ` +${card.authors.length - 3} others` : ''}
              </div>
            )}
          </div>

          {/* Pattern 07 Segmented Switcher: Source Abstract vs AI Breakdown */}
          <div className="space-y-2">
            <div className="inline-flex items-center p-0.5 rounded-lg bg-[rgba(10,12,16,0.7)] border border-[rgba(212,175,55,0.12)]">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveTab('raw');
                }}
                className={`text-[10px] font-mono px-2.5 py-1 rounded-md transition ${
                  activeTab === 'raw'
                    ? 'bg-[rgba(212,175,55,0.18)] text-[#F3D06B] font-semibold border border-[rgba(212,175,55,0.25)] shadow-sm'
                    : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                Source Abstract
              </button>
              {card.summary_ai && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveTab('ai');
                  }}
                  className={`text-[10px] font-mono px-2.5 py-1 rounded-md flex items-center gap-1 transition ${
                    activeTab === 'ai'
                      ? 'bg-[rgba(212,175,55,0.18)] text-[#F3D06B] font-semibold border border-[rgba(212,175,55,0.25)] shadow-sm'
                      : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                  }`}
                >
                  <Sparkles className="w-2.5 h-2.5 text-[#D4AF37]" />
                  <span>AI Breakdown</span>
                </button>
              )}
            </div>

            {/* Prose excerpt */}
            <p className="text-xs text-[#94A3B8] leading-relaxed font-sans line-clamp-2">
              {activeTab === 'raw'
                ? card.summary_raw || 'No raw abstract available for this record.'
                : card.summary_ai?.problem_statement ||
                  card.summary_ai?.key_findings ||
                  card.summary_raw}
            </p>
          </div>

          {/* Deduplicated Tag Chips */}
          <div className="flex items-center gap-1.5 flex-wrap pt-1">
            {uniqueTags.map((tag) => (
              <span
                key={tag.toLowerCase()}
                className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[rgba(15,18,24,0.7)] text-[#94A3B8] border border-[rgba(212,175,55,0.1)] group-hover:border-[rgba(212,175,55,0.2)]"
              >
                #{tag}
              </span>
            ))}
          </div>
        </div>

        {/* ── RIGHT ZONE: Telemetry Rail & Actions (Pattern 02) ────────── */}
        <div className="md:w-44 shrink-0 flex flex-col justify-between pt-3 md:pt-0 md:pl-5 border-t md:border-t-0 md:border-l border-[rgba(212,175,55,0.12)] space-y-3">
          {/* Linked Code/Paper Entity Badges */}
          <div className="space-y-1.5">
            {Boolean(card.linked_repos_count && card.linked_repos_count > 0) && (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-[10px] font-mono text-emerald-300 font-semibold">
                <GitBranch className="w-3 h-3 text-emerald-400 shrink-0" />
                <span>Code Linked ({card.linked_repos_count})</span>
              </div>
            )}
            {Boolean(card.linked_papers_count && card.linked_papers_count > 0) && (
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-blue-950/40 border border-blue-500/30 text-[10px] font-mono text-[#60A5FA] font-semibold">
                <FileText className="w-3 h-3 text-[#60A5FA] shrink-0" />
                <span>Paper Linked ({card.linked_papers_count})</span>
              </div>
            )}
            {!card.linked_repos_count && !card.linked_papers_count && (
              <div className="text-[10px] font-mono text-[#64748B]">
                Direct Signal
              </div>
            )}
          </div>

          {/* Control Actions: Compare & Bookmark */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleSelectDoc({
                  id: card.primary_document_id,
                  title: card.title,
                  content_type: card.content_type,
                });
              }}
              className={`flex-1 py-1.5 px-2 rounded-lg border text-xs font-mono transition flex items-center justify-center gap-1 ${
                isDocSelected
                  ? 'btn-gold-glow'
                  : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/10 text-[#94A3B8] hover:text-[#F8FAFC] hover:border-[rgba(212,175,55,0.3)]'
              }`}
              title="Add to side-by-side comparison matrix"
            >
              <Columns className="w-3 h-3" />
              <span className="text-[10px]">Compare</span>
            </button>

            <button
              onClick={handleBookmark}
              disabled={isBookmarking || isBookmarked}
              className={`p-1.5 rounded-lg border text-xs transition ${
                isBookmarked
                  ? 'bg-[rgba(212,175,55,0.18)] text-[#F3D06B] border-[rgba(212,175,55,0.4)]'
                  : 'bg-white/[0.04] hover:bg-white/[0.08] border-white/10 text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
              title={isBookmarked ? 'Bookmarked' : 'Save to Bookmarks'}
            >
              <Bookmark className={`w-3.5 h-3.5 ${isBookmarked ? 'fill-[#D4AF37] text-[#D4AF37]' : ''}`} />
            </button>
          </div>

          {/* Luminous Gold Link CTA */}
          <div className="pt-2 border-t border-[rgba(212,175,55,0.1)] flex items-center justify-between text-xs font-mono text-[#D4AF37] group-hover:text-[#F3D06B] transition-colors font-semibold">
            <span>Read 350w →</span>
            <ChevronRight className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>
    </article>
  );
};
