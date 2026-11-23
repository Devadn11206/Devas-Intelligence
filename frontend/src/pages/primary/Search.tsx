import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Search as SearchIcon,
  FileText,
  Code2,
  Cpu,
  Newspaper,
  Wrench,
  Sparkles,
  Zap,
  ExternalLink,
  GitFork,
  CheckCircle,
  Bookmark,
  Clock,
} from 'lucide-react';
import { apiClient } from '../../api/client';
import { DocumentDetailDrawer } from '../../components/intel/DocumentDetailDrawer';

interface SearchResultItem {
  document_id: string;
  chunk_id: string;
  section_type: string;
  title: string;
  content_type: 'paper' | 'repo' | 'model' | 'article' | 'tool';
  canonical_url: string;
  source_name: string;
  published_at: string | null;
  matched_snippet: string;
  summary_ai: Record<string, any> | null;
  tags: string[];
  linked_repos_count: number;
  linked_papers_count: number;
  lexical_rank: number | null;
  vector_rank: number | null;
  rrf_score: number;
  rerank_score: number;
}

interface SearchResponseData {
  query: string;
  mode: 'hybrid' | 'lexical' | 'vector';
  total_candidates: number;
  latency_ms: number;
  cache_hit: boolean;
  facets: Record<string, number>;
  results: SearchResultItem[];
}

export const SearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const queryParam = searchParams.get('q') || '';
  const modeParam = (searchParams.get('mode') as 'hybrid' | 'lexical' | 'vector') || 'hybrid';
  const typeParam = searchParams.get('type') || '';
  const hasCodeParam = searchParams.get('has_code') === 'true';

  const [inputVal, setInputVal] = useState(queryParam);
  const [selectedDrawerDocId, setSelectedDrawerDocId] = useState<string | null>(null);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setInputVal(queryParam);
  }, [queryParam]);

  const { data: searchData, isLoading, isFetching } = useQuery<SearchResponseData>({
    queryKey: ['search_query', queryParam, modeParam, typeParam, hasCodeParam],
    queryFn: async () => {
      if (!queryParam.trim()) {
        return {
          query: '',
          mode: modeParam,
          total_candidates: 0,
          latency_ms: 0,
          cache_hit: false,
          facets: {},
          results: [],
        };
      }
      const res = await apiClient.post<SearchResponseData>('/v1/search', {
        query: queryParam.trim(),
        mode: modeParam,
        content_types: typeParam ? [typeParam] : null,
        has_linked_code: hasCodeParam ? true : null,
        top_k: 20,
      });
      return res.data;
    },
    enabled: Boolean(queryParam.trim()),
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;
    const next = new URLSearchParams(searchParams);
    next.set('q', inputVal.trim());
    setSearchParams(next);
  };

  const setFilterMode = (mode: 'hybrid' | 'lexical' | 'vector') => {
    const next = new URLSearchParams(searchParams);
    next.set('mode', mode);
    setSearchParams(next);
  };

  const setContentType = (t: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (!t) {
      next.delete('type');
    } else {
      next.set('type', t);
    }
    setSearchParams(next);
  };

  const toggleLinkedCode = () => {
    const next = new URLSearchParams(searchParams);
    if (hasCodeParam) {
      next.delete('has_code');
    } else {
      next.set('has_code', 'true');
    }
    setSearchParams(next);
  };

  const handleBookmark = async (docId: string, contentType: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (bookmarkedIds.has(docId)) return;
    try {
      await apiClient.post('/v1/users/me/bookmarks', {
        entity_type: contentType,
        entity_id: docId,
        notes: 'Bookmarked from Search',
      });
      setBookmarkedIds((prev) => new Set(prev).add(docId));
    } catch (err) {
      console.error('Failed to bookmark', err);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'paper':
        return <FileText className="w-3.5 h-3.5 text-blue-400" />;
      case 'repo':
        return <Code2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'model':
        return <Cpu className="w-3.5 h-3.5 text-purple-400" />;
      case 'article':
        return <Newspaper className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Wrench className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Search Controls Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-3">
          <div className="relative flex-1">
            <SearchIcon className="w-5 h-5 text-cyan-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="Search papers, repositories, models, or technical queries..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-12 pr-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition shadow-inner"
            />
          </div>
          <button
            type="submit"
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white font-semibold text-sm transition shadow-lg shrink-0"
          >
            Search
          </button>
        </form>

        {/* Retrieval Mode Selector & Facets */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/80 text-xs">
          {/* Mode Selector */}
          <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <span className="text-[11px] font-mono text-slate-400 px-2 flex items-center gap-1">
              <Zap className="w-3 h-3 text-cyan-400" /> Mode:
            </span>
            {[
              { id: 'hybrid', label: 'Hybrid + Rerank' },
              { id: 'lexical', label: 'Lexical BM25' },
              { id: 'vector', label: 'Dense Vector' },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => setFilterMode(m.id as any)}
                className={`px-2.5 py-1 rounded-md font-mono text-[11px] font-semibold transition ${
                  modeParam === m.id
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Quick Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setContentType(null)}
              className={`px-2.5 py-1 rounded-lg border text-xs transition ${
                !typeParam
                  ? 'bg-slate-800 text-white border-slate-600'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              All Types
            </button>
            {['paper', 'repo', 'model', 'article'].map((t) => (
              <button
                key={t}
                onClick={() => setContentType(typeParam === t ? null : t)}
                className={`px-2.5 py-1 rounded-lg border text-xs capitalize transition ${
                  typeParam === t
                    ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                {t}s {searchData?.facets?.[t] ? `(${searchData.facets[t]})` : ''}
              </button>
            ))}
            <button
              onClick={toggleLinkedCode}
              className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition ${
                hasCodeParam
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              ⚡ Has Linked Code
            </button>
          </div>
        </div>
      </div>

      {/* Telemetry Header */}
      {queryParam.trim() && searchData && (
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-2">
          <div className="flex items-center gap-3">
            <span>
              Found <b>{searchData.results.length}</b> results (from {searchData.total_candidates} candidates)
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-cyan-400" />
              {searchData.latency_ms} ms
            </span>
            {searchData.cache_hit && (
              <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px]">
                CACHE HIT (Redis)
              </span>
            )}
          </div>
          <span className="text-slate-400">
            RRF (k=60) + BGE Reranker
          </span>
        </div>
      )}

      {/* Main Results List */}
      <div className="space-y-4">
        {isLoading || isFetching ? (
          <div className="py-24 text-center text-slate-500 font-mono text-xs">
            Executing dual-path retrieval and cross-encoder reranking...
          </div>
        ) : !queryParam.trim() ? (
          <div className="py-24 text-center border border-dashed border-slate-800 rounded-2xl p-12 text-slate-400 space-y-2">
            <SearchIcon className="w-8 h-8 mx-auto text-slate-600" />
            <h3 className="text-base font-bold text-slate-300">Unified Knowledge Discovery</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Execute hybrid lexical BM25 and vector semantic searches across millions of papers, repos, and model benchmarks.
            </p>
          </div>
        ) : searchData?.results.length === 0 ? (
          <div className="py-24 text-center border border-slate-800 rounded-2xl bg-slate-900/40 p-12 text-slate-400">
            No intelligence records matched your query with the current filters.
          </div>
        ) : (
          searchData?.results.map((item) => {
            const isBookmarked = bookmarkedIds.has(item.document_id);
            return (
              <div
                key={item.document_id}
                onClick={() => setSelectedDrawerDocId(item.document_id)}
                className="bg-surface-card border border-slate-800 hover:border-slate-700 rounded-xl p-5 shadow-lg transition hover:shadow-cyan-950/20 cursor-pointer space-y-3.5 group"
              >
                {/* Result Item Header */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase font-mono bg-slate-900 border border-slate-800 text-slate-300">
                      {getTypeIcon(item.content_type)}
                      {item.content_type}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      {item.source_name}
                    </span>
                    {item.published_at && (
                      <span className="text-xs text-slate-500 font-mono">
                        • {new Date(item.published_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  {/* Badges / Metrics */}
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800 font-semibold" title="Reranker relevance score">
                      Relevance: {Math.round(item.rerank_score * 100)}%
                    </span>
                    <button
                      onClick={(e) => handleBookmark(item.document_id, item.content_type, e)}
                      title={isBookmarked ? 'Bookmarked' : 'Save bookmark'}
                      className={`p-1.5 rounded-lg border transition ${
                        isBookmarked
                          ? 'bg-amber-950/60 border-amber-700 text-amber-400'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-amber-400 hover:border-slate-700'
                      }`}
                    >
                      {isBookmarked ? (
                        <CheckCircle className="w-3.5 h-3.5 text-amber-400" />
                      ) : (
                        <Bookmark className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Title */}
                <div>
                  <h3 className="text-base font-bold text-slate-100 group-hover:text-cyan-300 transition-colors">
                    {item.title}
                  </h3>
                </div>

                {/* Matched Snippet (Provenance) */}
                <div className="bg-slate-900/80 border border-slate-800/80 rounded-lg p-3 text-xs text-slate-300 space-y-1">
                  <div className="flex items-center gap-1.5 text-[10px] uppercase font-mono text-slate-400 font-bold">
                    <Sparkles className="w-3 h-3 text-cyan-400" />
                    Matched {item.section_type} Snippet:
                  </div>
                  <p className="leading-relaxed text-slate-300">
                    {item.matched_snippet}
                  </p>
                </div>

                {/* Connected Code & Links */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/60 text-xs">
                  <div className="flex items-center gap-2">
                    {item.linked_repos_count > 0 && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800 text-xs font-medium">
                        <Code2 className="w-3 h-3 text-emerald-400" />
                        Code Linked ({item.linked_repos_count})
                      </span>
                    )}
                    {item.linked_papers_count > 0 && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-800 text-xs font-medium">
                        <FileText className="w-3 h-3 text-cyan-400" />
                        Paper Linked ({item.linked_papers_count})
                      </span>
                    )}
                    {item.tags.slice(0, 3).map((tag, i) => (
                      <span key={i} className="text-[11px] text-slate-400">
                        #{tag}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/explorer/${item.document_id}`);
                      }}
                      className="inline-flex items-center gap-1 text-slate-400 hover:text-cyan-400 transition"
                      title="Open Knowledge Graph"
                    >
                      <GitFork className="w-3.5 h-3.5" />
                      <span>Graph</span>
                    </button>
                    <a
                      href={item.canonical_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-slate-400 hover:text-cyan-400 transition"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Source</span>
                    </a>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Document Detail Drawer */}
      <DocumentDetailDrawer
        documentId={selectedDrawerDocId}
        onClose={() => setSelectedDrawerDocId(null)}
        onSelectSibling={(siblingId) => setSelectedDrawerDocId(siblingId)}
      />
    </div>
  );
};
