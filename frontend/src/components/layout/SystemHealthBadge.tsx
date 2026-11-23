import React, { useState } from 'react';
import { useSystemReadiness } from '../../api/health';
import { Activity, Database, Layers, Cpu, AlertCircle, ChevronDown, CheckCircle2 } from 'lucide-react';

export const SystemHealthBadge: React.FC = () => {
  const { data, isLoading, isError } = useSystemReadiness();
  const [isOpen, setIsOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center space-x-2 text-[11px] font-mono text-[#94A3B8] bg-[rgba(19, 22, 29,0.65)] px-2.5 py-1 rounded-lg border border-[rgba(212, 175, 55,0.12)]">
        <span className="w-1.5 h-1.5 rounded-full bg-[#D4AF37] animate-pulse"></span>
        <span>Probing Cluster...</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex items-center space-x-1.5 text-[11px] font-mono text-rose-300 bg-rose-950/40 px-2.5 py-1 rounded-lg border border-rose-500/30">
        <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
        <span>System Degraded</span>
      </div>
    );
  }

  const { postgres, redis, celery } = data.components;
  const isHealthy = data.status === 'healthy';
  const avgLatency = Math.round(
    (postgres.latency_ms + redis.latency_ms + (celery.latency_ms || 0)) / 3
  );

  return (
    <div className="relative">
      {/* Consolidated Interactive Glass Pill */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[rgba(19, 22, 29,0.7)] backdrop-blur-md border border-[rgba(212, 175, 55,0.16)] hover:border-[#D4AF37]/60 hover:shadow-[0_0_15px_rgba(212, 175, 55,0.2)] text-xs font-mono transition-all group"
        title="Click to view detailed system telemetry"
      >
        <span className="relative flex h-2 w-2">
          {isHealthy && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          )}
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${
              isHealthy ? 'bg-emerald-400' : 'bg-[#D4AF37]'
            }`}
          ></span>
        </span>
        <span className="text-[#F8FAFC] font-medium group-hover:text-white">
          {isHealthy ? 'All Systems Operational' : 'Cluster Degraded'}
        </span>
        <span className="text-[10px] text-[#F3D06B] font-mono font-semibold">
          • {avgLatency}ms
        </span>
        <ChevronDown className="w-3 h-3 text-[#94A3B8] group-hover:text-[#D4AF37] transition-transform" />
      </button>

      {/* Popover Breakdown */}
      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-72 bg-[#10131A]/96 backdrop-blur-2xl border border-[rgba(212, 175, 55,0.22)] shadow-[0_24px_60px_rgba(0,0,0,0.85)] rounded-xl p-3.5 z-50 space-y-2.5 animate-in fade-in zoom-in-95 duration-150"
          onMouseLeave={() => setIsOpen(false)}
        >
          <div className="flex items-center justify-between pb-2 border-b border-[rgba(212, 175, 55,0.12)] text-[11px] font-mono text-[#94A3B8]">
            <span>INFRASTRUCTURE HEALTH</span>
            <span className="text-emerald-400 flex items-center gap-1 font-semibold">
              <CheckCircle2 className="w-3 h-3" /> Live
            </span>
          </div>

          <div className="space-y-1.5 text-xs font-mono">
            {/* API Gateway */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-[rgba(212, 175, 55,0.12)] border border-[rgba(212, 175, 55,0.08)]">
              <div className="flex items-center gap-2 text-[#F8FAFC]">
                <Activity className="w-3.5 h-3.5 text-[#D4AF37]" />
                <span>API Gateway</span>
              </div>
              <span className="text-emerald-400 text-[10px] font-semibold">Active</span>
            </div>

            {/* Postgres / pgvector */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-[rgba(212, 175, 55,0.12)] border border-[rgba(212, 175, 55,0.08)]">
              <div className="flex items-center gap-2 text-[#F8FAFC]">
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                <span>Postgres & pgvector</span>
              </div>
              <span className="text-[#94A3B8] text-[10px]">{postgres.latency_ms}ms</span>
            </div>

            {/* Redis Cache */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-[rgba(212, 175, 55,0.12)] border border-[rgba(212, 175, 55,0.08)]">
              <div className="flex items-center gap-2 text-[#F8FAFC]">
                <Layers className="w-3.5 h-3.5 text-amber-400" />
                <span>Redis L2 Cache</span>
              </div>
              <span className="text-[#94A3B8] text-[10px]">{redis.latency_ms}ms</span>
            </div>

            {/* Celery Asynchronous Workers */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-[rgba(212, 175, 55,0.12)] border border-[rgba(212, 175, 55,0.08)]">
              <div className="flex items-center gap-2 text-[#F8FAFC]">
                <Cpu className="w-3.5 h-3.5 text-[#D4AF37]" />
                <span>Celery Workers</span>
              </div>
              <span
                className={`text-[10px] font-semibold ${
                  celery.status === 'healthy' ? 'text-emerald-400' : 'text-[#D4AF37]'
                }`}
              >
                {celery.latency_ms ? `${celery.latency_ms}ms` : celery.status}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
