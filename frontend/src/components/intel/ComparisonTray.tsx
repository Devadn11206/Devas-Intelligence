import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useComparison } from '../../lib/comparison';
import { Columns, X, Trash2, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';

export const ComparisonTray: React.FC = () => {
  const { selectedDocs, toggleSelectDoc, clearSelection, setIsModalOpen } = useComparison();
  const [isMinimized, setIsMinimized] = useState(false);
  const location = useLocation();

  // Hide entirely on /analyst so it never covers the chat input bar or controls
  if (location.pathname === '/analyst') return null;

  if (selectedDocs.length === 0) return null;

  const canCompare = selectedDocs.length >= 2;

  // Minimized pill toggle
  if (isMinimized) {
    return (
      <div className="fixed bottom-5 right-6 z-40 animate-in slide-in-from-bottom duration-200">
        <button
          onClick={() => setIsMinimized(false)}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl glass-panel-elevated border border-[rgba(212,175,55,0.3)] shadow-2xl text-xs font-mono text-[#F8FAFC] hover:border-[#D4AF37] transition bg-[rgba(19,22,29,0.95)]"
        >
          <Columns className="w-3.5 h-3.5 text-[#D4AF37]" />
          <span>Comparing ({selectedDocs.length}/4)</span>
          <ChevronUp className="w-3.5 h-3.5 text-[#F3D06B]" />
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-40 w-11/12 max-w-3xl glass-panel-elevated border border-[rgba(212,175,55,0.25)] shadow-2xl rounded-2xl p-3.5 backdrop-blur-2xl animate-in slide-in-from-bottom duration-200 bg-[rgba(19,22,29,0.95)]">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Left: Selected Document Pills */}
        <div className="flex items-center space-x-2 overflow-x-auto max-w-full pb-1 sm:pb-0">
          <div className="flex items-center space-x-1.5 text-xs font-mono font-semibold text-[#D4AF37] shrink-0 mr-1">
            <Columns className="w-4 h-4" />
            <span>Compare ({selectedDocs.length}/4):</span>
          </div>

          <div className="flex items-center space-x-1.5">
            {selectedDocs.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-[rgba(10,12,16,0.7)] border border-[rgba(212,175,55,0.18)] text-xs font-mono text-[#F8FAFC] shrink-0"
              >
                <span className="max-w-[130px] truncate">{doc.title}</span>
                <button
                  onClick={() => toggleSelectDoc(doc)}
                  className="text-[#64748B] hover:text-[#D4AF37] transition"
                  title="Remove from comparison"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1.5 rounded-lg text-[#64748B] hover:text-[#F8FAFC] hover:bg-white/[0.08] text-xs font-mono transition"
            title="Minimize tray"
          >
            <ChevronDown className="w-4 h-4" />
          </button>

          <button
            onClick={clearSelection}
            className="p-1.5 rounded-lg text-[#64748B] hover:text-rose-400 hover:bg-white/[0.08] text-xs font-mono transition"
            title="Clear comparison selection"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            disabled={!canCompare}
            className={`flex items-center space-x-1.5 px-4 py-1.5 rounded-xl text-xs font-mono font-semibold transition ${
              canCompare
                ? 'btn-gold-glow cursor-pointer'
                : 'bg-white/[0.04] text-[#64748B] border border-white/10 cursor-not-allowed'
            }`}
          >
            <span>Compare Matrix</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
