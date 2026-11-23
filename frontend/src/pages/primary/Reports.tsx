import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  FileText,
  Sparkles,
  Download,
  Printer,
  Copy,
  Check,
  Volume2,
  Trash2,
  BookOpen,
  Calendar,
  ChevronRight,
  ShieldCheck,
  AlertCircle,
  ExternalLink,
  Code2,
  Cpu,
} from 'lucide-react';

interface UserBriefingItem {
  id: string;
  user_id: string;
  title: string;
  briefing_type: 'daily_digest' | 'deep_dossier' | 'weekly_radar';
  domain: string | null;
  executive_summary: string;
  content_markdown: string;
  source_count: number;
  status: string;
  created_at: string;
}

export const ReportsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [topic, setTopic] = useState('');
  const [briefingType, setBriefingType] = useState<'deep_dossier' | 'daily_digest' | 'weekly_radar'>('deep_dossier');
  const [domain, setDomain] = useState('Scientific Computing');
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [generationStep, setGenerationStep] = useState<string>('Querying live intelligence index...');

  // Query User Preferences for Digest Frequency
  const { data: userPref } = useQuery({
    queryKey: ['my_preferences'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/users/me/preferences');
      return res.data;
    },
  });

  // Query Saved Briefings
  const { data: reports, isLoading } = useQuery<UserBriefingItem[]>({
    queryKey: ['user_briefings'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/reports');
      return res.data;
    },
  });

  // Automatically select first report if none selected
  const activeReport =
    reports?.find((r) => r.id === selectedReportId) || (reports && reports.length > 0 ? reports[0] : null);

  // Generate Report Mutation
  const generateMutation = useMutation({
    mutationFn: async (payload: { topic: string; briefing_type: string; domain: string }) => {
      setErrorMessage(null);
      const res = await apiClient.post('/v1/reports/generate', payload);
      return res.data;
    },
    onSuccess: (newReport: UserBriefingItem) => {
      queryClient.setQueryData<UserBriefingItem[]>(['user_briefings'], (old) => {
        if (!old) return [newReport];
        return [newReport, ...old.filter((r) => r.id !== newReport.id)];
      });
      setSelectedReportId(newReport.id);
      setTopic('');
      setToastMessage(`Dossier "${newReport.title}" generated successfully!`);
      setTimeout(() => setToastMessage(null), 4000);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to synthesize dossier';
      setErrorMessage(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  // Animated generation progress steps
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (generateMutation.isPending) {
      const steps = [
        'Querying live intelligence index & research papers...',
        'Extracting mathematical models & ablation telemetry...',
        'Linking open-source GitHub & Hugging Face repositories...',
        'Compiling 5-section verified executive dossier...',
      ];
      let i = 0;
      setGenerationStep(steps[0]);
      interval = setInterval(() => {
        i = (i + 1) % steps.length;
        setGenerationStep(steps[i]);
      }, 2200);
    }
    return () => clearInterval(interval);
  }, [generateMutation.isPending]);

  // Delete Report Mutation
  const deleteMutation = useMutation({
    mutationFn: async (reportId: string) => {
      await apiClient.delete(`/v1/reports/${reportId}`);
    },
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData<UserBriefingItem[]>(['user_briefings'], (old) =>
        old ? old.filter((r) => r.id !== deletedId) : []
      );
      if (selectedReportId === deletedId) {
        setSelectedReportId(null);
      }
      setToastMessage('Briefing deleted.');
      setTimeout(() => setToastMessage(null), 3000);
    },
  });

  // Update Frequency Mutation
  const freqMutation = useMutation({
    mutationFn: async (frequency: 'daily' | 'weekly' | 'off') => {
      await apiClient.put('/v1/users/me/preferences', {
        digest_frequency: frequency,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my_preferences'] });
      setToastMessage('Digest delivery schedule updated.');
      setTimeout(() => setToastMessage(null), 3000);
    },
  });

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || generateMutation.isPending) return;
    generateMutation.mutate({ topic, briefing_type: briefingType, domain });
  };

  const handleCopy = () => {
    if (!activeReport) return;
    navigator.clipboard.writeText(
      `# ${activeReport.title}\n\n**Executive Summary:** ${activeReport.executive_summary}\n\n${activeReport.content_markdown}`
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!activeReport) return;
    const element = document.createElement('a');
    const file = new Blob(
      [`# ${activeReport.title}\n\n**Executive Summary:**\n${activeReport.executive_summary}\n\n${activeReport.content_markdown}`],
      { type: 'text/markdown' }
    );
    element.href = URL.createObjectURL(file);
    element.download = `${activeReport.title.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleSpeak = () => {
    if (!('speechSynthesis' in window) || !activeReport) return;
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    const cleanContent = activeReport.content_markdown
      .replace(/\[\d+\]/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/[#*`_]/g, '');
    const utterance = new SpeechSynthesisUtterance(
      `${activeReport.title}. Executive summary: ${activeReport.executive_summary}. ${cleanContent}`
    );
    utterance.rate = 1.05;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'daily_digest':
        return <span className="pill-terracotta text-[9px] font-mono font-semibold px-2 py-0.5 rounded">DAILY DIGEST</span>;
      case 'weekly_radar':
        return <span className="bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[9px] font-mono font-semibold px-2 py-0.5 rounded">WEEKLY RADAR</span>;
      default:
        return <span className="btn-gold-glow text-[9px] font-mono font-bold px-2 py-0.5 rounded shadow-sm">DEEP DOSSIER</span>;
    }
  };

  // Helper to render markdown paragraphs with clickable links & citation pills
  const renderFormattedParagraph = (paragraph: string, pIdx: number) => {
    // Header line
    if (paragraph.startsWith('### ')) {
      return (
        <h2
          key={pIdx}
          className="text-sm font-bold text-[#F3D06B] font-mono tracking-tight pt-4 pb-1 border-t border-[rgba(212, 175, 55,0.12)] flex items-center gap-2"
        >
          {paragraph.includes('Code') || paragraph.includes('Open-Source') ? (
            <Code2 className="w-4 h-4 text-[#D4AF37]" />
          ) : paragraph.includes('References') ? (
            <BookOpen className="w-4 h-4 text-emerald-400" />
          ) : (
            <Cpu className="w-4 h-4 text-[#D4AF37]" />
          )}
          <span>{paragraph.replace('### ', '')}</span>
        </h2>
      );
    }

    // List item (e.g. repos or references)
    if (paragraph.startsWith('- ') || paragraph.startsWith('• ')) {
      const items = paragraph.split('\n');
      return (
        <ul key={pIdx} className="space-y-2 my-2">
          {items.map((it, itIdx) => {
            const cleanItem = it.replace(/^[-•]\s*/, '');
            return (
              <li
                key={itIdx}
                className="text-xs text-[#94A3B8] leading-relaxed p-2.5 rounded-lg bg-[rgba(19, 22, 29,0.4)] border border-[rgba(212, 175, 55,0.08)] hover:border-[rgba(212, 175, 55,0.2)] transition"
              >
                {renderInlineMarkdown(cleanItem)}
              </li>
            );
          })}
        </ul>
      );
    }

    // Numbered references (e.g. [1] **Title**...)
    if (/^\[\d+\]/.test(paragraph)) {
      const lines = paragraph.split('\n');
      return (
        <div key={pIdx} className="space-y-2 my-3">
          {lines.map((line, lIdx) => (
            <div
              key={lIdx}
              className="text-xs text-[#94A3B8] leading-relaxed p-2 rounded-lg bg-[rgba(19, 22, 29,0.4)] border border-[rgba(212, 175, 55,0.08)] flex items-start gap-2"
            >
              {renderInlineMarkdown(line)}
            </div>
          ))}
        </div>
      );
    }

    // Standard prose paragraph
    return (
      <p key={pIdx} className="text-xs text-[#94A3B8] leading-relaxed">
        {renderInlineMarkdown(paragraph)}
      </p>
    );
  };

  // Parse inline Markdown: bolding, links, citations [1]
  const renderInlineMarkdown = (textStr: string) => {
    // Regex matching [text](url) OR [number] citation OR **bold**
    const parts: React.ReactNode[] = [];
    const regex = /\[(\d+)\]|\[(.*?)\]\((.*?)\)|\*\*(.*?)\*/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(textStr)) !== null) {
      if (match.index > lastIndex) {
        parts.push(textStr.substring(lastIndex, match.index));
      }

      if (match[1]) {
        // Citation pill [1]
        parts.push(
          <span
            key={match.index}
            className="inline-flex items-center justify-center px-1.5 py-0.2 mx-0.5 rounded text-[10px] font-mono font-bold bg-[#D4AF37]/20 text-[#F3D06B] border border-[#D4AF37]/30"
          >
            [{match[1]}]
          </span>
        );
      } else if (match[2] && match[3]) {
        // Link [text](url)
        parts.push(
          <a
            key={match.index}
            href={match[3]}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[#D4AF37] hover:text-[#F3D06B] underline underline-offset-2 transition font-medium"
          >
            <span>{match[2]}</span>
            <ExternalLink className="w-2.5 h-2.5 opacity-80" />
          </a>
        );
      } else if (match[4]) {
        // Bold
        parts.push(
          <strong key={match.index} className="font-semibold text-[#F8FAFC]">
            {match[4]}
          </strong>
        );
      }

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < textStr.length) {
      parts.push(textStr.substring(lastIndex));
    }

    return parts;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#10131A] border border-emerald-500/40 text-emerald-300 font-mono text-xs shadow-2xl animate-in slide-in-from-top-2">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Action Header */}
      <div className="glass-panel rounded-2xl p-6 border border-[rgba(212, 175, 55,0.18)]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-[11px] font-mono text-[#D4AF37] mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] animate-ping"></span>
              <span>AUTONOMOUS AGENTS • EXECUTIVE SYNTHESIS STUDIO</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#F8FAFC] tracking-tight">
              Intelligence Briefings & Dossiers
            </h1>
            <p className="text-xs text-[#94A3B8] mt-1 max-w-2xl font-sans leading-relaxed">
              Synthesize multi-hop technical research papers, verified open-source code repositories, and sector radar signals into citation-grounded executive intelligence dossiers.
            </p>
          </div>
        </div>

        {/* Quick Generator Bar */}
        <form onSubmit={handleGenerate} className="mt-5 pt-4 border-t border-[rgba(212, 175, 55,0.12)] flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              required
              placeholder="Enter research topic (e.g. PINN, Physics-Informed Neural Networks, Efficient LLM Serving)..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full bg-[rgba(10, 12, 16,0.8)] border border-[rgba(212, 175, 55,0.16)] rounded-xl pl-4 pr-4 py-2.5 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono transition"
            />
          </div>

          <select
            value={briefingType}
            onChange={(e: any) => setBriefingType(e.target.value)}
            className="bg-[rgba(10, 12, 16,0.8)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3 py-2.5 text-xs text-[#F8FAFC] font-mono focus:outline-none focus:border-[#D4AF37]"
          >
            <option value="deep_dossier">Deep Research Dossier</option>
            <option value="daily_digest">Daily Personalized Digest</option>
            <option value="weekly_radar">Weekly Sector Radar</option>
          </select>

          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="bg-[rgba(10, 12, 16,0.8)] border border-[rgba(212, 175, 55,0.16)] rounded-xl px-3 py-2.5 text-xs text-[#F8FAFC] font-mono focus:outline-none focus:border-[#D4AF37]"
          >
            <option value="Scientific Computing">Scientific & Space Tech (PINNs)</option>
            <option value="Artificial Intelligence">AI & Machine Learning</option>
            <option value="Healthcare & Biotech">Healthcare & Biotech</option>
            <option value="Audio & Entertainment">Music & Audio AI</option>
          </select>

          <button
            type="submit"
            disabled={!topic.trim() || generateMutation.isPending}
            className="px-5 py-2.5 rounded-xl btn-gold-glow text-xs font-mono font-semibold flex items-center justify-center gap-2 transition disabled:opacity-50 shrink-0 shadow-lg"
          >
            {generateMutation.isPending ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Synthesizing Dossier...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Generate Dossier</span>
              </>
            )}
          </button>
        </form>

        {/* Error Callout */}
        {errorMessage && (
          <div className="mt-4 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-mono flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <div className="flex-1">
              <strong>Generation Error:</strong> {errorMessage}
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-amber-400 hover:text-amber-200 text-xs underline font-sans"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* 2-Column Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Saved Briefings & Scheduled Digests (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel rounded-2xl p-4 border border-[rgba(212, 175, 55,0.18)] space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[rgba(212, 175, 55,0.1)] text-xs font-mono font-bold text-[#F8FAFC]">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-[#D4AF37]" />
                <span>SAVED BRIEFINGS & DOSSIERS</span>
              </div>
              <span className="text-[10px] text-[#F3D06B] font-semibold">{reports?.length || 0} TOTAL</span>
            </div>

            {isLoading ? (
              <div className="py-12 text-center text-xs font-mono text-[#64748B]">
                <div className="w-5 h-5 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                Loading intelligence archive...
              </div>
            ) : !reports || reports.length === 0 ? (
              <div className="py-12 text-center text-xs font-mono text-[#64748B] space-y-2">
                <BookOpen className="w-6 h-6 mx-auto opacity-40 text-[#D4AF37]" />
                <div>No briefings generated yet. Use the bar above to launch your first dossier.</div>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
                {reports.map((report) => {
                  const isSelected = activeReport?.id === report.id;
                  return (
                    <div
                      key={report.id}
                      onClick={() => setSelectedReportId(report.id)}
                      className={`p-3.5 rounded-xl cursor-pointer transition flex flex-col justify-between border ${
                        isSelected
                          ? 'glass-panel-elevated border-[#D4AF37]/60 shadow-[0_0_15px_rgba(212, 175, 55,0.15)]'
                          : 'bg-[rgba(19, 22, 29,0.5)] border-[rgba(212, 175, 55,0.1)] hover:border-[rgba(212, 175, 55,0.25)]'
                      }`}
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          {getTypeBadge(report.briefing_type)}
                          <div className="flex items-center space-x-2">
                            <span className="text-[10px] font-mono text-[#64748B]">
                              {new Date(report.created_at).toLocaleDateString()}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteMutation.mutate(report.id);
                              }}
                              className="text-[#64748B] hover:text-rose-400 p-1 transition"
                              title="Delete briefing"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>

                        <h3 className="text-xs font-bold text-[#F8FAFC] line-clamp-2 leading-snug">
                          {report.title}
                        </h3>

                        <p className="text-[11px] text-[#94A3B8] line-clamp-2 leading-relaxed">
                          {report.executive_summary}
                        </p>
                      </div>

                      <div className="mt-2.5 pt-2 border-t border-[rgba(212, 175, 55,0.08)] flex items-center justify-between text-[10px] font-mono text-[#64748B]">
                        <span className="text-[#F3D06B]">{report.source_count} Sources Grounded</span>
                        <span className="flex items-center gap-1 text-[#D4AF37]">
                          View Dossier <ChevronRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Compact Digest Schedule Card */}
          <div className="glass-panel rounded-2xl p-4 border border-[rgba(212, 175, 55,0.18)] space-y-3">
            <div className="flex items-center space-x-2 text-xs font-mono font-bold text-[#F8FAFC]">
              <Calendar className="w-4 h-4 text-[#D4AF37]" />
              <span>AUTOMATED DIGEST DELIVERY SCHEDULE</span>
            </div>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Celery Beat autonomously compiles customized executive dossiers delivered directly to your tenant inbox based on your followed domain vectors.
            </p>

            <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-xs">
              {(['daily', 'weekly', 'off'] as const).map((freq) => {
                const isSelected = (userPref?.digest_frequency || 'weekly') === freq;
                return (
                  <button
                    key={freq}
                    onClick={() => freqMutation.mutate(freq)}
                    className={`py-2 px-2 rounded-xl text-center capitalize transition border ${
                      isSelected
                        ? 'btn-gold-glow font-bold'
                        : 'bg-[rgba(19, 22, 29,0.5)] border-[rgba(212, 175, 55,0.1)] text-[#94A3B8] hover:text-[#F8FAFC]'
                    }`}
                  >
                    {freq === 'off' ? 'Disabled' : `${freq}`}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Full Dossier Reader & Export Studio (7 cols) */}
        <div className="lg:col-span-7">
          {generateMutation.isPending ? (
            <div className="glass-panel rounded-2xl p-12 text-center border border-[#D4AF37]/40 bg-[#0D1017]/90 space-y-4 shadow-2xl">
              <div className="w-12 h-12 border-3 border-[#D4AF37] border-t-transparent rounded-full animate-spin mx-auto" />
              <div className="space-y-1">
                <div className="text-sm font-bold text-[#F8FAFC] font-mono">Synthesizing Executive Dossier</div>
                <div className="text-xs text-[#F3D06B] font-mono animate-pulse">{generationStep}</div>
              </div>
              <div className="w-full max-w-md mx-auto bg-[rgba(19, 22, 29,0.8)] h-1.5 rounded-full overflow-hidden border border-[rgba(212, 175, 55,0.1)]">
                <div className="bg-gradient-to-r from-[#D4AF37] to-[#F3D06B] h-full w-2/3 animate-pulse rounded-full" />
              </div>
              <p className="text-[11px] text-[#64748B] font-sans max-w-sm mx-auto">
                Executing hybrid vector search, ranking cross-domain literature, and mapping open-source repository bindings...
              </p>
            </div>
          ) : !activeReport ? (
            <div className="glass-panel rounded-2xl p-16 text-center text-xs font-mono text-[#64748B] border border-[rgba(212, 175, 55,0.18)] space-y-3">
              <BookOpen className="w-10 h-10 mx-auto text-[#D4AF37] opacity-50" />
              <div className="text-base font-bold text-[#F8FAFC]">Select a Briefing to Inspect</div>
              <div>Choose a saved research report from the left or generate a new dossier above.</div>
            </div>
          ) : (
            <div className="glass-panel rounded-2xl border border-[rgba(212, 175, 55,0.18)] overflow-hidden">
              {/* Sticky Action Bar */}
              <div className="p-4 border-b border-[rgba(212, 175, 55,0.12)] bg-[rgba(19, 22, 29,0.85)] backdrop-blur-xl flex items-center justify-between flex-wrap gap-2 sticky top-0 z-10">
                <div className="flex items-center space-x-2">
                  {getTypeBadge(activeReport.briefing_type)}
                  <span className="text-[10px] font-mono text-[#64748B]">
                    {new Date(activeReport.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleSpeak}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition border ${
                      isSpeaking
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/50'
                        : 'bg-[rgba(212, 175, 55,0.22)] text-[#F3D06B] border-[rgba(212, 175, 55,0.2)] hover:border-[#D4AF37] hover:text-white'
                    }`}
                    title="Listen to briefing via TTS"
                  >
                    <Volume2 className="w-3.5 h-3.5 text-[#D4AF37]" />
                    <span>{isSpeaking ? 'Stop Voice' : 'Listen'}</span>
                  </button>

                  <button
                    onClick={handleCopy}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-[rgba(19, 22, 29,0.7)] text-[#94A3B8] border border-[rgba(212, 175, 55,0.14)] hover:text-white hover:border-[#D4AF37]/40 transition"
                    title="Copy Markdown to Clipboard"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>

                  <button
                    onClick={handleDownload}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-[rgba(19, 22, 29,0.7)] text-[#94A3B8] border border-[rgba(212, 175, 55,0.14)] hover:text-white hover:border-[#D4AF37]/40 transition"
                    title="Download .md file"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>.MD</span>
                  </button>

                  <button
                    onClick={handlePrint}
                    className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg btn-gold-glow text-xs font-mono font-semibold transition"
                    title="Export / Print PDF"
                  >
                    <Printer className="w-3.5 h-3.5" />
                    <span>Export PDF</span>
                  </button>
                </div>
              </div>

              {/* Dossier Content Reader */}
              <div className="p-8 space-y-6 max-h-[750px] overflow-y-auto font-sans leading-relaxed text-[#F8FAFC]">
                <div className="space-y-2 pb-5 border-b border-[rgba(212, 175, 55,0.12)]">
                  <h1 className="text-2xl font-extrabold text-[#F8FAFC] tracking-tight">
                    {activeReport.title}
                  </h1>
                  <div className="flex items-center space-x-3 text-xs font-mono text-[#64748B] flex-wrap gap-y-1">
                    <span className="text-[#F3D06B]">Domain: {activeReport.domain}</span>
                    <span>•</span>
                    <span>Status: {activeReport.status}</span>
                    <span>•</span>
                    <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                      <ShieldCheck className="w-3.5 h-3.5" /> Verified Multi-Hop Synthesis
                    </span>
                    <span>•</span>
                    <span className="text-[#F3D06B]">{activeReport.source_count} Sources Grounded</span>
                  </div>
                </div>

                {/* Executive Summary Card */}
                <div className="p-4 rounded-xl bg-[rgba(212, 175, 55,0.2)] border border-[rgba(212, 175, 55,0.2)] space-y-1.5">
                  <div className="text-xs font-mono font-bold text-[#F3D06B] uppercase">
                    Executive Summary & Inflection Takeaway
                  </div>
                  <p className="text-xs text-[#F8FAFC] leading-relaxed">
                    {activeReport.executive_summary}
                  </p>
                </div>

                {/* Markdown Sections Body with clickable links & citation pills */}
                <div className="prose prose-invert max-w-none text-xs leading-relaxed space-y-4 text-[#94A3B8]">
                  {activeReport.content_markdown.split('\n\n').map((paragraph, idx) =>
                    renderFormattedParagraph(paragraph, idx)
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
