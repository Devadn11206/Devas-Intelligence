import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  Cpu,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Terminal,
} from 'lucide-react';

interface AgentRun {
  id: string;
  workflow_type: string;
  query_or_topic: string;
  status: string;
  steps_executed: number;
  total_tokens: number;
  latency_ms: number;
  step_details: Array<Record<string, any>>;
  created_at: string;
}

export const AgentRunsPage: React.FC = () => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: runs = [], isLoading, refetch, isFetching } = useQuery<AgentRun[]>({
    queryKey: ['admin_agent_runs'],
    queryFn: async () => {
      const res = await apiClient.get('/v1/admin/agent-runs');
      return res.data;
    },
    refetchInterval: 20000,
  });

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto bg-background p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2.5">
            <Cpu className="w-6 h-6 text-purple-400" />
            <h1 className="text-xl font-bold text-white tracking-wide">Autonomous Agent Runs & LLM Telemetry</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Execution node graphs, token consumption, latency traces, and fact-check validation steps.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-surface-100 hover:bg-surface-200 border border-slate-800 text-xs font-mono text-slate-300 hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin text-purple-400' : ''}`} />
          <span>{isFetching ? 'Refreshing...' : 'Refresh Runs'}</span>
        </button>
      </div>

      {/* Runs Table */}
      <div className="border border-slate-800 rounded-xl overflow-hidden bg-surface-card shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-surface-100/50">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300">
            Recorded Multi-Agent Workflows ({runs.length})
          </span>
          <span className="text-xs font-mono text-slate-500">Fast Analyst & Deep Research Swarms</span>
        </div>

        {isLoading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-400">LOADING AGENT TELEMETRY...</div>
        ) : runs.length === 0 ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">No agent runs recorded yet.</div>
        ) : (
          <div className="divide-y divide-slate-800">
            {runs.map((run) => {
              const isExpanded = expandedId === run.id;
              return (
                <div key={run.id} className="transition-colors hover:bg-surface-100/30">
                  <div
                    onClick={() => toggleExpand(run.id)}
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                          {run.workflow_type}
                        </span>
                        <span className="text-xs font-semibold text-white">{run.query_or_topic}</span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-500">
                        Run ID: {run.id.slice(0, 13)}... • Started {new Date(run.created_at).toLocaleTimeString()}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 shrink-0 font-mono text-xs">
                      <span className="px-2 py-0.5 rounded bg-surface-100 border border-slate-800 text-slate-300">
                        {run.steps_executed} steps
                      </span>
                      <span className="px-2 py-0.5 rounded bg-surface-100 border border-slate-800 text-cyan-400">
                        {run.total_tokens.toLocaleString()} tokens
                      </span>
                      <span className="px-2 py-0.5 rounded bg-surface-100 border border-slate-800 text-amber-400">
                        {run.latency_ms.toFixed(1)}ms
                      </span>
                      <span className="inline-flex items-center text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2 py-0.5 rounded">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        {run.status}
                      </span>
                      <button className="text-slate-400 hover:text-white">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Step Trace */}
                  {isExpanded && (
                    <div className="p-4 bg-slate-950/70 border-t border-slate-800 space-y-3 font-mono text-xs animate-in fade-in duration-150">
                      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
                        <Terminal className="w-3.5 h-3.5 text-purple-400" />
                        <span>Execution Step Trace & Tool Invocations</span>
                      </div>
                      <div className="space-y-1.5">
                        {run.step_details.map((st, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded bg-surface-200/40 border border-slate-800/80 flex items-center justify-between text-xs"
                          >
                            <div className="flex items-center space-x-2">
                              <span className="text-purple-400 font-bold">{idx + 1}.</span>
                              <span className="text-slate-200 font-semibold">{st.step || st.action}</span>
                              {st.agent && <span className="text-slate-500 text-[10px]">[{st.agent}]</span>}
                            </div>
                            <div className="text-slate-400 text-[11px] flex items-center space-x-3">
                              {st.latency_ms && <span>{st.latency_ms.toFixed(1)}ms</span>}
                              {st.tokens && <span className="text-cyan-400">{st.tokens} toks</span>}
                              <span className="text-emerald-400">OK</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
