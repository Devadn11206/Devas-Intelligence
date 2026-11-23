import React from 'react';
import { Database, ArrowRight, ShieldCheck, Cpu, Code2 } from 'lucide-react';

interface PhasePlaceholderProps {
  title: string;
  moduleKey: string;
  phaseNumber: number;
  phaseName: string;
  responsibilities: string[];
  dataContracts: string[];
  techStack: string[];
}

export const PhasePlaceholder: React.FC<PhasePlaceholderProps> = ({
  title,
  moduleKey,
  phaseNumber,
  phaseName,
  responsibilities,
  dataContracts,
  techStack,
}) => {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-surface-card border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
        
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <span className="font-mono text-xs px-2.5 py-1 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800/60 font-semibold">
                PHASE {phaseNumber} TARGET
              </span>
              <span className="font-mono text-xs text-slate-400">
                domain: <code className="text-slate-300">app.modules.{moduleKey}</code>
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight pt-2">{title}</h1>
            <p className="text-sm text-slate-400 max-w-2xl">
              Foundation interface, schemas, and database migrations are provisioned. Execution logic is scheduled for implementation in <strong>{phaseName}</strong>.
            </p>
          </div>

          <div className="hidden md:flex flex-col items-end text-right font-mono text-xs">
            <span className="text-slate-400">Spec Status</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1.5 mt-0.5">
              <ShieldCheck className="w-4 h-4" /> Architectural Boundary Locked
            </span>
          </div>
        </div>
      </div>

      {/* Grid: Responsibilities & Data Contracts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Module Responsibilities */}
        <div className="bg-surface-card border border-slate-800/80 rounded-xl p-5 space-y-4">
          <div className="flex items-center space-x-2 text-sm font-semibold text-slate-200 border-b border-slate-800/60 pb-3">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>PRD Responsibilities</span>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-300">
            {responsibilities.map((resp, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <ArrowRight className="w-3.5 h-3.5 text-cyan-400 mt-0.5 flex-shrink-0" />
                <span className="leading-relaxed">{resp}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Data Contracts & Schemas */}
        <div className="bg-surface-card border border-slate-800/80 rounded-xl p-5 space-y-4">
          <div className="flex items-center space-x-2 text-sm font-semibold text-slate-200 border-b border-slate-800/60 pb-3">
            <Database className="w-4 h-4 text-emerald-400" />
            <span>Data Contracts & Schema Scope</span>
          </div>
          <div className="space-y-2 font-mono text-xs">
            {dataContracts.map((contract, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded bg-surface-100/40 border border-slate-800 text-slate-300 flex items-center justify-between"
              >
                <span>{contract}</span>
                <span className="text-[10px] text-slate-400 uppercase">Schema: intel</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tech Stack & Interfaces Footer */}
      <div className="bg-surface-card border border-slate-800/80 rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <Code2 className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-mono text-slate-400">Target Tech Stack:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech, idx) => (
            <span
              key={idx}
              className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800/70 text-cyan-300 border border-slate-700/60"
            >
              {tech}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
