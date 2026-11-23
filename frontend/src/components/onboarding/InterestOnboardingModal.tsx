import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  Compass,
  Check,
  ArrowRight,
  Brain,
  Activity,
  Music,
  Rocket,
  Search,
  Sparkles,
} from 'lucide-react';

interface DomainGroup {
  name: string;
  icon: React.ReactNode;
  topics: string[];
}

const DOMAIN_GROUPS: DomainGroup[] = [
  {
    name: 'Artificial Intelligence & Software',
    icon: <Brain className="w-4 h-4 text-[#D4AF37]" />,
    topics: [
      'AI & LLMs',
      'Scientific ML & PINNs',
      'Open-Source Code',
      'Agents & Automation',
      'Computer Vision',
    ],
  },
  {
    name: 'Healthcare & Biotech',
    icon: <Activity className="w-4 h-4 text-emerald-400" />,
    topics: [
      'Healthcare AI',
      'Drug Discovery',
      'Medical Imaging',
      'Genomics & Biotech',
      'Clinical Trials',
    ],
  },
  {
    name: 'Music, Audio & Entertainment',
    icon: <Music className="w-4 h-4 text-[#F3D06B]" />,
    topics: [
      'Music & Audio AI',
      'Film & Gaming Tech',
      'Media & Streaming',
      'Spatial Audio & VR',
    ],
  },
  {
    name: 'Science, Space & Engineering',
    icon: <Rocket className="w-4 h-4 text-amber-400" />,
    topics: [
      'Aerospace & Defense',
      'Physics & PDEs',
      'Autonomous Robotics',
      'Clean Tech & Energy',
    ],
  },
];

interface InterestOnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InterestOnboardingModal: React.FC<InterestOnboardingModalProps> = ({
  isOpen,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [selectedTopics, setSelectedTopics] = useState<string[]>([
    'AI & LLMs',
    'Open-Source Code',
    'Healthcare AI',
  ]);
  const [searchQuery, setSearchQuery] = useState('');

  const saveMutation = useMutation({
    mutationFn: async (topics: string[]) => {
      await apiClient.put('/v1/users/me/preferences', {
        followed_topics: topics,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my_preferences'] });
      queryClient.invalidateQueries({ queryKey: ['feed_for_you'] });
      onClose();
    },
  });

  if (!isOpen) return null;

  const toggleTopic = (topic: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const handleSave = () => {
    saveMutation.mutate(selectedTopics);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div className="max-w-2xl w-full glass-panel-elevated rounded-2xl p-6 shadow-2xl relative overflow-hidden flex flex-col max-h-[90vh]">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[rgba(212, 175, 55,0.08)] rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[rgba(212, 175, 55,0.12)]">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl btn-gold-glow flex items-center justify-center text-white">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[#F8FAFC] tracking-tight">
                Choose Your Intelligence Domains
              </h2>
              <p className="text-xs text-[#94A3B8] font-sans mt-0.5">
                Tailor your personal real-time radar feed, consensus alerts, and 3-minute daily audio briefing.
              </p>
            </div>
          </div>
        </div>

        {/* Search to filter chips */}
        <div className="my-4">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#64748B] absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search domains and technology chips..."
              className="w-full bg-[rgba(10, 12, 16,0.7)] border border-[rgba(212, 175, 55,0.16)] rounded-lg pl-9 pr-4 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-[#D4AF37] font-mono transition-colors"
            />
          </div>
        </div>

        {/* Domain Topics Grid */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {DOMAIN_GROUPS.map((group) => {
            const filteredTopics = group.topics.filter((t) =>
              t.toLowerCase().includes(searchQuery.toLowerCase())
            );
            if (filteredTopics.length === 0) return null;

            return (
              <div key={group.name} className="p-3.5 rounded-xl bg-[rgba(19, 22, 29,0.5)] border border-[rgba(212, 175, 55,0.1)] space-y-2.5">
                <div className="flex items-center space-x-2 text-xs font-semibold text-[#F8FAFC]">
                  {group.icon}
                  <span>{group.name}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {filteredTopics.map((topic) => {
                    const isSelected = selectedTopics.includes(topic);
                    return (
                      <button
                        key={topic}
                        onClick={() => toggleTopic(topic)}
                        className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                          isSelected
                            ? 'btn-gold-glow shadow-[0_0_12px_rgba(212, 175, 55,0.3)]'
                            : 'pill-terracotta hover:border-[#D4AF37]/50 hover:text-white'
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 text-white" />}
                        <span>{topic}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Live Counter & Save Footer */}
        <div className="mt-5 pt-4 border-t border-[rgba(212, 175, 55,0.12)] flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-mono text-[#F3D06B]">
            <Sparkles className="w-3.5 h-3.5 animate-pulse text-[#D4AF37]" />
            <span>
              {selectedTopics.length} interests selected — personalizing your radar
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs font-mono text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[rgba(212, 175, 55,0.08)] transition"
            >
              Skip for now
            </button>
            <button
              onClick={handleSave}
              disabled={saveMutation.isPending || selectedTopics.length === 0}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-lg btn-gold-glow font-mono text-xs font-semibold transition disabled:opacity-50"
            >
              <span>{saveMutation.isPending ? 'Configuring Radar...' : 'Launch Radar'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
