import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import {
  GitFork,
  ArrowLeft,
  FileText,
  Code2,
  Cpu,
  Newspaper,
  Wrench,
  ExternalLink,
  ShieldCheck,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  ChevronDown,
} from 'lucide-react';

interface GraphNode {
  id: string;
  title: string;
  content_type: 'paper' | 'repo' | 'model' | 'article' | 'tool';
  canonical_url: string;
  source_name: string | null;
  published_at: string | null;
  is_root: boolean;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation_type: string;
  confidence_score: number;
  link_method: string;
  evidence_snippet: string;
}

interface KnowledgeGraphData {
  root_document_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface FeedItem {
  id: string;
  title: string;
  content_type: string;
  source: string;
  linked_repos_count?: number;
}

export const GraphExplorerPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [confidenceFilter, setConfidenceFilter] = useState<'all' | 'verified_only'>('all');

  // Fetch linked documents for quick switcher dropdown
  const { data: linkedPapers } = useQuery<FeedItem[]>({
    queryKey: ['linked_papers_dropdown'],
    queryFn: async () => {
      const res = await apiClient.get<FeedItem[]>('/v1/intel/feed?content_type=paper&page_size=30');
      return Array.isArray(res.data) ? res.data : [];
    },
    staleTime: 60000,
  });

  const { data: rawGraphData, isLoading, error } = useQuery<KnowledgeGraphData>({
    queryKey: ['document_subgraph', documentId, confidenceFilter],
    queryFn: async () => {
      const minConf = confidenceFilter === 'verified_only' ? '&min_confidence=1.0' : '';
      const res = await apiClient.get<KnowledgeGraphData>(`/v1/intel/documents/${documentId}/graph?depth=2${minConf}`);
      return res.data;
    },
    enabled: Boolean(documentId),
  });

  // Filter out any nodes that don't match confidence filter
  const graphData = React.useMemo(() => {
    if (!rawGraphData) return null;
    if (confidenceFilter === 'all') return rawGraphData;
    const validEdges = rawGraphData.edges.filter((e) => e.confidence_score >= 0.99);
    const validNodeIds = new Set<string>([rawGraphData.root_document_id]);
    validEdges.forEach((e) => {
      validNodeIds.add(e.source);
      validNodeIds.add(e.target);
    });
    return {
      root_document_id: rawGraphData.root_document_id,
      nodes: rawGraphData.nodes.filter((n) => validNodeIds.has(n.id)),
      edges: validEdges,
    };
  }, [rawGraphData, confidenceFilter]);

  const selectedNode = graphData?.nodes.find((n) => n.id === selectedNodeId) ||
    graphData?.nodes.find((n) => n.id === documentId);
  const selectedEdge = graphData?.edges.find((e) => e.id === selectedEdgeId);

  // Position nodes radially around center with 2 non-overlapping concentric rings
  const width = 900;
  const height = 650;
  const centerX = width / 2;
  const centerY = height / 2;

  const nodePositions = React.useMemo(() => {
    if (!graphData?.nodes) return new Map<string, { x: number; y: number }>();
    const pos = new Map<string, { x: number; y: number }>();
    const rootId = documentId || graphData.root_document_id;

    // Put root at center
    pos.set(rootId, { x: centerX, y: centerY });

    // Partition remaining nodes into Hop 1 (direct neighbors of root) and Hop 2 (indirect)
    const directNeighborIds = new Set<string>();
    graphData.edges.forEach((edge) => {
      if (edge.source === rootId) directNeighborIds.add(edge.target);
      if (edge.target === rootId) directNeighborIds.add(edge.source);
    });

    const otherNodes = graphData.nodes.filter((n) => n.id !== rootId);
    const hop1Nodes = otherNodes.filter((n) => directNeighborIds.has(n.id)).slice(0, 10);
    const hop1IdSet = new Set(hop1Nodes.map((n) => n.id));
    const hop2Nodes = otherNodes.filter((n) => !hop1IdSet.has(n.id)).slice(0, 8);

    // Inner Ring: Hop 1 (Radius 190px, angular spacing >= 36 degrees)
    const r1 = 190;
    const step1 = (2 * Math.PI) / Math.max(1, hop1Nodes.length);
    hop1Nodes.forEach((node, idx) => {
      const angle = idx * step1 - Math.PI / 2;
      pos.set(node.id, {
        x: centerX + r1 * Math.cos(angle),
        y: centerY + r1 * Math.sin(angle),
      });
    });

    // Outer Ring: Hop 2 (Radius 330px, offset angle for staggered visibility)
    const r2 = 330;
    const step2 = (2 * Math.PI) / Math.max(1, hop2Nodes.length);
    const offsetAngle = step2 / 2;
    hop2Nodes.forEach((node, idx) => {
      const angle = idx * step2 - Math.PI / 2 + offsetAngle;
      pos.set(node.id, {
        x: centerX + r2 * Math.cos(angle),
        y: centerY + r2 * Math.sin(angle),
      });
    });

    return pos;
  }, [graphData, documentId]);

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'paper':
        return <FileText className="w-4 h-4 text-[#D4AF37]" />;
      case 'repo':
        return <Code2 className="w-4 h-4 text-emerald-400" />;
      case 'model':
        return <Cpu className="w-4 h-4 text-purple-400" />;
      case 'article':
        return <Newspaper className="w-4 h-4 text-amber-400" />;
      default:
        return <Wrench className="w-4 h-4 text-neutral-400" />;
    }
  };

  const getNodeColor = (type: string, isRoot: boolean) => {
    if (isRoot) return { stroke: '#D4AF37', fill: '#2A160F', text: '#F3D06B' };
    switch (type) {
      case 'paper':
        return { stroke: '#E06535', fill: '#22120C', text: '#FF8C5A' };
      case 'repo':
        return { stroke: '#10b981', fill: '#0a2318', text: '#34d399' };
      case 'model':
        return { stroke: '#a855f7', fill: '#240f3b', text: '#c084fc' };
      case 'article':
        return { stroke: '#f59e0b', fill: '#2b1b08', text: '#fbbf24' };
      default:
        return { stroke: '#78716c', fill: '#1c1917', text: '#a8a29e' };
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Bar Navigation & Knowledge Graph Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-4 rounded-2xl border border-[rgba(212, 175, 55,0.16)] bg-[#0D1017]/80">
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="p-2.5 rounded-xl bg-[#10131A] border border-[rgba(212, 175, 55,0.15)] text-[#EAD8D0] hover:text-[#D4AF37] hover:border-[#D4AF37]/40 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-[#FFF6F0] flex items-center gap-2 tracking-tight">
              <GitFork className="w-5 h-5 text-[#D4AF37]" />
              Paper-to-Code Knowledge Graph Explorer
            </h1>
            <p className="text-xs text-[#A89890]">
              Deterministic & semantic relational subgraphs with verified paper↔code links
            </p>
          </div>
        </div>

        {/* Quick Switcher & Zoom Controls */}
        <div className="flex items-center flex-wrap gap-2.5">
          {/* Confidence Filter Toggle */}
          <div className="flex items-center bg-[#10131A] border border-[rgba(212, 175, 55,0.18)] p-1 rounded-xl">
            <button
              onClick={() => setConfidenceFilter('all')}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono transition ${
                confidenceFilter === 'all'
                  ? 'btn-gold-glow font-bold'
                  : 'text-[#A89890] hover:text-[#FFF6F0]'
              }`}
            >
              All Links
            </button>
            <button
              onClick={() => setConfidenceFilter('verified_only')}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono transition ${
                confidenceFilter === 'verified_only'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
                  : 'text-[#A89890] hover:text-[#FFF6F0]'
              }`}
            >
              Verified URL (100%)
            </button>
          </div>

          {/* Quick Switcher Dropdown */}
          {linkedPapers && linkedPapers.length > 0 && (
            <div className="relative">
              <select
                aria-label="Browse Linked Paper-to-Code Graphs"
                className="appearance-none bg-[#10131A] border border-[rgba(212, 175, 55,0.2)] text-xs text-[#EAD8D0] rounded-xl px-3 py-2 pr-8 focus:outline-none focus:border-[#D4AF37] cursor-pointer max-w-[260px] truncate"
                value={documentId}
                onChange={(e) => navigate(`/explorer/${e.target.value}`)}
              >
                <option value="" disabled>Browse Linked Paper↔Code Graphs</option>
                {linkedPapers
                  .filter((p) => (p.linked_repos_count || 0) > 0)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.linked_repos_count ? `[${p.linked_repos_count} Repos] ` : ''}{p.title.slice(0, 36)}...
                    </option>
                  ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-[#A89890] absolute right-2.5 top-3 pointer-events-none" />
            </div>
          )}

          {/* Controls */}
          <div className="flex items-center gap-1.5 bg-[#10131A] border border-[rgba(212, 175, 55,0.15)] p-1 rounded-xl">
            <button
              onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.15))}
              className="p-1.5 rounded-lg text-[#A89890] hover:text-[#FFF6F0] hover:bg-[#232936] transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono text-[#EAD8D0] px-2">{Math.round(zoomLevel * 100)}%</span>
            <button
              onClick={() => setZoomLevel((z) => Math.min(1.6, z + 0.15))}
              className="p-1.5 rounded-lg text-[#A89890] hover:text-[#FFF6F0] hover:bg-[#232936] transition"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoomLevel(1)}
              className="p-1.5 rounded-lg text-[#A89890] hover:text-[#FFF6F0] hover:bg-[#232936] transition"
              title="Reset Zoom"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="h-[600px] flex items-center justify-center border border-[rgba(212, 175, 55,0.15)] rounded-2xl bg-[#0E0A08] text-[#A89890] font-mono text-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#D4AF37] animate-spin" />
            Traversing knowledge graph relationships...
          </div>
        </div>
      ) : error || !graphData ? (
        <div className="h-[600px] flex items-center justify-center border border-rose-900/40 rounded-2xl bg-[#0E0A08] text-rose-400 font-mono text-sm">
          Failed to load document knowledge graph.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Visualizer Canvas */}
          <div className="lg:col-span-2 border border-[rgba(212, 175, 55,0.18)] rounded-2xl bg-[#090706] dot-grid overflow-hidden relative shadow-2xl flex items-center justify-center min-h-[550px]">
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="w-full h-full select-none cursor-grab"
              style={{
                transform: `scale(${zoomLevel})`,
                transition: 'transform 0.15s ease-out',
              }}
            >
              <defs>
                <marker
                  id="arrowhead"
                  markerWidth="8"
                  markerHeight="6"
                  refX="18"
                  refY="3"
                  orient="auto"
                >
                  <polygon points="0 0, 8 3, 0 6" fill="#D4AF37" />
                </marker>
                <marker
                  id="arrowhead-dim"
                  markerWidth="8"
                  markerHeight="6"
                  refX="18"
                  refY="3"
                  orient="auto"
                >
                  <polygon points="0 0, 8 3, 0 6" fill="#66524A" />
                </marker>
              </defs>

              {/* Edges */}
              {graphData.edges.map((edge) => {
                const sPos = nodePositions.get(edge.source);
                const tPos = nodePositions.get(edge.target);
                if (!sPos || !tPos) return null;

                const isEdgeSelected = selectedEdgeId === edge.id;
                const midX = (sPos.x + tPos.x) / 2;
                const midY = (sPos.y + tPos.y) / 2;

                return (
                  <g key={edge.id} className="cursor-pointer" onClick={() => { setSelectedEdgeId(edge.id); setSelectedNodeId(null); }}>
                    <line
                      x1={sPos.x}
                      y1={sPos.y}
                      x2={tPos.x}
                      y2={tPos.y}
                      stroke={isEdgeSelected ? '#D4AF37' : '#45332B'}
                      strokeWidth={isEdgeSelected ? 3 : 1.5}
                      strokeDasharray={edge.link_method === 'semantic_author_match' ? '4,4' : undefined}
                      markerEnd={isEdgeSelected ? 'url(#arrowhead)' : 'url(#arrowhead-dim)'}
                    />
                    {/* Edge Label Pill */}
                    <rect
                      x={midX - 38}
                      y={midY - 10}
                      width="76"
                      height="18"
                      rx="5"
                      fill="#10131A"
                      stroke={isEdgeSelected ? '#D4AF37' : '#3D2B24'}
                      strokeWidth="1"
                    />
                    <text
                      x={midX}
                      y={midY + 3}
                      fill={isEdgeSelected ? '#D4AF37' : '#C7B6AF'}
                      fontSize="9"
                      fontWeight="bold"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      {edge.relation_type}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {graphData.nodes.map((node) => {
                const pos = nodePositions.get(node.id);
                if (!pos) return null;

                const isSelected = selectedNode?.id === node.id;
                const colors = getNodeColor(node.content_type, node.is_root);

                return (
                  <g
                    key={node.id}
                    className="cursor-pointer transition-transform hover:opacity-90"
                    onClick={() => { setSelectedNodeId(node.id); setSelectedEdgeId(null); }}
                    transform={`translate(${pos.x}, ${pos.y})`}
                  >
                    <circle
                      r={node.is_root ? 32 : 26}
                      fill={colors.fill}
                      stroke={isSelected ? '#FFF6F0' : colors.stroke}
                      strokeWidth={isSelected ? 3.5 : 2}
                      className={isSelected ? 'filter drop-shadow-[0_0_12px_rgba(212, 175, 55,0.8)]' : ''}
                    />
                    <text
                      y={4}
                      fill={colors.text}
                      fontSize="9"
                      fontWeight="bold"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      {node.content_type.toUpperCase()}
                    </text>

                    {/* Node title preview below */}
                    <text
                      y={node.is_root ? 44 : 38}
                      fill="#EAD8D0"
                      fontSize="11"
                      fontWeight={node.is_root ? 'bold' : 'normal'}
                      textAnchor="middle"
                      className="pointer-events-none"
                    >
                      {node.title.length > 22 ? `${node.title.slice(0, 20)}...` : node.title}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Canvas overlay badge */}
            <div className="absolute bottom-3 left-3 bg-[#10131A]/90 border border-[rgba(212, 175, 55,0.18)] px-3 py-1.5 rounded-xl text-xs font-mono text-[#A89890] flex items-center gap-3 backdrop-blur-sm">
              <span>Nodes: <strong className="text-[#D4AF37]">{graphData.nodes.length}</strong></span>
              <span>•</span>
              <span>Relations: <strong className="text-emerald-400">{graphData.edges.length}</strong></span>
            </div>
          </div>

          {/* Side Entity / Relationship Inspector */}
          <div className="border border-[rgba(212, 175, 55,0.16)] rounded-2xl bg-[#140F0D]/90 p-5 space-y-5 flex flex-col justify-between backdrop-blur-md">
            <div>
              <div className="border-b border-[rgba(212, 175, 55,0.12)] pb-3 flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#FFF6F0] uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#D4AF37]" />
                  Graph Inspector
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-[#241712] border border-[rgba(212, 175, 55,0.2)] text-[#D4AF37] font-semibold">
                  {selectedEdge ? 'RELATION' : 'ENTITY'}
                </span>
              </div>

              {selectedEdge ? (
                <div className="mt-4 space-y-4">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#A89890]">Relation Type</span>
                    <p className="text-base font-bold text-[#D4AF37] font-mono mt-0.5">
                      {selectedEdge.relation_type}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#A89890]">Confidence Score</span>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-[#241712] rounded-full h-2 overflow-hidden border border-[rgba(212, 175, 55,0.1)]">
                        <div
                          className="bg-emerald-500 h-2 rounded-full"
                          style={{ width: `${selectedEdge.confidence_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono font-bold text-emerald-400">
                        {Math.round(selectedEdge.confidence_score * 100)}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#A89890]">Discovery Method</span>
                    <p className="text-xs font-mono text-[#EAD8D0] mt-0.5 px-2.5 py-1 rounded-lg bg-[#241712] border border-[rgba(212, 175, 55,0.18)] inline-block">
                      {selectedEdge.link_method}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#A89890]">Evidence Snippet</span>
                    <p className="text-xs font-mono text-[#D5C2B9] mt-1 bg-[#0A0706] p-3 rounded-xl border border-[rgba(212, 175, 55,0.14)] break-all leading-relaxed">
                      {selectedEdge.evidence_snippet}
                    </p>
                  </div>
                </div>
              ) : selectedNode ? (
                <div className="mt-4 space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase font-mono px-2.5 py-1 rounded-lg bg-[#2A160F] text-[#D4AF37] border border-[#D4AF37]/30 font-semibold flex items-center gap-1.5">
                      {getNodeIcon(selectedNode.content_type)}
                      {selectedNode.content_type}
                    </span>
                    {selectedNode.is_root && (
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-[#381B10] text-[#F3D06B] border border-[rgba(212, 175, 55,0.3)]">
                        ROOT ORIGIN
                      </span>
                    )}
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#A89890]">Title</span>
                    <h4 className="text-sm font-bold text-[#FFF6F0] mt-1 leading-snug">
                      {selectedNode.title}
                    </h4>
                  </div>

                  {selectedNode.source_name && (
                    <div>
                      <span className="text-[10px] uppercase font-bold text-[#A89890]">Source</span>
                      <p className="text-xs text-[#EAD8D0] font-mono mt-0.5">{selectedNode.source_name}</p>
                    </div>
                  )}

                  {selectedNode.published_at && (
                    <div>
                      <span className="text-[10px] uppercase font-bold text-[#A89890]">Published</span>
                      <p className="text-xs text-[#EAD8D0] font-mono mt-0.5">
                        {new Date(selectedNode.published_at).toLocaleDateString()}
                      </p>
                    </div>
                  )}

                  <div>
                    <a
                      href={selectedNode.canonical_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-[#D4AF37] hover:text-[#FFA078] font-medium transition"
                    >
                      Canonical Reference URL
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>

                  {graphData && graphData.edges.length === 0 && (
                    <div className="p-3 rounded-xl bg-[#2A160F]/40 border border-[#D4AF37]/30 text-xs text-[#F3D06B] space-y-1 mt-2">
                      <div className="font-semibold flex items-center gap-1.5">
                        <RotateCcw className="w-3.5 h-3.5 text-[#D4AF37]" />
                        Explore & Link Related Entities
                      </div>
                      <p className="text-[11px] text-[#D5C2B9] leading-relaxed">
                        This entity has 0 explicit relationship edges yet. When background entity linking or citations run, connections to GitHub repositories and papers will automatically emerge here.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-xs text-[#A89890] py-10 text-center">
                  Select any node or relation edge to inspect evidence details.
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-[rgba(212, 175, 55,0.12)] text-[11px] text-[#A89890]">
              Deterministic links verified by exact URL/arXiv ID. Semantic links corroborated with author surname overlap.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
