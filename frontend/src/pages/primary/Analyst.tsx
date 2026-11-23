import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { DocumentDetailDrawer } from '../../components/intel/DocumentDetailDrawer';
import {
  Brain,
  Sparkles,
  Send,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  RotateCcw,
  BookOpen,
  CheckCircle2,
  Zap,
  Microscope,
  FileText,
  Code2,
  Cpu,
  Newspaper,
  ArrowRight,
  Loader2,
} from 'lucide-react';

interface CitationSource {
  index: number;
  document_id: string;
  title: string;
  content_type: string;
  source_name: string;
  canonical_url: string;
  snippet?: string;
  relevance_score?: number;
}

interface Message {
  role: 'user' | 'assistant';
  text: string;
  citations?: CitationSource[];
  evidence_sufficient?: boolean;
  mode?: 'fast' | 'deep';
  model_name?: string;
  latency_ms?: number;
}

export const AnalystPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'fast' | 'deep'>('fast');
  const [scope, setScope] = useState<string>('all');
  const [conversation, setConversation] = useState<Message[]>([]);
  const [activeCitation, setActiveCitation] = useState<CitationSource | null>(null);
  const [selectedDrawerDocId, setSelectedDrawerDocId] = useState<string | null>(null);
  const [activeStepText, setActiveStepText] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasAutoSubmittedRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation, activeStepText]);

  // Handle incoming query param ?q= from comparison modal handoff
  useEffect(() => {
    const qParam = searchParams.get('q');
    if (qParam && !hasAutoSubmittedRef.current) {
      hasAutoSubmittedRef.current = true;
      const cleanPrompt = qParam.trim();
      // Remove query param from browser URL cleanly without refreshing
      setSearchParams({}, { replace: true });
      // Trigger execution immediately
      handleSend(cleanPrompt);
    }
  }, [searchParams, setSearchParams]);

  // Dynamic live starter prompts based on real ingested documents
  const { data: realFeed } = useQuery<{ items: any[] } | any[]>({
    queryKey: ['analyst_starter_feed'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/intel/feed?limit=6');
      return res.data;
    },
    staleTime: 120000,
  });

  const feedItems = Array.isArray(realFeed) ? realFeed : realFeed?.items || [];
  
  const starterPrompts = React.useMemo(() => {
    const list: string[] = [];
    if (feedItems.length > 0) {
      feedItems.slice(0, 3).forEach((item: any) => {
        if (item.title) {
          list.push(`Analyze the core technical architecture and tradeoffs of ${item.title}`);
        }
      });
    }
    // High-signal domain fallbacks
    list.push('How do Physics-Informed Neural Networks enforce Navier-Stokes boundary equations?');
    list.push('Compare speculative decoding with vLLM PagedAttention in high-throughput inference.');
    list.push('Summarize recent breakthroughs in audio source separation and latent diffusion models.');
    return list.slice(0, 4);
  }, [feedItems]);

  const handleSend = async (textToSend?: string) => {
    const q = (textToSend || query).trim();
    if (!q || isSubmitting) return;

    setErrorMessage(null);
    setQuery('');
    setIsSubmitting(true);
    setActiveStepText('1. Searching Hybrid Vector + BM25 Index...');

    // Append user message immediately
    const userMsg: Message = { role: 'user', text: q };
    setConversation((prev) => [...prev, userMsg]);

    try {
      // Step tracking simulation for instant feedback
      const timer = setTimeout(() => {
        setActiveStepText('2. Verifying Provenance Citations & CitationGuard...');
      }, 500);

      const res = await apiClient.post('/v1/agents/ask', {
        query: q,
        mode,
        content_type: scope === 'all' ? null : scope,
        stream: false,
      });

      clearTimeout(timer);
      setActiveStepText(null);

      const data = res.data;
      const assistantMsg: Message = {
        role: 'assistant',
        text: data.answer,
        citations: data.citations || [],
        evidence_sufficient: data.evidence_sufficient,
        mode: data.mode || mode,
        model_name: data.model_name,
        latency_ms: data.latency_ms,
      };

      setConversation((prev) => [...prev, assistantMsg]);

      // Automatically select first citation into evidence inspector
      if (data.citations && data.citations.length > 0) {
        setActiveCitation(data.citations[0]);
      }
    } catch (err: any) {
      setActiveStepText(null);
      const detail = err.response?.data?.detail || err.message || 'Failed to communicate with DEVA Analyst agent.';
      setErrorMessage(detail);
      setConversation((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `Error connecting to DEVA Agent service: ${detail}. Please verify backend health.`,
          evidence_sufficient: false,
        },
      ]);
    } finally {
      setIsSubmitting(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const getContentTypeIcon = (type?: string) => {
    switch (type) {
      case 'paper':
        return <FileText className="w-3.5 h-3.5 text-[#D4AF37]" />;
      case 'repo':
        return <Code2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'model':
        return <Cpu className="w-3.5 h-3.5 text-purple-400" />;
      default:
        return <Newspaper className="w-3.5 h-3.5 text-amber-400" />;
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] overflow-hidden">
      {/* Top Header & Scope Controls */}
      <div className="p-3.5 rounded-2xl glass-card border border-[rgba(212, 175, 55,0.16)] bg-[#0D1017]/90 mb-4 flex flex-col md:flex-row md:items-center justify-between gap-3 flex-shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl btn-gold-glow flex items-center justify-center text-white flex-shrink-0 shadow-lg">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-[#FFF6F0] flex items-center gap-2">
              <span>Autonomous AI Technical Analyst</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full pill-terracotta font-semibold">
                CITATION-GUARD v2.4
              </span>
            </div>
            <div className="text-[11px] text-[#A89890] font-mono">
              100% Provenance Guaranteed • Multi-Hop Evidence Reasoning
            </div>
          </div>
        </div>

        {/* Mode Toggle & Scope Pills */}
        <div className="flex items-center flex-wrap gap-2.5">
          {/* Mode: Fast vs Deep Swarm */}
          <div className="flex items-center bg-[#10131A] border border-[rgba(212, 175, 55,0.18)] p-1 rounded-xl">
            <button
              onClick={() => setMode('fast')}
              className={`px-3 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 transition ${
                mode === 'fast'
                  ? 'btn-gold-glow font-bold'
                  : 'text-[#A89890] hover:text-[#FFF6F0]'
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-amber-300" />
              <span>Fast Analyst</span>
            </button>
            <button
              onClick={() => setMode('deep')}
              className={`px-3 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 transition ${
                mode === 'deep'
                  ? 'bg-violet-500/20 text-violet-300 border border-violet-500/40 font-bold'
                  : 'text-[#A89890] hover:text-[#FFF6F0]'
              }`}
            >
              <Microscope className="w-3.5 h-3.5 text-violet-400" />
              <span>Deep Swarm</span>
            </button>
          </div>

          {/* Scope Filter */}
          <div className="flex items-center bg-[#10131A] border border-[rgba(212, 175, 55,0.15)] p-0.5 rounded-xl">
            {[
              { key: 'all', label: 'All Sources' },
              { key: 'paper', label: 'Papers' },
              { key: 'repo', label: 'GitHub Code' },
              { key: 'article', label: 'News' },
            ].map((sc) => (
              <button
                key={sc.key}
                onClick={() => setScope(sc.key)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-mono transition ${
                  scope === sc.key
                    ? 'bg-[rgba(212, 175, 55,0.35)] text-[#FFF6F0] font-semibold'
                    : 'text-[#A89890] hover:text-[#FFF6F0]'
                }`}
              >
                {sc.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => {
              setConversation([]);
              setActiveCitation(null);
            }}
            className="p-2 rounded-xl bg-[#10131A] border border-[rgba(212, 175, 55,0.15)] text-[#A89890] hover:text-[#FFF6F0] hover:border-[#D4AF37]/40 transition"
            title="Reset conversation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Workspace Body (Chat Stream + Right Evidence Drawer) */}
      <div className="flex-1 flex gap-4 min-h-0 overflow-hidden">
        {/* Left Column: Conversational Stream */}
        <div className="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden border border-[rgba(212, 175, 55,0.18)] min-w-0 bg-[#0E0A08]/70">
          
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-5">
            {errorMessage && (
              <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-300 text-xs font-mono flex items-center justify-between animate-in fade-in">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <span>{errorMessage}</span>
                </div>
                <button onClick={() => setErrorMessage(null)} className="text-amber-400 hover:text-white">
                  ✕
                </button>
              </div>
            )}

            {conversation.length === 0 ? (
              <div className="max-w-xl mx-auto py-8 text-center space-y-6">
                <div className="w-12 h-12 rounded-2xl btn-gold-glow flex items-center justify-center text-white mx-auto shadow-xl">
                  <Sparkles className="w-6 h-6 animate-pulse" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-[#FFF6F0] tracking-tight">
                    Ask the DEVA Autonomous Technical Analyst
                  </h2>
                  <p className="text-xs text-[#A89890] mt-1.5 leading-relaxed font-sans">
                    Synthesize cross-domain research papers, open-source repository implementations, and engineering benchmarks with verifiable inline citations.
                  </p>
                </div>

                {/* Grounded Starter Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left pt-2">
                  {starterPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(prompt)}
                      className="p-3.5 rounded-xl glass-card text-xs text-[#EAD8D0] hover:text-[#FFF6F0] hover:border-[#D4AF37]/40 transition group flex flex-col justify-between"
                    >
                      <span className="leading-snug">{prompt}</span>
                      <span className="text-[10px] font-mono text-[#D4AF37] mt-2.5 flex items-center gap-1 group-hover:translate-x-1 transition-transform font-semibold">
                        Ask Analyst <ChevronRight className="w-3 h-3" />
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              conversation.map((msg, i) => (
                <div
                  key={i}
                  className={`flex flex-col ${
                    msg.role === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  <div
                    className={`max-w-3xl rounded-2xl p-4 text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'btn-gold-glow text-white font-medium shadow-md'
                        : 'glass-panel text-[#FFF6F0] border border-[rgba(212, 175, 55,0.18)] bg-[#140F0D]/90'
                    }`}
                  >
                    {/* Insufficient Evidence Alert */}
                    {msg.role === 'assistant' && msg.evidence_sufficient === false && (
                      <div className="mb-3 p-3 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-300 text-xs flex items-center gap-2 font-mono">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
                        <span>
                          INSUFFICIENT EVIDENCE DETECTED: Ground-truth sources did not meet verification threshold.
                        </span>
                      </div>
                    )}

                    {/* Formatted Content */}
                    <div className="space-y-3 font-sans leading-relaxed text-[13.5px] text-[#F8FAFC] whitespace-pre-wrap">
                      {msg.text}
                    </div>

                    {/* Inline Citation Chips */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3.5 pt-3 border-t border-[rgba(212, 175, 55,0.12)] flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] font-mono text-[#A89890] mr-1">
                          Verified Sources:
                        </span>
                        {msg.citations.map((c) => (
                          <button
                            key={c.index}
                            onClick={() => setActiveCitation(c)}
                            className={`text-[10px] font-mono px-2.5 py-1 rounded-lg border transition flex items-center gap-1.5 ${
                              activeCitation?.index === c.index
                                ? 'btn-gold-glow shadow-[0_0_8px_rgba(212, 175, 55,0.4)]'
                                : 'pill-terracotta hover:border-[#D4AF37]/50 hover:text-white'
                            }`}
                          >
                            <span>[{c.index}]</span>
                            <span className="truncate max-w-[140px] font-sans">{c.title}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Active Progress Tracker */}
            {isSubmitting && (
              <div className="flex items-center space-x-2.5 p-3 rounded-xl bg-[#10131A]/80 border border-[rgba(212, 175, 55,0.2)] text-xs font-mono text-[#D4AF37] animate-in fade-in">
                <Loader2 className="w-4 h-4 animate-spin text-[#D4AF37]" />
                <span className="font-semibold">{activeStepText || 'Reasoning over multi-hop corpus...'}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-3.5 border-t border-[rgba(212, 175, 55,0.14)] bg-[rgba(19, 22, 29,0.85)]">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="relative flex items-center"
            >
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={
                  mode === 'deep'
                    ? 'Launch Deep Swarm research across papers, repositories, and models...'
                    : 'Ask technical question across papers, repositories, and models...'
                }
                className="w-full bg-[rgba(10, 12, 16,0.85)] border border-[rgba(212, 175, 55,0.18)] rounded-xl pl-4 pr-12 py-3 text-xs text-[#FFF6F0] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono transition"
              />
              <button
                type="submit"
                disabled={!query.trim() || isSubmitting}
                className="absolute right-2 p-2 rounded-lg btn-gold-glow disabled:opacity-40 transition"
              >
                <Send className="w-3.5 h-3.5 text-white" />
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Verified Sources & Provenance Inspector */}
        <div className="w-88 glass-panel rounded-2xl p-4 hidden lg:flex flex-col border border-[rgba(212, 175, 55,0.18)] bg-[#0E0A08]/75">
          <div className="flex items-center justify-between pb-3 border-b border-[rgba(212, 175, 55,0.12)]">
            <div className="flex items-center space-x-2 text-xs font-mono font-bold text-[#FFF6F0]">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>VERIFIED SOURCES DRAWER</span>
            </div>
            <span className="text-[10px] font-mono text-[#A89890] px-1.5 py-0.5 rounded bg-[#10131A]">
              {activeCitation ? `[${activeCitation.index}] ACTIVE` : 'IDLE'}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto py-3 space-y-3.5">
            {activeCitation ? (
              <div className="space-y-3.5 p-4 rounded-xl bg-[rgba(212, 175, 55,0.15)] border border-[rgba(212, 175, 55,0.22)] animate-in fade-in">
                <div className="flex items-center justify-between text-[10px] font-mono text-[#F3D06B]">
                  <span className="flex items-center gap-1.5">
                    {getContentTypeIcon(activeCitation.content_type)}
                    <strong className="uppercase">{activeCitation.content_type}</strong> • [{activeCitation.index}]
                  </span>
                  <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                    <CheckCircle2 className="w-3 h-3" /> Grounded
                  </span>
                </div>

                <h3 className="text-xs font-bold text-[#FFF6F0] leading-snug">
                  {activeCitation.title}
                </h3>

                <div className="text-[11px] font-mono text-[#A89890]">
                  Source: <span className="text-[#EAD8D0]">{activeCitation.source_name}</span>
                </div>

                {activeCitation.snippet && (
                  <div className="p-3 rounded-lg bg-[#0A0706] border border-[rgba(212, 175, 55,0.12)] text-[11px] text-[#94A3B8] font-mono leading-relaxed max-h-36 overflow-y-auto">
                    "{activeCitation.snippet}"
                  </div>
                )}

                <div className="pt-2 flex items-center justify-between gap-2 border-t border-[rgba(212, 175, 55,0.12)]">
                  {activeCitation.document_id && (
                    <button
                      onClick={() => setSelectedDrawerDocId(activeCitation.document_id)}
                      className="inline-flex items-center gap-1 text-xs font-mono text-[#D4AF37] hover:text-[#FFA078] font-medium"
                    >
                      <span>Read 350w Briefing</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  )}

                  {activeCitation.canonical_url && (
                    <a
                      href={activeCitation.canonical_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded-lg bg-[#10131A] text-[#A89890] hover:text-[#FFF6F0] border border-[rgba(212, 175, 55,0.15)]"
                      title="Open Canonical Evidence"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-xs font-mono text-[#64748B] space-y-2">
                <BookOpen className="w-7 h-7 mx-auto opacity-50 text-[#D4AF37]" />
                <div className="leading-relaxed px-4">
                  Click any inline citation [N] to inspect grounded document evidence and read executive briefings.
                </div>
              </div>
            )}
          </div>

          <div className="p-2.5 rounded-xl bg-[rgba(19, 22, 29,0.7)] border border-[rgba(212, 175, 55,0.12)] text-[10px] font-mono text-[#A89890] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>DEVA Grounding Engine: Zero Hallucination Guardrail Active</span>
          </div>
        </div>
      </div>

      {/* Slide-out Full Executive Briefing Drawer */}
      {selectedDrawerDocId && (
        <DocumentDetailDrawer
          documentId={selectedDrawerDocId}
          onClose={() => setSelectedDrawerDocId(null)}
          onSelectSibling={(sibId) => setSelectedDrawerDocId(sibId)}
        />
      )}
    </div>
  );
};
