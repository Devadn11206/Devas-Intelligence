import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ProtectedRoute } from './components/common/ProtectedRoute';

// Public Pages
import { LandingPage } from './pages/public/LandingPage';

// Primary Pages
import { OverviewPage } from './pages/primary/Overview';
import { TrendsPage } from './pages/primary/Trends';
import {
  NewsPage,
  PapersPage,
  GitHubPage,
  ToolsPage,
} from './pages/primary/Placeholders';
import { AnalystPage } from './pages/primary/Analyst';
import { ReportsPage } from './pages/primary/Reports';
import { PreferencesPage } from './pages/primary/Preferences';
import { BookmarksPage } from './pages/primary/Bookmarks';
import { GraphExplorerPage } from './pages/primary/GraphExplorer';
import { SearchPage } from './pages/primary/Search';

// Auth Pages
import { LoginPage } from './pages/auth/Login';
import { RegisterPage } from './pages/auth/Register';

// Admin Pages
import { AdminOverviewPage } from './pages/admin/AdminOverview';
import { AgentRunsPage } from './pages/admin/AgentRuns';
import { SystemHealthAdminPage } from './pages/admin/SystemHealth';
import { SourcesPage } from './pages/admin/Sources';
import { IngestionJobsPage } from './pages/admin/IngestionJobs';

/** Wraps a page inside AppShell for protected, app-shell-framed routes */
const AppPage: React.FC<{ children: React.ReactNode; requireAdmin?: boolean }> = ({
  children,
  requireAdmin = false,
}) => (
  <ProtectedRoute requireAdmin={requireAdmin}>
    <AppShell>{children}</AppShell>
  </ProtectedRoute>
);

export const App: React.FC = () => {
  return (
    <Routes>
      {/* ── Public Routes (no AppShell) ──────────────────────────────────── */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* ── Protected App Routes (inside AppShell) ───────────────────────── */}
      <Route path="/dashboard" element={<AppPage><OverviewPage /></AppPage>} />
      <Route path="/news"      element={<AppPage><NewsPage /></AppPage>} />
      <Route path="/papers"    element={<AppPage><PapersPage /></AppPage>} />
      <Route path="/github"    element={<AppPage><GitHubPage /></AppPage>} />
      <Route path="/tools"     element={<AppPage><ToolsPage /></AppPage>} />
      <Route path="/trends"    element={<AppPage><TrendsPage /></AppPage>} />
      <Route path="/analyst"   element={<AppPage><AnalystPage /></AppPage>} />
      <Route path="/reports"   element={<AppPage><ReportsPage /></AppPage>} />
      <Route path="/search"    element={<AppPage><SearchPage /></AppPage>} />
      <Route path="/bookmarks" element={<AppPage><BookmarksPage /></AppPage>} />
      <Route path="/preferences" element={<AppPage><PreferencesPage /></AppPage>} />
      <Route
        path="/explorer/:documentId"
        element={<AppPage><GraphExplorerPage /></AppPage>}
      />

      {/* ── Admin Console (RBAC: platform_admin / super_admin) ──────────── */}
      <Route path="/admin"         element={<AppPage requireAdmin><AdminOverviewPage /></AppPage>} />
      <Route path="/admin/sources" element={<AppPage requireAdmin><SourcesPage /></AppPage>} />
      <Route path="/admin/jobs"    element={<AppPage requireAdmin><IngestionJobsPage /></AppPage>} />
      <Route path="/admin/agents"  element={<AppPage requireAdmin><AgentRunsPage /></AppPage>} />
      <Route path="/admin/health"  element={<AppPage requireAdmin><SystemHealthAdminPage /></AppPage>} />

      {/* ── Fallback ─────────────────────────────────────────────────────── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
