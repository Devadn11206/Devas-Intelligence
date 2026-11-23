import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import {
  LayoutDashboard,
  Newspaper,
  BookOpen,
  GitBranch,
  Wrench,
  TrendingUp,
  Brain,
  FileSpreadsheet,
  Bookmark,
  ChevronDown,
  ChevronRight,
  Shield,
  Radio,
  Workflow,
  Bot,
  Activity,
  Terminal,
  Sliders,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  badge?: string;
}

interface SidebarProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const [isAdminOpen, setIsAdminOpen] = useState(true);
  const { isAdmin } = useAuth();

  const intelligenceNav: NavItem[] = [
    { name: 'Overview', path: '/dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { name: 'AI Analyst', path: '/analyst', icon: <Brain className="w-4 h-4" /> },
    { name: 'Explore Trends', path: '/trends', icon: <TrendingUp className="w-4 h-4" /> },
    { name: 'Reports', path: '/reports', icon: <FileSpreadsheet className="w-4 h-4" /> },
  ];

  const exploreDomainsNav: NavItem[] = [
    { name: 'Research Papers', path: '/papers', icon: <BookOpen className="w-4 h-4" /> },
    { name: 'GitHub Code', path: '/github', icon: <GitBranch className="w-4 h-4" /> },
    { name: 'AI Tools & Models', path: '/tools', icon: <Wrench className="w-4 h-4" /> },
    { name: 'Global News', path: '/news', icon: <Newspaper className="w-4 h-4" /> },
  ];

  const personalNav: NavItem[] = [
    { name: 'Bookmarks', path: '/bookmarks', icon: <Bookmark className="w-4 h-4" /> },
    { name: 'Preferences', path: '/preferences', icon: <Sliders className="w-4 h-4" /> },
  ];

  const adminNav: NavItem[] = [
    { name: 'Admin Overview', path: '/admin', icon: <Shield className="w-4 h-4" /> },
    { name: 'Sources', path: '/admin/sources', icon: <Radio className="w-4 h-4" /> },
    { name: 'Ingestion Jobs', path: '/admin/jobs', icon: <Workflow className="w-4 h-4" /> },
    { name: 'Agent Runs', path: '/admin/agents', icon: <Bot className="w-4 h-4" /> },
    { name: 'System Health', path: '/admin/health', icon: <Activity className="w-4 h-4" /> },
  ];

  const renderNavGroup = (title: string, items: NavItem[]) => (
    <div>
      {!isCollapsed && (
        <div className="px-3 text-[10px] font-mono uppercase tracking-wider text-[#64748B] mb-1.5 font-semibold">
          {title}
        </div>
      )}
      <nav className="space-y-0.5">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            title={isCollapsed ? item.name : undefined}
            className={({ isActive }) =>
              `flex items-center ${
                isCollapsed ? 'justify-center px-2 py-2.5' : 'justify-between px-3 py-2'
              } rounded-lg text-xs font-medium transition-all group ${
                isActive
                  ? 'bg-[rgba(212, 175, 55,0.28)] text-[#F8FAFC] font-semibold border-l-2 border-[#D4AF37] shadow-[0_0_15px_rgba(212, 175, 55,0.15)]'
                  : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[rgba(212, 175, 55,0.06)]'
              }`
            }
          >
            <div className={`flex items-center ${isCollapsed ? '' : 'space-x-2.5'}`}>
              <span className="text-[#64748B] group-hover:text-[#D4AF37] transition-colors">
                {item.icon}
              </span>
              {!isCollapsed && <span>{item.name}</span>}
            </div>
            {!isCollapsed && item.badge && (
              <span className="text-[9px] px-1.5 py-0.5 rounded pill-terracotta font-mono font-semibold">
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );

  return (
    <aside
      className={`${
        isCollapsed ? 'w-16' : 'w-64'
      } glass-panel border-r border-[rgba(212, 175, 55,0.12)] flex flex-col h-screen select-none transition-all duration-200 ease-in-out z-20`}
    >
      {/* Brand / Logo + Rail Collapse Button */}
      <div className="p-3.5 border-b border-[rgba(212, 175, 55,0.12)] flex items-center justify-between">
        <div className="flex items-center space-x-2.5 overflow-hidden">
          <div className="w-7 h-7 rounded-lg btn-gold-glow flex items-center justify-center font-mono font-bold text-white text-sm flex-shrink-0">
            D
          </div>
          {!isCollapsed && (
            <div className="min-w-0">
              <div className="font-mono font-bold text-xs tracking-wider text-[#F8FAFC] flex items-center gap-1.5">
                <span>DEVA</span>
                <span className="text-[9px] px-1.5 py-0.2 pill-terracotta rounded font-semibold">
                  INTEL
                </span>
              </div>
              <div className="text-[9px] text-[#64748B] font-mono tracking-tight truncate">
                LUMINOUS RADAR • v2.1
              </div>
            </div>
          )}
        </div>

        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="p-1 rounded text-[#64748B] hover:text-[#D4AF37] hover:bg-[rgba(212, 175, 55,0.08)] transition"
            title={isCollapsed ? 'Expand Sidebar' : 'Collapse to Icon Rail'}
          >
            {isCollapsed ? (
              <PanelLeft className="w-3.5 h-3.5" />
            ) : (
              <PanelLeftClose className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto px-2.5 py-4 space-y-5">
        {renderNavGroup('INTELLIGENCE', intelligenceNav)}
        {renderNavGroup('EXPLORE DOMAINS', exploreDomainsNav)}
        {renderNavGroup('PERSONAL', personalNav)}

        {/* Collapsible Admin Console Section */}
        {isAdmin && (
          <div>
            {!isCollapsed ? (
              <button
                onClick={() => setIsAdminOpen(!isAdminOpen)}
                className="w-full flex items-center justify-between px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-[#64748B] hover:text-[#94A3B8] transition-colors"
              >
                <div className="flex items-center space-x-1.5 font-semibold">
                  <Terminal className="w-3 h-3 text-[#D4AF37]" />
                  <span>ADMIN CONSOLE</span>
                </div>
                {isAdminOpen ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
              </button>
            ) : (
              <div className="h-px bg-[rgba(212, 175, 55,0.12)] my-2" />
            )}

            {(isAdminOpen || isCollapsed) && (
              <nav className="mt-1 space-y-0.5">
                {adminNav.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    title={isCollapsed ? item.name : undefined}
                    className={({ isActive }) =>
                      `flex items-center ${
                        isCollapsed ? 'justify-center px-2 py-2' : 'space-x-2.5 px-3 py-1.5'
                      } rounded-lg text-xs font-medium transition-all group ${
                        isActive
                          ? 'bg-[rgba(212, 175, 55,0.28)] text-[#F8FAFC] font-semibold border-l-2 border-[#D4AF37]'
                          : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[rgba(212, 175, 55,0.06)]'
                      }`
                    }
                  >
                    <span className="text-[#64748B] group-hover:text-[#D4AF37] transition-colors">
                      {item.icon}
                    </span>
                    {!isCollapsed && <span>{item.name}</span>}
                  </NavLink>
                ))}
              </nav>
            )}
          </div>
        )}
      </div>

      {/* Footer Profile & Build Status */}
      <div className="p-3 border-t border-[rgba(212, 175, 55,0.12)] bg-[rgba(10, 12, 16,0.6)]">
        <div className="flex items-center justify-between text-[11px] font-mono text-[#64748B]">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] animate-pulse"></span>
            {!isCollapsed && <span className="text-[#94A3B8]">Radar Active</span>}
          </div>
          {!isCollapsed && <span className="text-[10px] text-[#64748B]">v2.1</span>}
        </div>
      </div>
    </aside>
  );
};
