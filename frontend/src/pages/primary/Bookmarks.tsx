import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { Bookmark as BookmarkIcon, Trash2, Filter, Columns } from 'lucide-react';
import { useComparison } from '../../lib/comparison';

interface BookmarkItem {
  id: string;
  user_id: string;
  entity_type: 'paper' | 'repo' | 'model' | 'article' | 'tool';
  entity_id: string;
  notes?: string | null;
  created_at: string;
}

export const BookmarksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string>('all');
  const { toggleSelectDoc, isSelected } = useComparison();

  const { data: bookmarks, isLoading } = useQuery<BookmarkItem[]>({
    queryKey: ['user', 'bookmarks'],
    queryFn: async () => {
      const resp = await apiClient.get<BookmarkItem[]>('/v1/users/me/bookmarks');
      return resp.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (bookmarkId: string) => {
      await apiClient.delete(`/v1/users/me/bookmarks/${bookmarkId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user', 'bookmarks'] });
    },
  });

  const filteredBookmarks = bookmarks?.filter((b) => {
    if (activeTab === 'all') return true;
    return b.entity_type === activeTab;
  });

  const tabs = [
    { id: 'all', label: 'All Items' },
    { id: 'paper', label: 'Papers' },
    { id: 'repo', label: 'Repos' },
    { id: 'model', label: 'Models' },
    { id: 'article', label: 'Articles' },
    { id: 'tool', label: 'Tools' },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="glass-panel border border-[rgba(212, 175, 55,0.18)] rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-xs font-mono text-[#D4AF37]">
              <BookmarkIcon className="w-4 h-4" />
              <span>PRIVATE RESEARCH REPOSITORY</span>
            </div>
            <h1 className="text-2xl font-bold text-[#F8FAFC] tracking-tight">Saved Intelligence & Bookmarks</h1>
            <p className="text-xs text-[#94A3B8] font-mono">
              Enforced by PostgreSQL Row-Level Security in <code className="text-[#F3D06B]">tenant.bookmarks</code>
            </p>
          </div>
          <div className="glass-panel rounded-lg px-3.5 py-2 font-mono text-right text-xs">
            <span className="text-[#64748B]">Saved Records: </span>
            <span className="text-[#D4AF37] font-semibold">{bookmarks?.length || 0}</span>
          </div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800/80 pb-2">
        <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-md text-xs font-mono transition-colors ${
              activeTab === tab.id
                ? 'bg-cyan-950/60 border border-cyan-800/80 text-cyan-300 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Bookmarks List or Empty State */}
      {isLoading ? (
        <div className="text-center py-16 text-slate-400 font-mono text-xs">
          FETCHING BOOKMARKS UNDER CURRENT RLS CONTEXT...
        </div>
      ) : !filteredBookmarks || filteredBookmarks.length === 0 ? (
        <div className="bg-surface-card border border-slate-800/80 rounded-xl p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-surface-100 border border-slate-800 flex items-center justify-center mx-auto text-slate-400">
            <BookmarkIcon className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-white">No Bookmarks in This View</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Save papers, repositories, models, or intelligence briefs from any discovery feed. They will appear here under your private RLS encryption partition.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredBookmarks.map((bm) => (
            <div
              key={bm.id}
              className="bg-surface-card border border-slate-800/80 rounded-xl p-5 space-y-3 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/60 text-cyan-300 font-semibold">
                  {bm.entity_type}
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {new Date(bm.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="space-y-1">
                <div className="font-mono text-xs text-slate-300 font-semibold truncate">
                  ID: {bm.entity_id}
                </div>
                {bm.notes && <p className="text-xs text-slate-400 italic">"{bm.notes}"</p>}
              </div>

              <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs font-mono">
                <button
                  onClick={() => toggleSelectDoc({
                    id: bm.entity_id,
                    title: `Item ${bm.entity_id.slice(0, 8)}`,
                    content_type: bm.entity_type,
                  })}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded border transition ${
                    isSelected(bm.entity_id)
                      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/60'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <Columns className="w-3 h-3" />
                  <span>{isSelected(bm.entity_id) ? 'Selected' : 'Compare +'}</span>
                </button>

                <button
                  onClick={() => deleteMutation.mutate(bm.id)}
                  className="flex items-center gap-1 text-rose-400 hover:text-rose-300 transition-colors"
                  title="Remove bookmark"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Remove</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
