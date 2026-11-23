import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { Lock, Mail, Eye, EyeOff, AlertCircle, ArrowRight, FileText, GitBranch, Radio } from 'lucide-react';
import { AuthRadarVisual } from '../public/LandingPage';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const redirectTarget = params.get('redirect') || (location.state as any)?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate(redirectTarget === '/' ? '/dashboard' : redirectTarget, { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      await login('admin@devaintelligence.local', 'Admin@Deva2026!');
      navigate(redirectTarget === '/' ? '/dashboard' : redirectTarget, { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Demo login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 font-sans"
      style={{
        background: '#08090C',
        backgroundImage:
          'radial-gradient(ellipse 60% 40% at 10% 15%, rgba(212, 175, 55,0.18) 0%, transparent 70%), radial-gradient(ellipse 50% 35% at 90% 85%, rgba(212, 175, 55,0.10) 0%, transparent 70%)',
      }}
    >
      {/* Back to home */}
      <Link
        to="/"
        className="fixed top-6 left-6 z-50 flex items-center gap-2 text-xs font-mono text-[#64748B] hover:text-[#F3D06B] transition-colors"
      >
        ← DEVA INTEL
      </Link>

      {/* Main framed container */}
      <div
        className="w-full max-w-5xl rounded-[32px] overflow-hidden shadow-2xl"
        style={{ border: '1px solid rgba(212, 175, 55,0.16)', background: 'rgba(11,9,8,0.4)' }}
      >
        <div className="grid grid-cols-1 md:grid-cols-[46%_54%] min-h-[600px]">
          {/* ── LEFT FORM COLUMN (46%) ───────────────────────────────── */}
          <div
            className="flex flex-col justify-center p-10 md:p-12"
            style={{
              background: 'rgba(19, 22, 29,0.92)',
              backdropFilter: 'blur(28px)',
            }}
          >
            {/* Logo */}
            <div className="flex items-center gap-3 mb-8">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center font-mono font-black text-white text-lg"
                style={{
                  background: 'linear-gradient(135deg, #D4AF37 0%, #c24b1f 100%)',
                  boxShadow: '0 0 24px rgba(212, 175, 55,0.5)',
                }}
              >
                D
              </div>
              <span className="font-mono font-black text-sm text-[#F8FAFC] tracking-widest">DEVA</span>
            </div>

            {/* Heading */}
            <div className="mb-7">
              <h1 className="text-2xl font-extrabold text-[#F8FAFC] tracking-tight leading-snug mb-2">
                Let's Decode the Future!
              </h1>
              <p className="text-xs text-[#94A3B8] leading-relaxed max-w-[280px]">
                Track breakthroughs across research, code, and global industries in real time.
              </p>
            </div>

            {/* Error banner */}
            {error && (
              <div className="mb-5 p-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-[11px] font-mono uppercase tracking-wider text-[#94A3B8] mb-1.5 font-semibold">
                  Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[#64748B] absolute left-3.5 top-3" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="analyst@company.com"
                    className="w-full bg-[rgba(10, 12, 16,0.9)] border border-[rgba(212, 175, 55,0.16)] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] focus:ring-1 focus:ring-[#D4AF37]/30 transition-colors"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-[11px] font-mono uppercase tracking-wider text-[#94A3B8] mb-1.5 font-semibold">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#64748B] absolute left-3.5 top-3" />
                  <input
                    type={showPw ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[rgba(10, 12, 16,0.9)] border border-[rgba(212, 175, 55,0.16)] rounded-xl pl-10 pr-11 py-2.5 text-sm text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] focus:ring-1 focus:ring-[#D4AF37]/30 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(!showPw)}
                    className="absolute right-3.5 top-2.5 text-[#64748B] hover:text-[#94A3B8] transition-colors"
                  >
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Primary CTA */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 mt-2"
                style={{
                  background: loading
                    ? 'rgba(212, 175, 55,0.4)'
                    : 'linear-gradient(135deg, #D4AF37 0%, #c24b1f 100%)',
                  boxShadow: loading ? 'none' : '0 4px 20px rgba(212, 175, 55,0.4)',
                  color: 'white',
                }}
              >
                {loading ? 'Authenticating...' : (
                  <>Sign In <ArrowRight className="w-4 h-4" /></>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="my-5 flex items-center gap-3">
              <div className="flex-1 h-px bg-[rgba(212, 175, 55,0.14)]" />
              <span className="text-[11px] font-mono text-[#64748B]">or quick access</span>
              <div className="flex-1 h-px bg-[rgba(212, 175, 55,0.14)]" />
            </div>

            {/* One-Click Admin Demo button */}
            <button
              onClick={handleDemoLogin}
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 border border-[rgba(212, 175, 55,0.2)] text-[#94A3B8] hover:border-[#D4AF37] hover:text-[#F3D06B] hover:bg-[rgba(212, 175, 55,0.08)]"
              style={{ background: 'rgba(19, 22, 29,0.6)' }}
            >
              ⚡ One-Click Admin Demo
            </button>

            {/* Switcher */}
            <div className="mt-6 text-center text-xs text-[#94A3B8]">
              Don't have an account?{' '}
              <Link to="/register" className="text-[#D4AF37] hover:text-[#F3D06B] font-semibold underline underline-offset-4">
                Register
              </Link>
            </div>
          </div>

          {/* ── RIGHT VISUAL COLUMN (54%) ─────────────────────────────── */}
          <div className="relative hidden md:block overflow-hidden min-h-[600px]">
            {/* Visual with fallback + floating telemetry cards */}
            <div className="absolute inset-0">
              <AuthRadarVisual />
            </div>

            {/* Bottom Warm Obsidian-to-Gold Gradient Overlay */}
            <div
              className="absolute inset-x-0 bottom-0 h-3/4 flex flex-col justify-end p-10 z-10"
              style={{
                background:
                  'linear-gradient(to top, rgba(11,9,8,0.98) 0%, rgba(19, 22, 29,0.85) 45%, rgba(19, 22, 29,0.3) 75%, transparent 100%)',
              }}
            >
              <h2 className="text-2xl font-black text-[#F8FAFC] leading-tight mb-3 tracking-tight">
                Catch Every<br />Breakthrough First
              </h2>
              <p className="text-xs text-[#94A3B8] leading-relaxed mb-6 max-w-sm">
                Connect arXiv papers, GitHub implementations, and global domain intelligence with verified citations and 350-word daily briefings.
              </p>

              {/* Overlapping Avatar Stack with Fixed Spacing */}
              <div className="flex items-center">
                <div className="flex items-center -space-x-2">
                  {[
                    { bg: 'bg-violet-600', label: 'arXiv' },
                    { bg: 'bg-emerald-600', label: 'GH' },
                    { bg: 'bg-sky-600', label: 'HF' },
                    { bg: 'bg-amber-600', label: 'bio' },
                  ].map((av, i) => (
                    <div
                      key={i}
                      className={`w-8 h-8 rounded-full ${av.bg} ring-2 ring-[#140F0D] flex items-center justify-center text-white text-[10px] font-bold shadow-md`}
                    >
                      {av.label}
                    </div>
                  ))}
                  <div className="w-8 h-8 rounded-full bg-[rgba(212, 175, 55,0.35)] ring-2 ring-[#140F0D] flex items-center justify-center text-[#F3D06B] text-[10px] font-bold shadow-md">
                    +99
                  </div>
                </div>

                {/* 1,040+ Live Indexed Signals Pill with explicit ml-3 */}
                <div
                  className="ml-3 flex items-center gap-2 px-3 py-1.5 rounded-xl backdrop-blur-md"
                  style={{
                    background: 'rgba(19, 22, 29,0.85)',
                    border: '1px solid rgba(212, 175, 55,0.35)',
                  }}
                >
                  <Radio className="w-3.5 h-3.5 text-[#D4AF37] animate-pulse" />
                  <span className="text-xs font-mono text-[#F8FAFC] font-semibold whitespace-nowrap">
                    1,040+ Live Indexed Signals
                  </span>
                </div>
              </div>

              {/* Three Mini Feature Pills */}
              <div className="flex flex-wrap gap-2 mt-5">
                {[
                  { icon: <FileText className="w-3 h-3" />, label: 'arXiv Papers', color: 'text-violet-400' },
                  { icon: <GitBranch className="w-3 h-3" />, label: 'GitHub Repos', color: 'text-emerald-400' },
                  { icon: <Radio className="w-3 h-3" />, label: 'Live Signals', color: 'text-[#D4AF37]' },
                ].map((pill) => (
                  <div
                    key={pill.label}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] ${pill.color}`}
                  >
                    {pill.icon}
                    {pill.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
