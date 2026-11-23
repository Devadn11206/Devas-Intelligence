import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  X,
  FileText,
  Code2,
  Cpu,
  Newspaper,
  Wrench,
  ArrowRight,
  Sparkles,
  Command,
} from 'lucide-react';
import { apiClient } from '../../api/client';

interface SuggestionItem {
  id: string;
  title: string;
  content_type: string;
  tags: string[];
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDocument?: (documentId: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectDocument,
}) => {
  const [query, setQuery] = useState('');
  const [hasLinkedCode, setHasLinkedCode] = useState(false);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setSelectedType(null);
      setHasLinkedCode(false);
    }
  }, [isOpen]);

  const { data: suggestions, isLoading } = useQuery<SuggestionItem[]>({
    queryKey: ['search_suggestions', query],
    queryFn: async () => {
      if (!query.trim()) return [];
      const res = await apiClient.get<SuggestionItem[]>('/v1/search/suggest', {
        params: { q: query.trim(), limit: 6 },
      });
      return res.data;
    },
    enabled: isOpen && query.trim().length > 0,
  });

  if (!isOpen) return null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'Enter') {
      if (query.trim()) {
        onClose();
        const params = new URLSearchParams();
        params.set('q', query.trim());
        if (selectedType) params.set('type', selectedType);
        if (hasLinkedCode) params.set('has_code', 'true');
        navigate(`/search?${params.toString()}`);
      }
    }
  };

  const handleSelectSuggestion = (item: SuggestionItem) => {
    onClose();
    if (onSelectDocument) {
      onSelectDocument(item.id);
    } else {
      navigate(`/search?q=${encodeURIComponent(item.title)}`);
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
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-md flex items-start justify-center pt-20 px-4 animate-in fade-in duration-150">
      <div
        className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-slate-800 gap-3 bg-slate-950/60">
          <Search className="w-5 h-5 text-cyan-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search papers, code, models, concepts (e.g. 'LoRA diffusion', 'PINNs')..."
            className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded-md text-slate-400 hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            ESC
          </kbd>
        </div>

        {/* Quick Filter Chips */}
        <div className="flex flex-wrap items-center gap-1.5 px-4 py-2 border-b border-slate-800/80 bg-slate-900/60 text-xs">
          <span className="text-slate-400 text-[11px] font-mono mr-1">Filter:</span>
          {['paper', 'repo', 'model', 'article'].map((t) => (
            <button
              key={t}
              onClick={() => setSelectedType(selectedType === t ? null : t)}
              className={`px-2 py-0.5 rounded-full text-[11px] font-medium border transition ${
                selectedType === t
                  ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                  : 'bg-slate-800/60 text-slate-400 border-slate-700/50 hover:text-slate-200'
              }`}
            >
              {t === 'paper' ? 'Papers' : t === 'repo' ? 'Repositories' : t === 'model' ? 'Models' : 'Articles'}
            </button>
          ))}
          <button
            onClick={() => setHasLinkedCode(!hasLinkedCode)}
            className={`px-2 py-0.5 rounded-full text-[11px] font-medium border transition ${
              hasLinkedCode
                ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                : 'bg-slate-800/60 text-slate-400 border-slate-700/50 hover:text-slate-200'
            }`}
          >
            ⚡ Has Linked Code
          </button>
        </div>

        {/* Dynamic Suggestions List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {isLoading ? (
            <div className="py-8 text-center text-xs font-mono text-slate-500">
              Querying neural & lexical index...
            </div>
          ) : suggestions && suggestions.length > 0 ? (
            <div>
              <div className="text-[10px] uppercase font-mono text-slate-400 px-3 py-1 font-semibold">
                Instant Matches
              </div>
              {suggestions.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleSelectSuggestion(item)}
                  className="px-3 py-2 rounded-lg hover:bg-slate-800/80 cursor-pointer flex items-center justify-between group transition"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1 rounded bg-slate-800 border border-slate-700 shrink-0">
                      {getTypeIcon(item.content_type)}
                    </span>
                    <div className="truncate">
                      <div className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 truncate">
                        {item.title}
                      </div>
                      <div className="flex gap-1 text-[10px] text-slate-400">
                        {item.tags.slice(0, 3).map((tag, i) => (
                          <span key={i}>#{tag}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-cyan-400 transition" />
                </div>
              ))}
            </div>
          ) : query.trim() ? (
            <div
              onClick={() => {
                onClose();
                navigate(`/search?q=${encodeURIComponent(query.trim())}`);
              }}
              className="py-6 text-center text-xs text-slate-400 hover:text-cyan-300 cursor-pointer flex flex-col items-center gap-1"
            >
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Press <b>Enter</b> to launch full Hybrid Retrieval for "{query}"</span>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-slate-400 space-y-1">
              <div className="flex items-center justify-center gap-1.5 font-mono text-slate-400">
                <Command className="w-3.5 h-3.5 text-cyan-400" />
                <span>Global Command Palette</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Type keywords, technical terms, or authors to search across papers and code.
              </p>
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <div className="flex items-center gap-3">
            <span><b>Enter</b> to search</span>
            <span><b>ESC</b> to close</span>
          </div>
          <span className="text-cyan-400">RRF + BGE Cross-Encoder Reranker</span>
        </div>
      </div>
    </div>
  );
};
