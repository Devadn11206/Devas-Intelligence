import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  ListMusic,
  ChevronDown,
  Check,
  Headphones,
  FileText,
  Code2,
  Cpu,
  Newspaper,
} from 'lucide-react';
import { IntelFeedCard } from './IntelCard';

interface AudioDigestBarProps {
  cards: IntelFeedCard[];
  onSelectDocument: (docId: string) => void;
}

export const AudioDigestBar: React.FC<AudioDigestBarProps> = ({
  cards,
  onSelectDocument,
}) => {
  const topStories = cards.slice(0, 5);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState<number>(1.0);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceURI, setSelectedVoiceURI] = useState<string>('');
  const [isVoiceDropdownOpen, setIsVoiceDropdownOpen] = useState(false);
  const [isQueueOpen, setIsQueueOpen] = useState(false);
  const [progressPercent, setProgressPercent] = useState<number>(0);

  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const currentCard = topStories[currentIndex] || cards[0];
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsVoiceDropdownOpen(false);
        setIsQueueOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Populate Speech Synthesis Voices
  useEffect(() => {
    if (!('speechSynthesis' in window)) return;

    const populateVoices = () => {
      const available = window.speechSynthesis.getVoices();
      if (!available || available.length === 0) return;

      const englishVoices = available.filter(
        (v) => v.lang.startsWith('en') || v.lang.includes('US') || v.lang.includes('GB')
      );
      const voicePool = englishVoices.length > 0 ? englishVoices : available;
      setVoices(voicePool);

      const naturalVoice = voicePool.find(
        (v) =>
          v.name.includes('Natural') ||
          v.name.includes('Neural') ||
          v.name.includes('Google') ||
          v.name.includes('Aria') ||
          v.name.includes('Guy') ||
          v.name.includes('Jenny')
      );

      if (naturalVoice && !selectedVoiceURI) {
        setSelectedVoiceURI(naturalVoice.voiceURI);
      } else if (!selectedVoiceURI && voicePool[0]) {
        setSelectedVoiceURI(voicePool[0].voiceURI);
      }
    };

    populateVoices();
    window.speechSynthesis.onvoiceschanged = populateVoices;

    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [selectedVoiceURI]);

  // Clean and prepare spoken executive anchor script
  const buildSpokenScript = (card: IntelFeedCard, index: number, total: number) => {
    if (!card) return '';
    const cleanTitle = (card.title || '')
      .replace(/\[\d+\]/g, '')
      .replace(/http\S+/g, '')
      .trim();

    const summaryText =
      card.summary_ai?.problem_statement ||
      card.summary_ai?.key_findings ||
      card.summary_raw ||
      '';

    const cleanSummary = summaryText
      .replace(/https?:\/\/\S+/g, '')
      .replace(/arXiv:\S+/g, '')
      .replace(/[*#_~`]/g, '')
      .trim();

    return `Briefing ${index + 1} of ${total}. From ${card.source_name || 'Global Radar'}. ${cleanTitle}. ${cleanSummary}`;
  };

  const playStory = (index: number, rate: number = playbackRate) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    const targetCard = topStories[index];
    if (!targetCard) return;

    const script = buildSpokenScript(targetCard, index, topStories.length);
    const utterance = new SpeechSynthesisUtterance(script);

    utterance.rate = rate;
    utterance.pitch = 1.0;

    if (selectedVoiceURI) {
      const voiceObj = voices.find((v) => v.voiceURI === selectedVoiceURI);
      if (voiceObj) utterance.voice = voiceObj;
    }

    utterance.onboundary = (e) => {
      if (script.length > 0 && e.charIndex) {
        const pct = Math.min(100, Math.round((e.charIndex / script.length) * 100));
        setProgressPercent(pct);
      }
    };

    utterance.onend = () => {
      setProgressPercent(100);
      if (index < topStories.length - 1) {
        setCurrentIndex(index + 1);
        setTimeout(() => {
          playStory(index + 1, rate);
        }, 500);
      } else {
        setIsPlaying(false);
        setProgressPercent(0);
      }
    };

    utterance.onerror = () => {
      setIsPlaying(false);
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    setCurrentIndex(index);
    setIsPlaying(true);
    setProgressPercent(5);
  };

  const togglePlay = () => {
    if (!('speechSynthesis' in window)) return;

    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
    } else {
      playStory(currentIndex, playbackRate);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      const prev = currentIndex - 1;
      setCurrentIndex(prev);
      if (isPlaying) {
        playStory(prev, playbackRate);
      }
    }
  };

  const handleNext = () => {
    if (currentIndex < topStories.length - 1) {
      const next = currentIndex + 1;
      setCurrentIndex(next);
      if (isPlaying) {
        playStory(next, playbackRate);
      }
    }
  };

  const cyclePlaybackRate = () => {
    const rates = [1.0, 1.25, 1.5];
    const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
    const nextRate = rates[nextIdx];
    setPlaybackRate(nextRate);
    if (isPlaying) {
      playStory(currentIndex, nextRate);
    }
  };

  const handleSelectVoice = (voiceURI: string) => {
    setSelectedVoiceURI(voiceURI);
    setIsVoiceDropdownOpen(false);
    if (isPlaying) {
      playStory(currentIndex, playbackRate);
    }
  };

  if (!currentCard) return null;

  const getBadgeIcon = (contentType: string) => {
    switch (contentType) {
      case 'paper':
        return <FileText className="w-3 h-3 text-[#60A5FA]" />;
      case 'repo':
        return <Code2 className="w-3 h-3 text-emerald-400" />;
      case 'model':
        return <Cpu className="w-3 h-3 text-[#F3D06B]" />;
      default:
        return <Newspaper className="w-3 h-3 text-[#D4AF37]" />;
    }
  };

  const selectedVoice = voices.find((v) => v.voiceURI === selectedVoiceURI);

  return (
    <div
      ref={dropdownRef}
      className="relative p-3.5 rounded-2xl border border-[rgba(212,175,55,0.2)] bg-[rgba(15,18,24,0.92)] backdrop-blur-2xl shadow-2xl transition-all z-20"
    >
      {/* Bottom Border Glowing Progress Bar */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[rgba(212,175,55,0.12)] rounded-b-2xl overflow-hidden pointer-events-none">
        <div
          className="h-full bg-gradient-to-r from-[#D4AF37] via-[#F3D06B] to-[#E5C158] shadow-[0_0_10px_#D4AF37] transition-all duration-300"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Left: Player Controls & Equalizer */}
        <div className="flex items-center space-x-2.5 shrink-0">
          {/* Previous Story */}
          <button
            onClick={handlePrev}
            disabled={currentIndex === 0}
            className="p-1.5 text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/[0.06] rounded-lg transition disabled:opacity-30 disabled:hover:bg-transparent"
            title="Previous story"
          >
            <SkipBack className="w-4 h-4" />
          </button>

          {/* Glowing Circular Play/Pause */}
          <button
            onClick={togglePlay}
            className="w-9 h-9 rounded-full btn-gold-glow flex items-center justify-center text-[#08090C] transition hover:scale-105 shadow-lg shrink-0"
            title={isPlaying ? 'Pause Digest' : 'Play 3-Min Executive Briefing'}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4 ml-0.5" />
            )}
          </button>

          {/* Next Story */}
          <button
            onClick={handleNext}
            disabled={currentIndex === topStories.length - 1}
            className="p-1.5 text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/[0.06] rounded-lg transition disabled:opacity-30 disabled:hover:bg-transparent"
            title="Next story"
          >
            <SkipForward className="w-4 h-4" />
          </button>

          {/* Pattern 07: Speed Pill Toggle */}
          <button
            onClick={cyclePlaybackRate}
            className="px-2 py-0.5 rounded-lg bg-[rgba(10,12,16,0.7)] border border-[rgba(212,175,55,0.2)] hover:border-[#D4AF37] text-[11px] font-mono text-[#F3D06B] font-semibold transition"
            title="Click to toggle playback speed (1.0x -> 1.25x -> 1.5x)"
          >
            {playbackRate.toFixed(2).replace('.00', '')}x
          </button>

          {/* 5-Bar Animated Equalizer */}
          <div className="flex items-center space-x-1.5 pl-1">
            <span className="text-[10px] font-mono text-[#D4AF37] font-bold uppercase tracking-wider">
              BRIEFING {currentIndex + 1} OF {topStories.length}
            </span>
            {isPlaying ? (
              <div className="flex items-end space-x-0.5 h-3.5">
                <span className="w-0.5 h-2 bg-[#D4AF37] animate-pulse rounded-full" />
                <span className="w-0.5 h-3.5 bg-[#F3D06B] animate-pulse delay-75 rounded-full" />
                <span className="w-0.5 h-1.5 bg-[#D4AF37] animate-pulse delay-150 rounded-full" />
                <span className="w-0.5 h-3 bg-[#E5C158] animate-pulse delay-100 rounded-full" />
                <span className="w-0.5 h-2.5 bg-[#D4AF37] animate-pulse delay-200 rounded-full" />
              </div>
            ) : (
              <div className="flex items-end space-x-0.5 h-3.5 opacity-40">
                <span className="w-0.5 h-1.5 bg-[#64748B] rounded-full" />
                <span className="w-0.5 h-1.5 bg-[#64748B] rounded-full" />
                <span className="w-0.5 h-1.5 bg-[#64748B] rounded-full" />
                <span className="w-0.5 h-1.5 bg-[#64748B] rounded-full" />
                <span className="w-0.5 h-1.5 bg-[#64748B] rounded-full" />
              </div>
            )}
          </div>
        </div>

        {/* Center: Clickable Track Title */}
        <div
          onClick={() => onSelectDocument(currentCard.primary_document_id)}
          className="flex-1 min-w-0 mx-2 cursor-pointer group flex items-center gap-1.5"
          title="Click to open 350-Word Executive Briefing Drawer"
        >
          <span className="text-xs font-semibold text-[#F8FAFC] group-hover:text-[#F3D06B] truncate transition-colors">
            {currentCard.title}
          </span>
          <span className="text-[10px] font-mono text-[#64748B] group-hover:text-[#F3D06B] shrink-0 transition-colors">
            • {currentCard.source_name}
          </span>
        </div>

        {/* Right: Voice Selector & 5-Story Queue Toggle */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* Voice Selector Pill */}
          {voices.length > 0 && (
            <div className="relative">
              <button
                onClick={() => {
                  setIsVoiceDropdownOpen(!isVoiceDropdownOpen);
                  setIsQueueOpen(false);
                }}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-[rgba(10,12,16,0.7)] border border-[rgba(212,175,55,0.18)] text-[10px] font-mono text-[#94A3B8] hover:text-[#F8FAFC] hover:border-[#D4AF37]/50 transition"
                title="Change TTS voice"
              >
                <Volume2 className="w-3 h-3 text-[#D4AF37]" />
                <span className="max-w-[70px] truncate">
                  {selectedVoice ? selectedVoice.name.replace(/Microsoft |Google |English \(United States\)/g, '').trim() : 'Voice'}
                </span>
                <ChevronDown className="w-2.5 h-2.5 opacity-60" />
              </button>

              {/* Voice Popover */}
              {isVoiceDropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-[#10131A]/98 backdrop-blur-2xl border border-[rgba(212,175,55,0.25)] shadow-[0_20px_50px_rgba(0,0,0,0.85)] rounded-xl p-2 z-50 space-y-1 max-h-56 overflow-y-auto animate-in fade-in zoom-in-95 duration-150">
                  <div className="text-[10px] font-mono text-[#64748B] px-2 py-1 uppercase border-b border-[rgba(212,175,55,0.12)]">
                    Available TTS Voices
                  </div>
                  {voices.map((v) => {
                    const isSelected = v.voiceURI === selectedVoiceURI;
                    return (
                      <button
                        key={v.voiceURI}
                        onClick={() => handleSelectVoice(v.voiceURI)}
                        className={`w-full text-left px-2 py-1.5 rounded-lg text-xs font-mono flex items-center justify-between transition ${
                          isSelected
                            ? 'bg-[rgba(212,175,55,0.2)] text-[#F3D06B] font-semibold'
                            : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-white/[0.04]'
                        }`}
                      >
                        <span className="truncate pr-2">{v.name}</span>
                        {isSelected && <Check className="w-3 h-3 text-[#D4AF37] shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Interactive Queue Popover Button */}
          <div className="relative">
            <button
              onClick={() => {
                setIsQueueOpen(!isQueueOpen);
                setIsVoiceDropdownOpen(false);
              }}
              className="flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-[rgba(10,12,16,0.7)] border border-[rgba(212,175,55,0.2)] hover:border-[#D4AF37] text-xs font-mono text-[#F8FAFC] transition group"
              title="View and jump to queued briefings"
            >
              <ListMusic className="w-3.5 h-3.5 text-[#D4AF37]" />
              <span>Queue ({topStories.length})</span>
              <ChevronDown
                className={`w-3 h-3 text-[#94A3B8] group-hover:text-[#D4AF37] transition-transform ${
                  isQueueOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {/* Expandable 5-Story Playlist Popover */}
            {isQueueOpen && (
              <div className="absolute right-0 mt-2 w-88 bg-[#10131A]/98 backdrop-blur-2xl border border-[rgba(212,175,55,0.25)] shadow-[0_24px_60px_rgba(0,0,0,0.85)] rounded-2xl p-3 z-50 space-y-2 animate-in fade-in zoom-in-95 duration-150">
                <div className="flex items-center justify-between pb-2 border-b border-[rgba(212,175,55,0.12)]">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-[#F8FAFC]">
                    <Headphones className="w-3.5 h-3.5 text-[#D4AF37]" />
                    <span>Executive AI Audio Queue</span>
                  </div>
                  <span className="text-[10px] font-mono text-[#64748B]">~3 min total</span>
                </div>

                <div className="space-y-1.5 max-h-72 overflow-y-auto pr-0.5">
                  {topStories.map((story, sIdx) => {
                    const isStoryActive = sIdx === currentIndex;
                    return (
                      <div
                        key={story.id}
                        onClick={() => {
                          playStory(sIdx, playbackRate);
                          setIsQueueOpen(false);
                        }}
                        className={`p-2.5 rounded-xl cursor-pointer transition flex items-center justify-between border ${
                          isStoryActive
                            ? 'bg-[rgba(212,175,55,0.18)] border-[#D4AF37]/60 shadow-[0_0_12px_rgba(212,175,55,0.15)]'
                            : 'bg-[rgba(15,18,24,0.6)] border-[rgba(212,175,55,0.1)] hover:border-[rgba(212,175,55,0.28)] hover:bg-[rgba(26,31,41,0.7)]'
                        }`}
                      >
                        <div className="space-y-1 max-w-[80%]">
                          <div className="flex items-center space-x-1.5 text-[10px] font-mono">
                            <span className="flex items-center gap-1 text-[#F3D06B]">
                              {getBadgeIcon(story.content_type)}
                              <span className="uppercase">{story.content_type}</span>
                            </span>
                            <span className="text-[#64748B]">•</span>
                            <span className="text-[#94A3B8] truncate max-w-[120px]">{story.source_name}</span>
                          </div>
                          <div
                            className={`text-xs font-semibold line-clamp-1 ${
                              isStoryActive ? 'text-[#F3D06B]' : 'text-[#F8FAFC]'
                            }`}
                          >
                            {story.title}
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          {isStoryActive && isPlaying ? (
                            <div className="flex items-end space-x-0.5 h-3">
                              <span className="w-0.5 h-2 bg-[#D4AF37] animate-pulse rounded-full" />
                              <span className="w-0.5 h-3 bg-[#F3D06B] animate-pulse delay-75 rounded-full" />
                              <span className="w-0.5 h-1.5 bg-[#D4AF37] animate-pulse delay-150 rounded-full" />
                            </div>
                          ) : (
                            <span className="text-[10px] font-mono text-[#64748B]">~35s</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
