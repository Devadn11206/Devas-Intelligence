import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { Sidebar } from './Sidebar';
import { SystemHealthBadge } from './SystemHealthBadge';
import { CommandPalette } from '../search/CommandPalette';
import { DocumentDetailDrawer } from '../intel/DocumentDetailDrawer';
import { InterestOnboardingModal } from '../onboarding/InterestOnboardingModal';
import { ComparisonTray } from '../intel/ComparisonTray';
import { ComparisonModal } from '../intel/ComparisonModal';
import { useAuth } from '../../lib/auth';
import { Search, ChevronRight, LogOut, LogIn, Bell } from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, logout } = useAuth();
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [selectedDrawerDocId, setSelectedDrawerDocId] = useState<string | null>(null);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Notifications query
  const { data: notifications, refetch: refetchNotifications } = useQuery({
    queryKey: ['my_notifications'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/users/me/notifications');
      return res.data;
    },
    enabled: Boolean(user),
    refetchInterval: 30000,
  });

  const unreadCount = (notifications || []).filter((n: any) => !n.is_read).length;

  const handleMarkRead = async (notif: any) => {
    try {
      // Optimistic update
      queryClient.setQueryData(['my_notifications'], (old: any) =>
        Array.isArray(old) ? old.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n)) : []
      );
      await apiClient.patch(`/v1/users/me/notifications/${notif.id}/read`);
      refetchNotifications();
    } catch (err) {
      console.error('Failed to mark read', err);
    } finally {
      setIsNotificationsOpen(false);
      if (notif.document_id) {
        // If already on /dashboard, open drawer directly and update URL
        setSelectedDrawerDocId(notif.document_id);
        navigate(`/dashboard?doc=${notif.document_id}`);
      } else {
        navigate(`/dashboard?q=${encodeURIComponent(notif.title || '')}`);
      }
    }
  };

  const handleMarkAllRead = async () => {
    try {
      queryClient.setQueryData(['my_notifications'], (old: any) =>
        Array.isArray(old) ? old.map((n) => ({ ...n, is_read: true })) : []
      );
      await apiClient.patch('/v1/users/me/notifications/read-all');
      refetchNotifications();
    } catch (err) {
      console.error('Failed to mark all read', err);
    }
  };

  // Check if authenticated user has empty followed topics on initial login
  const { data: userPref } = useQuery({
    queryKey: ['my_preferences'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/users/me/preferences');
      return res.data;
    },
    enabled: Boolean(user),
  });

  useEffect(() => {
    if (userPref && (!userPref.followed_topics || userPref.followed_topics.length === 0)) {
      setIsOnboardingOpen(true);
    }
  }, [userPref]);

  // Global Ctrl+K / Cmd+K keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Generate readable breadcrumbs from path
  const pathSegments = location.pathname.split('/').filter(Boolean);
  const breadcrumb =
    pathSegments.length === 0 || (pathSegments.length === 1 && pathSegments[0] === 'dashboard')
      ? 'Overview'
      : pathSegments.map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join(' / ');

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#08090C] text-[#F8FAFC] font-sans">
      {/* Persistent Collapsible Sidebar */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
      />

      {/* Main App Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Decluttered Frosted Glass Top Header Bar */}
        <header className="h-14 border-b border-[rgba(212, 175, 55,0.12)] glass-panel px-5 flex items-center justify-between z-10">
          {/* Breadcrumb Path */}
          <div className="flex items-center space-x-2 text-xs font-mono text-[#94A3B8]">
            <span className="text-[#64748B] font-medium">DEVA</span>
            <ChevronRight className="w-3.5 h-3.5 text-[#64748B]" />
            <span className="text-[#D4AF37] font-semibold">{breadcrumb}</span>
          </div>

          {/* Center: Sleek Wide Command Palette Trigger with Champagne Gold Badge */}
          <div className="flex-1 max-w-lg mx-6">
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-lg bg-[rgba(19, 22, 29,0.7)] border border-[rgba(212, 175, 55,0.14)] text-[#94A3B8] text-xs font-mono hover:border-[#D4AF37]/50 hover:text-white transition group shadow-sm"
              title="Press Ctrl+K to open search"
            >
              <div className="flex items-center space-x-2.5">
                <Search className="w-3.5 h-3.5 text-[#D4AF37] group-hover:text-[#F3D06B] transition-colors" />
                <span className="text-[#94A3B8] group-hover:text-[#F8FAFC]">
                  Search papers, repos, models, or ask AI...
                </span>
              </div>
              <kbd className="text-[10px] bg-[rgba(212, 175, 55,0.25)] px-1.5 py-0.5 rounded border border-[rgba(212, 175, 55,0.25)] text-[#F3D06B] font-semibold">
                Ctrl+K
              </kbd>
            </button>
          </div>

          {/* Right: Consolidated Telemetry + Notifications + User Menu */}
          <div className="flex items-center space-x-3.5">
            <SystemHealthBadge />

            <div className="h-4 w-px bg-[rgba(212, 175, 55,0.14)]" />

            {user ? (
              <div className="flex items-center space-x-3">
                {/* Notification Bell Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                    className="relative p-1.5 rounded-lg text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[rgba(212, 175, 55,0.08)] transition"
                    title="Semantic Watchlist Alerts"
                  >
                    <Bell className="w-4 h-4" />
                    {unreadCount > 0 && (
                      <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-[#D4AF37] text-[10px] font-mono font-bold text-[#08090C] flex items-center justify-center shadow-[0_0_8px_#D4AF37] animate-pulse">
                        {unreadCount}
                      </span>
                    )}
                  </button>

                  {isNotificationsOpen && (
                    <div className="absolute right-0 mt-2 w-84 bg-[#10131A]/96 backdrop-blur-2xl border border-[rgba(212, 175, 55,0.22)] shadow-[0_24px_60px_rgba(0,0,0,0.85)] rounded-2xl p-3.5 z-50 space-y-2.5 animate-in fade-in zoom-in-95 duration-150">
                      <div className="flex items-center justify-between pb-2 border-b border-[rgba(212, 175, 55,0.12)]">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-[#F8FAFC]">Watchlist Alerts</span>
                          {unreadCount > 0 && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#D4AF37]/20 text-[#F3D06B] border border-[#D4AF37]/30 font-semibold">
                              {unreadCount} Unread
                            </span>
                          )}
                        </div>
                        {unreadCount > 0 && (
                          <button
                            onClick={handleMarkAllRead}
                            className="text-[10px] font-mono text-[#F3D06B] hover:text-[#F3D06B] underline underline-offset-2 transition font-medium"
                          >
                            Mark all read
                          </button>
                        )}
                      </div>
                      <div className="max-h-72 overflow-y-auto space-y-2 pr-0.5">
                        {!notifications || notifications.length === 0 ? (
                          <div className="text-center py-6 text-xs font-mono text-[#64748B] space-y-1">
                            <Bell className="w-5 h-5 mx-auto opacity-40 text-[#D4AF37]" />
                            <div>No notifications yet.</div>
                          </div>
                        ) : (
                          notifications.map((notif: any) => (
                            <div
                              key={notif.id}
                              onClick={() => handleMarkRead(notif)}
                              className={`p-2.5 rounded-xl cursor-pointer transition text-left group border ${
                                notif.is_read
                                  ? 'bg-[rgba(19, 22, 29,0.45)] border-[rgba(212, 175, 55,0.08)] opacity-65 hover:opacity-100 hover:border-[rgba(212, 175, 55,0.2)]'
                                  : 'bg-[rgba(212, 175, 55,0.22)] border-[rgba(212, 175, 55,0.25)] hover:border-[#D4AF37]/60 hover:bg-[rgba(212, 175, 55,0.32)] shadow-sm'
                              }`}
                            >
                              <div className="flex items-start justify-between gap-1.5">
                                <div className="text-xs font-bold text-[#F8FAFC] leading-snug group-hover:text-[#F3D06B] transition-colors">
                                  {notif.title}
                                </div>
                                {!notif.is_read && (
                                  <span className="w-2 h-2 rounded-full bg-[#D4AF37] shrink-0 mt-1" />
                                )}
                              </div>
                              <div className="text-[11px] text-[#94A3B8] line-clamp-2 mt-1 leading-relaxed">
                                {notif.message}
                              </div>
                              <div className="text-[10px] font-mono mt-2 pt-1.5 border-t border-[rgba(212, 175, 55,0.08)] flex items-center justify-between text-[#64748B]">
                                <span>{new Date(notif.created_at).toLocaleDateString()}</span>
                                <span className="text-[#D4AF37] flex items-center gap-1 group-hover:translate-x-0.5 transition-transform font-medium">
                                  <span>Inspect Briefing</span>
                                  <ChevronRight className="w-3 h-3" />
                                </span>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* User Profile Info & Logout */}
                <div className="flex items-center space-x-2 pl-2 border-l border-[rgba(212, 175, 55,0.14)]">
                  <div className="flex flex-col text-right">
                    <span className="text-xs font-medium text-[#F8FAFC] leading-tight">
                      {user.full_name}
                    </span>
                    <span className="text-[10px] font-mono text-[#D4AF37] leading-tight font-semibold">
                      {user.role}
                    </span>
                  </div>
                  <button
                    onClick={logout}
                    className="p-1.5 text-[#94A3B8] hover:text-rose-400 hover:bg-rose-950/40 rounded-lg transition"
                    title="Sign Out"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  to="/login"
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#94A3B8] hover:text-white hover:bg-[rgba(212, 175, 55,0.08)] transition"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Sign In</span>
                </Link>
                <Link
                  to="/register"
                  className="px-3.5 py-1.5 rounded-lg text-xs font-medium btn-gold-glow transition"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </header>

        {/* Content Body Viewport */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#08090C]">
          {children}
        </main>
      </div>

      {/* Global Command Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectDocument={(docId: string) => setSelectedDrawerDocId(docId)}
      />

      {/* Slide-in Document Intelligence Detail Drawer */}
      <DocumentDetailDrawer
        documentId={selectedDrawerDocId}
        onClose={() => setSelectedDrawerDocId(null)}
        onSelectSibling={(siblingId) => setSelectedDrawerDocId(siblingId)}
      />

      {/* First-Login Interest Onboarding Modal */}
      <InterestOnboardingModal
        isOpen={isOnboardingOpen}
        onClose={() => setIsOnboardingOpen(false)}
      />

      {/* Floating Multi-Item Comparison Tray */}
      <ComparisonTray />
      <ComparisonModal />
    </div>
  );
};
