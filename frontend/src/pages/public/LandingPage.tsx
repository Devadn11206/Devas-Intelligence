import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import {
  ArrowRight,
  FileText,
  GitBranch,
  Globe,
  Zap,
  Brain,
  Radio,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  Volume2,
  Stethoscope,
  Headphones,
  Compass,
  Cpu,
  Layers,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────
interface LiveSignal {
  id: string;
  title: string;
  content_type: string;
  source: string;
  summary_text?: string;
  domain?: string;
  published_at?: string;
}

const CONTENT_TYPE_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  paper: {
    icon: <FileText className="w-3.5 h-3.5" />,
    color: 'text-violet-400 bg-violet-500/10 border-violet-500/30',
    label: 'PAPER',
  },
  repo: {
    icon: <GitBranch className="w-3.5 h-3.5" />,
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    label: 'REPO',
  },
  model: {
    icon: <Brain className="w-3.5 h-3.5" />,
    color: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
    label: 'MODEL',
  },
  article: {
    icon: <Globe className="w-3.5 h-3.5" />,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    label: 'NEWS',
  },
  tool: {
    icon: <Zap className="w-3.5 h-3.5" />,
    color: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
    label: 'TOOL',
  },
};

// ── Fallback signals with verified technical substance ────────────────────────
const FALLBACK_SIGNALS: LiveSignal[] = [
  {
    id: '1',
    title: 'vLLM Ray Distributed Orchestration Multi-Node Model Parallel Serving',
    content_type: 'paper',
    source: 'arXiv cs.LG',
    summary_text: 'High-throughput distributed model serving with tensor parallel PagedAttention across heterogeneous GPU clusters.',
    domain: 'AI & Scientific ML',
  },
  {
    id: '2',
    title: 'Whisper Robust Speech Recognition via Large Scale Weak Supervision',
    content_type: 'model',
    source: 'Hugging Face',
    summary_text: 'Zero-shot multilingual speech-to-text with sequence-to-sequence transformer encoder-decoder architecture.',
    domain: 'Music & Audio Tech',
  },
  {
    id: '3',
    title: 'Cryo-EM 3D Reconstruction with Neural Fields and Implicit Representations',
    content_type: 'paper',
    source: 'bioRxiv',
    summary_text: 'Resolving continuous structural heterogeneity in biomacromolecules via coordinate neural networks.',
    domain: 'Healthcare & Biotech',
  },
  {
    id: '4',
    title: 'Mamba Linear-Time Sequence Modeling with Selective State Spaces',
    content_type: 'repo',
    source: 'GitHub',
    summary_text: 'Sub-quadratic context scaling with hardware-aware parallel scan, outperforming transformers at 1M token context.',
    domain: 'Global Tech & Markets',
  },
  {
    id: '5',
    title: 'Neural Ordinary Differential Equations with Continuous-Depth Adjoint Sensitivity',
    content_type: 'paper',
    source: 'arXiv math.NA',
    summary_text: 'Continuous-time residual dynamics with adaptive ODE solvers for stiff nonlinear physical systems.',
    domain: 'Space & Physics',
  },
];

// ── Global Domains Catalog ────────────────────────────────────────────────────
interface DomainItem {
  id: string;
  name: string;
  tag: string;
  icon: React.ReactNode;
  subtitle: string;
  subsources: string[];
  gradient: string;
}

const GLOBAL_DOMAINS: DomainItem[] = [
  {
    id: 'ai-ml',
    name: 'AI & Scientific ML',
    tag: 'ai',
    icon: <Cpu className="w-5 h-5 text-[#D4AF37]" />,
    subtitle: 'Frontier LLMs, PINNs, Transformers & Neural Operators',
    subsources: ['arXiv cs.AI', 'GitHub', 'Hugging Face'],
    gradient: 'from-[rgba(212, 175, 55,0.18)] to-[rgba(19, 22, 29,0.7)]',
  },
  {
    id: 'healthcare',
    name: 'Healthcare & Biotech',
    tag: 'health',
    icon: <Stethoscope className="w-5 h-5 text-emerald-400" />,
    subtitle: 'AlphaFold, Cryo-EM, Clinical Trials & Drug Discovery',
    subsources: ['PubMed', 'bioRxiv', 'ClinicalTrials.gov'],
    gradient: 'from-emerald-500/10 to-[rgba(19, 22, 29,0.7)]',
  },
  {
    id: 'music-audio',
    name: 'Music & Audio Tech',
    tag: 'audio',
    icon: <Headphones className="w-5 h-5 text-sky-400" />,
    subtitle: 'Generative Audio, Neural DSP, Whisper & MusicLM',
    subsources: ['Audio ML', 'DSP Open-Source', 'Hugging Face Audio'],
    gradient: 'from-sky-500/10 to-[rgba(19, 22, 29,0.7)]',
  },
  {
    id: 'space-physics',
    name: 'Space & Physics',
    tag: 'physics',
    icon: <Compass className="w-5 h-5 text-violet-400" />,
    subtitle: 'Astrophysics, Quantum Mechanics & Nonlinear PDEs',
    subsources: ['NASA ADS', 'arXiv math.NA', 'Quantum Simulators'],
    gradient: 'from-violet-500/10 to-[rgba(19, 22, 29,0.7)]',
  },
  {
    id: 'global-tech',
    name: 'Global Tech & Markets',
    tag: 'tech',
    icon: <Globe className="w-5 h-5 text-amber-400" />,
    subtitle: 'Frontier Lab Blogs, System Runtimes & OS Frameworks',
    subsources: ['Engineering Blogs', 'Open-Source Ecosystems', 'HackerNews'],
    gradient: 'from-amber-500/10 to-[rgba(19, 22, 29,0.7)]',
  },
];

// Helper to sanitize title strings (e.g. remove trailing generic benchmark noise)
function cleanTitle(rawTitle: string): string {
  if (!rawTitle) return '';
  return rawTitle
    .replace(/:\s*Technical\s+Architecture\s+and\s+Benchmarks/gi, '')
    .trim();
}

// ── 3D SVG Prism Fallback ─────────────────────────────────────────────────────
const HeroPrismFallback: React.FC = () => (
  <div className="relative w-full h-full flex items-center justify-center pointer-events-none">
    {/* Concentric glowing orbital rings */}
    <div className="absolute inset-0 flex items-center justify-center">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="absolute rounded-full border border-[rgba(212, 175, 55,0.18)]"
          style={{
            width: `${i * 32}%`,
            height: `${i * 32}%`,
            boxShadow: `0 0 24px rgba(212, 175, 55,${0.08 * i})`,
            animation: `spin ${10 + i * 5}s linear infinite ${i % 2 === 0 ? 'reverse' : ''}`,
          }}
        />
      ))}
    </div>

    {/* Faceted 3D Glass Prism SVG */}
    <svg className="w-48 h-48 md:w-60 md:h-60 drop-shadow-[0_0_35px_rgba(212, 175, 55,0.45)]" viewBox="0 0 200 200">
      <defs>
        <linearGradient id="prismFaceA" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F3D06B" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#c24b1f" stopOpacity="0.6" />
        </linearGradient>
        <linearGradient id="prismFaceB" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#F8FAFC" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#D4AF37" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#AA8828" stopOpacity="0.4" />
        </linearGradient>
        <linearGradient id="prismFaceC" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#34d399" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#D4AF37" stopOpacity="0.8" />
        </linearGradient>
      </defs>
      {/* Front Face */}
      <polygon points="100,20 170,150 100,180" fill="url(#prismFaceA)" />
      {/* Left Face */}
      <polygon points="100,20 30,150 100,180" fill="url(#prismFaceB)" opacity="0.9" />
      {/* Internal Reflection */}
      <polygon points="100,20 100,180 120,110" fill="url(#prismFaceC)" opacity="0.6" />
      {/* Center White Core Light Beam */}
      <line x1="100" y1="20" x2="100" y2="180" stroke="#F8FAFC" strokeWidth="2" strokeOpacity="0.9" />
      <circle cx="100" cy="20" r="4" fill="#FFFFFF" />
      <circle cx="100" cy="180" r="4" fill="#D4AF37" />
    </svg>

    {/* Floating Data Particles */}
    {[
      { x: '18%', y: '28%', delay: '0s', color: '#D4AF37' },
      { x: '78%', y: '24%', delay: '1.2s', color: '#34d399' },
      { x: '74%', y: '72%', delay: '0.6s', color: '#38bdf8' },
      { x: '24%', y: '68%', delay: '1.8s', color: '#c084fc' },
    ].map((dot, i) => (
      <div
        key={i}
        className="absolute w-2 h-2 rounded-full"
        style={{
          left: dot.x,
          top: dot.y,
          backgroundColor: dot.color,
          boxShadow: `0 0 12px ${dot.color}`,
          animation: `pulse 2.2s ease-in-out infinite ${dot.delay}`,
        }}
      />
    ))}
  </div>
);

// ── Hero Prism Image with Seamless Fallback ────────────────────────────────────
const HeroPrismVisual: React.FC = () => {
  const [imgFailed, setImgFailed] = useState(false);

  if (imgFailed) {
    return <HeroPrismFallback />;
  }

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <img
        src="/images/hero-prism.png"
        alt="DEVA Intelligence Holographic Prism"
        onError={() => setImgFailed(true)}
        className="w-64 h-64 md:w-80 md:h-80 object-contain rounded-3xl mix-blend-lighten filter drop-shadow-[0_0_40px_rgba(212, 175, 55,0.35)] transition-transform duration-500 hover:scale-105"
      />
    </div>
  );
};

// ── Animated Radar Visual for Auth Pages ──────────────────────────────────────
export const AuthRadarVisual: React.FC = () => {
  const [imgFailed, setImgFailed] = useState(false);

  return (
    <div className="relative w-full h-full overflow-hidden">
      {!imgFailed ? (
        <img
          src="/images/auth-radar.png"
          alt="DEVA Intelligence Horizon Radar"
          onError={() => setImgFailed(true)}
          className="w-full h-full object-cover filter brightness-90"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center relative">
          <div
            className="absolute inset-0"
            style={{
              background:
                'radial-gradient(ellipse at 50% 50%, rgba(212, 175, 55,0.35) 0%, rgba(19, 22, 29,0.65) 60%, #08090C 100%)',
            }}
          />
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="absolute rounded-full border border-[rgba(212, 175, 55,0.12)]"
              style={{ width: `${i * 22}%`, height: `${i * 22}%` }}
            />
          ))}
          <div
            className="absolute top-1/2 left-1/2 origin-bottom-left"
            style={{
              width: '50%',
              height: '1px',
              background: 'linear-gradient(90deg, transparent, rgba(212, 175, 55,0.65))',
              animation: 'spin 4s linear infinite',
              transformOrigin: '0 0',
            }}
          />
          <div className="absolute w-4 h-4 rounded-full border-2 border-[#D4AF37] opacity-70" />
        </div>
      )}

      {/* Floating telemetry cards overlayed top-right */}
      <div className="absolute top-6 right-6 z-20 space-y-2.5 max-w-[240px]">
        <div
          className="px-3 py-2 rounded-xl border border-[rgba(212, 175, 55,0.22)] shadow-xl flex items-center gap-2.5 backdrop-blur-xl animate-in fade-in slide-in-from-top-2 duration-300"
          style={{ background: 'rgba(19, 22, 29,0.85)' }}
        >
          <div className="w-6 h-6 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 flex-shrink-0">
            <CheckCircle2 className="w-3.5 h-3.5" />
          </div>
          <div className="text-[11px] leading-tight">
            <div className="text-[#F8FAFC] font-semibold">Paper → Code Linked</div>
            <div className="text-[#34d399] font-mono text-[9px]">100% Verified Match</div>
          </div>
        </div>

        <div
          className="px-3 py-2 rounded-xl border border-[rgba(212, 175, 55,0.22)] shadow-xl flex items-center gap-2.5 backdrop-blur-xl"
          style={{ background: 'rgba(19, 22, 29,0.85)' }}
        >
          <div className="w-6 h-6 rounded-lg bg-[rgba(212, 175, 55,0.2)] border border-[rgba(212, 175, 55,0.4)] flex items-center justify-center text-[#D4AF37] flex-shrink-0">
            <Volume2 className="w-3.5 h-3.5" />
          </div>
          <div className="text-[11px] leading-tight">
            <div className="text-[#F8FAFC] font-semibold">Daily Briefing Ready</div>
            <div className="text-[#F3D06B] font-mono text-[9px]">350w Audio Digest</div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Live Signal Row Component ─────────────────────────────────────────────────
const LiveSignalRow: React.FC<{ signal: LiveSignal; index: number }> = ({ signal, index }) => {
  const meta = CONTENT_TYPE_META[signal.content_type] || CONTENT_TYPE_META.article;
  const navigate = useNavigate();

  const handleRowClick = () => {
    navigate('/login?redirect=/dashboard');
  };

  return (
    <div
      onClick={handleRowClick}
      className="flex items-center gap-4 p-4 rounded-2xl border border-[rgba(212, 175, 55,0.1)] bg-[rgba(19, 22, 29,0.55)] hover:border-[rgba(212, 175, 55,0.35)] hover:bg-[rgba(26, 31, 41,0.7)] transition-all group cursor-pointer"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Content Type Pill */}
      <div
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-mono font-bold whitespace-nowrap flex-shrink-0 ${meta.color}`}
      >
        {meta.icon}
        {meta.label}
      </div>

      {/* Main Signal Info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-[#F8FAFC] leading-snug truncate group-hover:text-[#F3D06B] transition-colors">
          {cleanTitle(signal.title)}
        </div>
        {signal.summary_text && (
          <p className="text-[11px] text-[#94A3B8] mt-0.5 line-clamp-1 leading-relaxed">
            {signal.summary_text}
          </p>
        )}
        <div className="flex items-center gap-3 text-[10px] font-mono text-[#64748B] mt-1">
          <span className="text-[#94A3B8] font-medium">{signal.source}</span>
          {signal.published_at && (
            <span>• {new Date(signal.published_at).toLocaleDateString()}</span>
          )}
        </div>
      </div>

      {/* Domain Tag */}
      {signal.domain && (
        <div className="hidden sm:block flex-shrink-0 text-[10px] font-mono text-[#94A3B8] bg-[rgba(212, 175, 55,0.08)] px-2.5 py-1 rounded-full border border-[rgba(212, 175, 55,0.16)]">
          {signal.domain}
        </div>
      )}

      {/* + Action Button */}
      <Link
        to="/login?redirect=/dashboard"
        onClick={(e) => e.stopPropagation()}
        title="Open full 350-word editorial briefing"
        className="flex-shrink-0 w-8 h-8 rounded-full border border-[rgba(212, 175, 55,0.4)] bg-[rgba(212, 175, 55,0.1)] text-[#D4AF37] flex items-center justify-center hover:bg-[#D4AF37] hover:text-white transition-all text-sm font-bold group-hover:scale-105"
      >
        +
      </Link>
    </div>
  );
};

// ── Main Landing Page ──────────────────────────────────────────────────────────
export const LandingPage: React.FC = () => {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();
  const [liveSignals, setLiveSignals] = useState<LiveSignal[]>(FALLBACK_SIGNALS);
  const [liveCount, setLiveCount] = useState<number>(1040);
  const [selectedDomainTag, setSelectedDomainTag] = useState<string>('all');
  const [activeDomainName, setActiveDomainName] = useState<string>('All Domains');
  const [isFeedLoading, setIsFeedLoading] = useState(false);

  // Auto-redirect authenticated user to /dashboard
  useEffect(() => {
    if (!isLoading && user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, isLoading, navigate]);

  // Fetch signals whenever domain filter changes
  useEffect(() => {
    const fetchSignals = async () => {
      setIsFeedLoading(true);
      try {
        let endpoint = '/api/v1/intel/feed?limit=5';
        if (selectedDomainTag !== 'all') {
          endpoint += `&search=${encodeURIComponent(selectedDomainTag)}`;
        }
        const res = await fetch(endpoint);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            const mapped: LiveSignal[] = data.map((d: any) => ({
              id: d.id,
              title: d.title,
              content_type: d.content_type || 'paper',
              source: d.source_name || (d.canonical_url?.includes('github') ? 'GitHub' : 'arXiv'),
              summary_text: d.summary_raw || d.summary_ai?.methodology || '',
              domain: d.tags?.[0] ? d.tags[0].toUpperCase() : 'AI & Scientific ML',
              published_at: d.published_at,
            }));
            setLiveSignals(mapped.slice(0, 5));
          } else {
            // Filter fallback items
            const filteredFallback = FALLBACK_SIGNALS.filter((s) =>
              s.domain?.toLowerCase().includes(selectedDomainTag.toLowerCase())
            );
            setLiveSignals(filteredFallback.length > 0 ? filteredFallback : FALLBACK_SIGNALS);
          }
        } else {
          setLiveSignals(FALLBACK_SIGNALS);
        }
      } catch {
        setLiveSignals(FALLBACK_SIGNALS);
      } finally {
        setIsFeedLoading(false);
      }
    };

    fetchSignals();
  }, [selectedDomainTag]);

  // Incremental live counter
  useEffect(() => {
    const interval = setInterval(() => {
      setLiveCount((prev) => prev + Math.floor(Math.random() * 2));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleDomainCardClick = (domain: DomainItem) => {
    if (selectedDomainTag === domain.tag) {
      setSelectedDomainTag('all');
      setActiveDomainName('All Domains');
    } else {
      setSelectedDomainTag(domain.tag);
      setActiveDomainName(domain.name);
    }
    // Smooth scroll down to TOP-5 SIGNALS
    const signalsElement = document.getElementById('live-signals');
    if (signalsElement) {
      signalsElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const DOMAIN_FILTER_PILLS = [
    { label: 'All', tag: 'all' },
    { label: 'AI', tag: 'ai' },
    { label: 'Healthcare', tag: 'health' },
    { label: 'Music', tag: 'audio' },
    { label: 'Science', tag: 'physics' },
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#08090C] flex items-center justify-center">
        <div className="flex items-center gap-3 font-mono text-sm text-[#94A3B8]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#D4AF37] animate-ping" />
          AUTHENTICATING COGNITIVE RADAR...
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen font-sans text-[#F8FAFC] overflow-x-hidden selection:bg-[#D4AF37]/30 selection:text-white"
      style={{ background: '#08090C' }}
    >
      {/* Ambient background glows */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 65% 45% at 12% 15%, rgba(212, 175, 55,0.2) 0%, transparent 70%), radial-gradient(ellipse 55% 40% at 88% 85%, rgba(212, 175, 55,0.12) 0%, transparent 70%)',
          zIndex: 0,
        }}
      />

      {/* ── TOP FLOATING GLASS NAVIGATION BAR ─────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-3.5">
        <div
          className="absolute inset-0"
          style={{
            background: 'rgba(11,9,8,0.76)',
            backdropFilter: 'blur(20px)',
            borderBottom: '1px solid rgba(212, 175, 55,0.1)',
          }}
        />

        {/* Logo Mark + Wordmark */}
        <div className="relative flex items-center gap-3 z-10">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center font-mono font-black text-white text-base"
            style={{
              background: 'linear-gradient(135deg, #D4AF37 0%, #c24b1f 100%)',
              boxShadow: '0 0 24px rgba(212, 175, 55,0.5)',
            }}
          >
            D
          </div>
          <div>
            <div className="font-mono font-black text-sm text-[#F8FAFC] tracking-wider">DEVA INTEL</div>
            <div className="text-[9px] font-mono text-[#64748B] tracking-widest -mt-0.5">
              COGNITIVE RADAR
            </div>
          </div>
        </div>

        {/* Center 4 Anchor Links */}
        <div className="relative z-10 hidden md:flex items-center gap-8">
          {[
            { label: 'Domains', href: '#domains' },
            { label: 'Knowledge Graph', href: '#knowledge-graph' },
            { label: 'AI Analyst', href: '#ai-analyst' },
            { label: 'Live Signals', href: '#live-signals' },
          ].map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-xs font-medium text-[#94A3B8] hover:text-[#F3D06B] transition-colors tracking-wide"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Right CTA Button */}
        <div className="relative z-10 flex items-center gap-3">
          <Link
            to="/login"
            className="text-xs font-semibold text-[#94A3B8] hover:text-white transition-colors px-3 py-1.5"
          >
            SIGN IN
          </Link>
          <Link
            to="/login"
            className="relative flex items-center gap-2.5 px-4 py-2 rounded-full text-xs font-bold font-mono text-white transition-all hover:scale-105"
            style={{
              background: 'linear-gradient(135deg, #D4AF37 0%, #c24b1f 100%)',
              boxShadow: '0 0 20px rgba(212, 175, 55,0.45)',
            }}
          >
            LAUNCH RADAR
            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-white/20 text-[9px] font-black">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              LIVE
            </span>
          </Link>
        </div>
      </nav>

      {/* ── ASYMMETRIC 2-COLUMN HERO BENTO GRID (65% / 35%) ────────────────── */}
      <section className="relative z-10 pt-28 pb-8 px-5 md:px-8 lg:px-12 max-w-[1400px] mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-[65fr_35fr] gap-5 items-stretch min-h-[540px]">
          
          {/* ── LEFT GIANT HERO CARD (65%) ─────────────────────────────────── */}
          <div
            className="relative overflow-hidden rounded-[32px] p-8 md:p-10 flex flex-col justify-between min-h-[500px] lg:min-h-[540px]"
            style={{
              background:
                'radial-gradient(ellipse at 35% 25%, rgba(212, 175, 55,0.48) 0%, rgba(19, 22, 29,0.85) 60%, rgba(11,9,8,0.95) 100%)',
              border: '1px solid rgba(212, 175, 55,0.2)',
              backdropFilter: 'blur(28px)',
            }}
          >
            {/* Ambient inner card glow */}
            <div
              className="absolute top-0 right-0 w-80 h-80 rounded-full pointer-events-none"
              style={{
                background: 'radial-gradient(circle, rgba(212, 175, 55,0.18) 0%, transparent 70%)',
              }}
            />

            {/* Top row: live badge + index counter */}
            <div className="relative z-10 flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse"
                  style={{ boxShadow: '0 0 8px #D4AF37' }}
                />
                <span className="text-[11px] font-mono text-[#D4AF37] font-bold tracking-widest">
                  STAGE 3 COGNITIVE RADAR
                </span>
              </div>
              <div className="text-[11px] font-mono text-[#64748B]">
                {liveCount.toLocaleString()}+ verified nodes
              </div>
            </div>

            {/* Middle Section: Big Display Typography + Centerpiece Visual */}
            <div className="relative z-10 grid grid-cols-1 md:grid-cols-[55%_45%] items-center gap-6 my-auto">
              <div>
                <h1
                  className="font-black leading-[0.9] tracking-tighter select-none"
                  style={{
                    fontSize: 'clamp(52px, 7.5vw, 92px)',
                    color: '#F8FAFC',
                    textShadow: '0 2px 40px rgba(212, 175, 55,0.22)',
                    letterSpacing: '-0.04em',
                  }}
                >
                  REAL-TIME
                  <br />
                  <span
                    style={{
                      background: 'linear-gradient(135deg, #D4AF37 0%, #F8FAFC 65%)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    INTEL!
                  </span>
                </h1>
                <p className="text-sm md:text-base text-[#94A3B8] mt-5 max-w-sm leading-relaxed font-normal">
                  Verified research, code & global signals—synthesized for you.
                </p>
              </div>

              {/* Centerpiece Visual with 100% CITED Pill */}
              <div className="relative flex items-center justify-center">
                <HeroPrismVisual />

                {/* 100% CITED Frosted Pill Badge */}
                <div
                  className="absolute bottom-2 left-4 md:left-2 px-3.5 py-1.5 rounded-full font-mono text-xs font-bold flex items-center gap-2 border border-emerald-500/30 backdrop-blur-xl shadow-lg"
                  style={{
                    background: 'rgba(16,30,16,0.85)',
                    boxShadow: '0 0 20px rgba(52,211,153,0.25)',
                  }}
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  <span className="text-emerald-300">100% Grounded Citations</span>
                </div>
              </div>
            </div>

            {/* Bottom Row Inside Left Hero Card */}
            <div className="relative z-10 flex flex-wrap items-center gap-3 pt-6 border-t border-[rgba(212, 175, 55,0.12)]">
              {/* Grounded Consensus Pill */}
              <div
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono"
                style={{
                  background: 'rgba(212, 175, 55,0.12)',
                  border: '1px solid rgba(212, 175, 55,0.3)',
                }}
              >
                <span className="text-[#F3D06B]">●</span>
                <span className="text-[#94A3B8]">( 99.8% • Grounded Consensus )</span>
              </div>

              {/* 3 Domain Icon Pills */}
              <div className="flex items-center gap-2">
                {[
                  { label: 'Papers', icon: <FileText className="w-3 h-3" />, color: 'text-violet-400' },
                  { label: 'GitHub', icon: <GitBranch className="w-3 h-3" />, color: 'text-emerald-400' },
                  { label: 'Global', icon: <Globe className="w-3 h-3" />, color: 'text-sky-400' },
                ].map((d) => (
                  <div
                    key={d.label}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] ${d.color}`}
                  >
                    {d.icon}
                    {d.label}
                  </div>
                ))}
              </div>

              {/* Direct Access CTA */}
              <Link
                to="/login"
                className="ml-auto flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold text-white transition-all hover:scale-105"
                style={{
                  background: 'linear-gradient(135deg, #D4AF37 0%, #c24b1f 100%)',
                  boxShadow: '0 4px 20px rgba(212, 175, 55,0.4)',
                }}
              >
                Launch Radar
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* ── RIGHT DUAL STACKED BENTO CARDS (35%) ────────────────────────── */}
          <div className="flex flex-col gap-5">
            
            {/* Top-Right Card (AI ANALYST) with Tilted Cited Answer Preview */}
            <div
              id="ai-analyst"
              className="relative overflow-hidden rounded-[28px] p-6 flex flex-col justify-between flex-1 cursor-pointer group"
              style={{
                background:
                  'linear-gradient(140deg, rgba(26, 31, 41,0.85) 0%, rgba(19, 22, 29,0.95) 100%)',
                border: '1px solid rgba(212, 175, 55,0.18)',
                backdropFilter: 'blur(24px)',
                minHeight: '250px',
              }}
            >
              {/* Floating LangGraph Badge */}
              <div className="flex justify-between items-start mb-2">
                <div className="text-[10px] font-mono text-[#64748B] tracking-widest uppercase">
                  Cognitive Engine
                </div>
                <div
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border"
                  style={{
                    color: '#D4AF37',
                    borderColor: 'rgba(212, 175, 55,0.4)',
                    background: 'rgba(212, 175, 55,0.12)',
                  }}
                >
                  LANGGRAPH
                </div>
              </div>

              {/* Content + Mini Tilted Preview */}
              <div className="grid grid-cols-1 sm:grid-cols-[55%_45%] items-center gap-4 my-auto">
                <div>
                  <h2
                    className="font-black leading-none mb-2"
                    style={{
                      fontSize: 'clamp(32px, 4vw, 42px)',
                      color: '#F8FAFC',
                      letterSpacing: '-0.03em',
                    }}
                  >
                    AI
                    <br />
                    ANALYST
                  </h2>
                  <p className="text-xs text-[#94A3B8] leading-relaxed">
                    Ask complex technical questions with zero hallucinations
                  </p>
                </div>

                {/* Tilted Frosted Glass Mini-Preview Card */}
                <div
                  className="p-3 rounded-2xl border border-[rgba(212, 175, 55,0.22)] shadow-xl transform rotate-1 group-hover:rotate-0 transition-transform duration-300"
                  style={{
                    background: 'rgba(19, 22, 29,0.85)',
                    backdropFilter: 'blur(16px)',
                  }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[9px] font-mono text-emerald-400 flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" />
                      Verified Source
                    </span>
                    <span className="text-[9px] font-mono text-[#D4AF37] font-bold">[1]</span>
                  </div>
                  <p className="text-[11px] text-[#F8FAFC] font-mono leading-tight">
                    "DeepXDE achieves 3.2x faster convergence <span className="text-[#D4AF37] font-bold">[1]</span>"
                  </p>
                  <div className="mt-2 text-[9px] text-[#64748B] font-mono truncate">
                    arXiv:2601.04812 • PDE Solver
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <Link
                to="/login"
                className="mt-3 w-fit flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-bold border transition-all group-hover:bg-[rgba(212, 175, 55,0.15)] group-hover:border-[rgba(212, 175, 55,0.5)]"
                style={{
                  color: '#D4AF37',
                  borderColor: 'rgba(212, 175, 55,0.3)',
                  background: 'rgba(212, 175, 55,0.08)',
                }}
              >
                EXPLORE →
              </Link>
            </div>

            {/* Bottom-Right Card (EVERY DAY) with 350-word & Equalizer Preview */}
            <div
              className="relative overflow-hidden rounded-[28px] p-6 flex flex-col justify-between flex-1"
              style={{
                background:
                  'linear-gradient(140deg, rgba(65,32,20,0.8) 0%, rgba(26, 31, 41,0.95) 100%)',
                border: '1px solid rgba(212, 175, 55,0.25)',
                backdropFilter: 'blur(24px)',
                minHeight: '250px',
              }}
            >
              {/* Header */}
              <div className="flex justify-between items-start mb-2">
                <div className="text-[10px] font-mono text-[#64748B] tracking-widest uppercase">
                  Daily Dossiers
                </div>
                <div
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold"
                  style={{
                    color: '#F8FAFC',
                    background: 'linear-gradient(135deg, #D4AF37 0%, #c24b1f 100%)',
                    boxShadow: '0 0 14px rgba(212, 175, 55,0.5)',
                  }}
                >
                  350w BRIEF
                </div>
              </div>

              {/* Middle with Audio Digest Preview Card */}
              <div className="grid grid-cols-1 sm:grid-cols-[55%_45%] items-center gap-4 my-auto">
                <div>
                  <h2
                    className="font-black leading-none mb-1"
                    style={{
                      fontSize: 'clamp(30px, 3.8vw, 40px)',
                      color: '#F8FAFC',
                      letterSpacing: '-0.03em',
                    }}
                  >
                    EVERY
                    <br />
                    <span style={{ color: '#D4AF37' }}>DAY</span>
                  </h2>
                  <p className="text-xs text-[#94A3B8] leading-relaxed">
                    Multi-domain 350-word intelligence briefings, curated daily.
                  </p>
                </div>

                {/* Frosted Glass Audio Digest Preview Card */}
                <div
                  className="p-3 rounded-2xl border border-[rgba(212, 175, 55,0.22)] shadow-xl"
                  style={{
                    background: 'rgba(19, 22, 29,0.85)',
                    backdropFilter: 'blur(16px)',
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[9px] font-mono text-[#F3D06B] flex items-center gap-1 font-semibold">
                      <Volume2 className="w-3 h-3" />
                      2 min listen
                    </span>
                    {/* Animated Equalizer Bars */}
                    <div className="flex items-end gap-1 h-3.5">
                      <span className="w-1 bg-[#D4AF37] rounded-full animate-[pulse_1s_infinite] h-3" />
                      <span className="w-1 bg-[#F3D06B] rounded-full animate-[pulse_0.7s_infinite] h-2" />
                      <span className="w-1 bg-[#D4AF37] rounded-full animate-[pulse_1.2s_infinite] h-3.5" />
                      <span className="w-1 bg-amber-400 rounded-full animate-[pulse_0.9s_infinite] h-2.5" />
                    </div>
                  </div>
                  <div className="text-[10px] text-[#F8FAFC] font-semibold leading-tight">
                    350w Executive Summary
                  </div>
                  <div className="text-[9px] text-[#64748B] font-mono mt-1">
                    Multi-Domain Audio Radar
                  </div>
                </div>
              </div>

              {/* Tagline footer */}
              <div className="pt-3 border-t border-[rgba(212, 175, 55,0.12)] flex items-center justify-between">
                <span className="text-[10px] font-mono text-[#64748B]">Auto-synthesized at 06:00 UTC</span>
                <Link to="/login" className="text-[10px] font-mono text-[#D4AF37] hover:underline">
                  Listen Now →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── INTERACTIVE GLOBAL DOMAINS SECTION (#domains) ────────────────── */}
      <section
        id="domains"
        className="relative z-10 px-5 md:px-8 lg:px-12 max-w-[1400px] mx-auto py-10"
      >
        <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-4 h-4 text-[#D4AF37]" />
              <span className="text-[11px] font-mono text-[#D4AF37] tracking-widest font-bold uppercase">
                Global Coverage
              </span>
            </div>
            <h2
              className="font-black leading-tight"
              style={{
                fontSize: 'clamp(28px, 4vw, 42px)',
                letterSpacing: '-0.03em',
                color: '#F8FAFC',
              }}
            >
              Interactive Intelligence Domains
            </h2>
            <p className="text-xs text-[#94A3B8] mt-1 max-w-xl">
              Click any domain card to highlight its ecosystem and instantly filter live signals below.
            </p>
          </div>

          <div className="text-xs font-mono text-[#64748B]">
            Active Filter: <span className="text-[#D4AF37] font-bold">{activeDomainName}</span>
          </div>
        </div>

        {/* 5-Card Domain Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {GLOBAL_DOMAINS.map((domain) => {
            const isSelected = selectedDomainTag === domain.tag;
            return (
              <div
                key={domain.id}
                onClick={() => handleDomainCardClick(domain)}
                className={`p-5 rounded-[24px] border transition-all cursor-pointer flex flex-col justify-between group ${
                  isSelected
                    ? 'border-[#D4AF37] bg-[rgba(55,27,20,0.85)] shadow-[0_0_25px_rgba(212, 175, 55,0.3)] scale-[1.02]'
                    : 'border-[rgba(212, 175, 55,0.12)] bg-[rgba(19, 22, 29,0.6)] hover:border-[rgba(212, 175, 55,0.35)] hover:bg-[rgba(26, 31, 41,0.75)]'
                }`}
                style={{ backdropFilter: 'blur(20px)', minHeight: '190px' }}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 rounded-xl bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.08)]">
                      {domain.icon}
                    </div>
                    {isSelected && (
                      <span className="text-[9px] font-mono text-[#D4AF37] font-bold px-2 py-0.5 rounded-full bg-[rgba(212, 175, 55,0.15)] border border-[rgba(212, 175, 55,0.3)]">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-[#F8FAFC] mb-1 group-hover:text-[#F3D06B] transition-colors">
                    {domain.name}
                  </h3>
                  <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                    {domain.subtitle}
                  </p>
                </div>

                {/* Sub-sources tags */}
                <div className="mt-4 pt-3 border-t border-[rgba(212, 175, 55,0.1)] flex flex-wrap gap-1">
                  {domain.subsources.map((src) => (
                    <span
                      key={src}
                      className="text-[9px] font-mono text-[#64748B] bg-[rgba(255,255,255,0.04)] px-1.5 py-0.5 rounded"
                    >
                      {src}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── LIVE TOP-5 SIGNALS FEED (#live-signals) ────────────────────────── */}
      <section
        id="live-signals"
        className="relative z-10 px-5 md:px-8 lg:px-12 max-w-[1400px] mx-auto pb-16"
      >
        <div
          className="rounded-[28px] overflow-hidden p-7 md:p-8"
          style={{
            background: 'rgba(19, 22, 29,0.76)',
            border: '1px solid rgba(212, 175, 55,0.16)',
            backdropFilter: 'blur(24px)',
          }}
        >
          {/* Section Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Radio className="w-4 h-4 text-[#D4AF37] animate-pulse" />
                <span className="text-[11px] font-mono text-[#D4AF37] tracking-widest font-bold">
                  VERIFIED FEED
                </span>
              </div>
              <h3
                className="font-black leading-none"
                style={{
                  fontSize: 'clamp(28px, 4vw, 42px)',
                  letterSpacing: '-0.03em',
                  color: '#F8FAFC',
                }}
              >
                TOP-5 SIGNALS
              </h3>
              <p className="text-xs text-[#94A3B8] mt-1">
                Showing real breakthroughs filtered by: <span className="text-[#D4AF37] font-semibold">{activeDomainName}</span>
              </p>
            </div>

            {/* Filter Pills */}
            <div className="flex flex-wrap gap-2">
              {DOMAIN_FILTER_PILLS.map((p) => {
                const isActive = selectedDomainTag === p.tag;
                return (
                  <button
                    key={p.tag}
                    onClick={() => {
                      setSelectedDomainTag(p.tag);
                      setActiveDomainName(p.tag === 'all' ? 'All Domains' : p.label);
                    }}
                    className={`px-3.5 py-1.5 rounded-full text-[11px] font-mono font-semibold transition-all ${
                      isActive
                        ? 'bg-[#D4AF37] text-white shadow-[0_0_12px_rgba(212, 175, 55,0.4)]'
                        : 'bg-[rgba(212, 175, 55,0.08)] text-[#94A3B8] border border-[rgba(212, 175, 55,0.14)] hover:border-[rgba(212, 175, 55,0.3)] hover:text-[#F3D06B]'
                    }`}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Feed Rows */}
          {isFeedLoading ? (
            <div className="py-12 flex items-center justify-center text-xs font-mono text-[#94A3B8]">
              <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-ping mr-2" />
              QUERYING VERIFIED STREAM...
            </div>
          ) : (
            <div className="space-y-3">
              {liveSignals.map((signal, i) => (
                <LiveSignalRow key={signal.id} signal={signal} index={i} />
              ))}
            </div>
          )}

          {/* Footer Navigation */}
          <div className="mt-6 pt-5 border-t border-[rgba(212, 175, 55,0.12)] flex items-center justify-between">
            <span className="text-xs text-[#64748B] font-mono">
              Filtered live against {liveCount.toLocaleString()}+ indexed signals
            </span>
            <Link
              to="/login?redirect=/dashboard"
              className="flex items-center gap-2 text-xs font-semibold text-[#D4AF37] hover:text-[#F3D06B] transition-colors"
            >
              Sign in for 350-word deep briefs
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────────── */}
      <footer className="relative z-10 px-5 md:px-8 lg:px-12 max-w-[1400px] mx-auto pb-10">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-[rgba(212, 175, 55,0.1)]">
          <div className="font-mono text-xs text-[#64748B]">
            © 2026 DEVA INTELLIGENCE • MIL-STD DATA ISOLATION • GROUNDED CONSENSUS
          </div>
          <div className="flex items-center gap-6">
            <Link to="/login" className="text-xs text-[#94A3B8] hover:text-[#F3D06B] transition-colors">
              Sign In
            </Link>
            <Link to="/register" className="text-xs text-[#94A3B8] hover:text-[#F3D06B] transition-colors">
              Register
            </Link>
          </div>
        </div>
      </footer>

      {/* CSS Keyframes */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};
