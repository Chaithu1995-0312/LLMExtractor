// ============================================================
//  IngestionPage — Full-page Ingestion Pipeline Monitor
//  Shows: Active sync job progress, historical run log,
//  pipeline stage breakdown, and raw file stats.
// ============================================================

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlayCircle, RefreshCw, FileJson, Scissors, Layers, Box, Network,
  CheckCircle2, XCircle, Clock, ChevronRight, AlertTriangle, Terminal,
  Database, Activity
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────
interface SyncJob {
  run_id: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  started_at: string;
  completed_at?: string;
  stage: string;
  stats: {
    files_processed: number;
    bricks_extracted: number;
    nodes_created: number;
    edges_created: number;
    errors: number;
  };
  logs: string[];
}

interface SyncStats {
  total_runs: number;
  last_run: string;
  total_bricks: number;
  total_nodes: number;
  avg_run_duration_s: number;
}

interface NexusReportValidation {
  check: string;
  result: string;
  notes?: string;
}

interface NexusReportTableUpdate {
  table: string;
  added: number;
  updated: number;
  why: string;
}

interface NexusReportNode {
  node_id: string;
  node_type: string;
  description: string;
}

interface NexusProcessingReport {
  source_run: string;
  graph_nodes_created: NexusReportNode[];
  edges_created: Array<{ source: string; type: string; target: string }>;
  tables_updated: NexusReportTableUpdate[];
  pending_tasks: Array<{ task: string; status: string; assignee?: string; detail?: string }>;
  validation_results: NexusReportValidation[];
}

interface NexusArchitectureReport {
  entry_points: Array<{ item: string; status: string }>;
  internal_components: Array<{ item: string; file: string; status: string }>;
}

// ─── Pipeline Stage Definitions ───────────────────────────────
const PIPELINE_STAGES = [
  { key: 'FETCH',    icon: FileJson,  label: 'Fetch Sources',    color: '#22d3ee', desc: 'Pull raw JSON from ChatGPT export' },
  { key: 'SPLIT',    icon: Scissors,  label: 'Tree Splitter',    color: '#a78bfa', desc: 'Segment conversation trees into chunks' },
  { key: 'COMPILE',  icon: Layers,    label: 'Semantic Compile', color: '#fbbf24', desc: 'Extract semantic bricks via LLM' },
  { key: 'GRAPH',    icon: Box,       label: 'Graph Ingest',     color: '#fb923c', desc: 'Write bricks into Postgres graph' },
  { key: 'SYNTHESIZE', icon: Network, label: 'Synthesize',       color: '#34d399', desc: 'Build edges & lifecycle transitions' },
];

function stageIndex(stageKey: string): number {
  return PIPELINE_STAGES.findIndex(s => s.key === stageKey || stageKey?.includes(s.key));
}

// ─── Sub-components ───────────────────────────────────────────
function PipelineStageRow({ stage, index, activeIndex }: {
  stage: typeof PIPELINE_STAGES[0];
  index: number;
  activeIndex: number;
}) {
  const Icon = stage.icon;
  const isActive = index === activeIndex;
  const isDone = index < activeIndex;
  const isPending = index > activeIndex;

  return (
    <div className="flex items-center gap-4 py-3 px-4 rounded-lg border transition-all duration-300"
      style={{
        background: isActive ? `${stage.color}10` : isDone ? 'rgba(52,211,153,0.04)' : 'rgba(255,255,255,0.02)',
        borderColor: isActive ? `${stage.color}50` : isDone ? 'rgba(52,211,153,0.2)' : 'rgba(255,255,255,0.05)',
        boxShadow: isActive ? `0 0 16px ${stage.color}20` : 'none',
      }}
    >
      {/* Status icon */}
      <div className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg"
        style={{
          background: isActive ? `${stage.color}20` : isDone ? 'rgba(52,211,153,0.12)' : 'rgba(255,255,255,0.04)',
          border: `1px solid ${isActive ? stage.color + '60' : isDone ? 'rgba(52,211,153,0.3)' : 'rgba(255,255,255,0.08)'}`,
        }}
      >
        {isDone
          ? <CheckCircle2 style={{ width: 14, height: 14, color: '#34d399' }} />
          : <Icon style={{ width: 14, height: 14, color: isActive ? stage.color : 'rgba(255,255,255,0.2)',
              filter: isActive ? `drop-shadow(0 0 4px ${stage.color})` : 'none' }} />
        }
      </div>

      {/* Label + desc */}
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-bold" style={{ color: isActive ? stage.color : isDone ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.25)' }}>
          {stage.label}
        </div>
        <div className="text-[9px]" style={{ color: 'rgba(255,255,255,0.25)' }}>{stage.desc}</div>
      </div>

      {/* Animated badge */}
      {isActive && (
        <motion.div
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ repeat: Infinity, duration: 1.2 }}
          className="text-[8px] font-bold px-2 py-0.5 rounded border"
          style={{ color: stage.color, borderColor: `${stage.color}50`, background: `${stage.color}10`, letterSpacing: '0.1em' }}
        >
          ACTIVE
        </motion.div>
      )}
      {isDone && (
        <span className="text-[8px] font-bold px-2 py-0.5 rounded border"
          style={{ color: '#34d399', borderColor: 'rgba(52,211,153,0.3)', background: 'rgba(52,211,153,0.08)', letterSpacing: '0.1em' }}>
          DONE
        </span>
      )}
      {isPending && activeIndex >= 0 && (
        <span className="text-[8px] font-bold px-2 py-0.5 rounded border"
          style={{ color: 'rgba(255,255,255,0.2)', borderColor: 'rgba(255,255,255,0.06)', letterSpacing: '0.1em' }}>
          QUEUED
        </span>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: SyncJob['status'] }) {
  const cfg = {
    running:   { color: '#22d3ee', label: 'RUNNING',   border: 'rgba(34,211,238,0.3)',  bg: 'rgba(34,211,238,0.08)'  },
    completed: { color: '#34d399', label: 'COMPLETED', border: 'rgba(52,211,153,0.3)',  bg: 'rgba(52,211,153,0.08)'  },
    failed:    { color: '#f87171', label: 'FAILED',    border: 'rgba(248,113,113,0.3)', bg: 'rgba(248,113,113,0.08)' },
    pending:   { color: '#fbbf24', label: 'PENDING',   border: 'rgba(251,191,36,0.3)',  bg: 'rgba(251,191,36,0.08)'  },
  }[status] ?? { color: '#ffffff50', label: status.toUpperCase(), border: 'rgba(255,255,255,0.1)', bg: 'transparent' };

  return (
    <span className="text-[8px] font-black px-2 py-0.5 rounded border" style={{ color: cfg.color, borderColor: cfg.border, background: cfg.bg, letterSpacing: '0.12em' }}>
      {cfg.label}
    </span>
  );
}

// ─── Main ─────────────────────────────────────────────────────
export default function IngestionPage() {
  const queryClient = useQueryClient();
  const [selectedJob, setSelectedJob] = useState<SyncJob | null>(null);
  const [logExpanded, setLogExpanded] = useState(false);

  // Poll for current sync status
  const { data: syncStatus } = useQuery<{ job: SyncJob | null; stats: SyncStats }>({
    queryKey: ['sync-status'],
    queryFn: async () => {
      const res = await fetch('/api/sync/status');
      if (!res.ok) return { job: null, stats: { total_runs: 0, last_run: '—', total_bricks: 0, total_nodes: 0, avg_run_duration_s: 0 } };
      return res.json();
    },
    refetchInterval: 3000,
  });

  // Poll for run history
  const { data: runHistory } = useQuery<SyncJob[]>({
    queryKey: ['sync-history'],
    queryFn: async () => {
      const res = await fetch('/api/sync/history?limit=10');
      if (!res.ok) return [];
      return res.json();
    },
    refetchInterval: 10000,
  });

  const triggerSync = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/sync/run', { method: 'POST' });
      if (!res.ok) throw new Error('Sync trigger failed');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sync-status'] });
      queryClient.invalidateQueries({ queryKey: ['sync-history'] });
    },
  });

  // Latest processed report artifacts (generated by scripts/process_memory_context.py)
  const { data: nexusReport, isLoading: reportLoading } = useQuery<NexusProcessingReport | null>({
    queryKey: ['nexus-latest-report'],
    queryFn: async () => {
      const res = await fetch('/api/reports/nexus/latest');
      if (!res.ok) return null;
      return res.json();
    },
    refetchInterval: 15000,
  });

  const { data: architectureReport } = useQuery<NexusArchitectureReport | null>({
    queryKey: ['nexus-architecture-report'],
    queryFn: async () => {
      const res = await fetch('/api/reports/nexus/architecture');
      if (!res.ok) return null;
      return res.json();
    },
    refetchInterval: 30000,
  });

  const activeJob = syncStatus?.job;
  const stats = syncStatus?.stats;
  const isRunning = activeJob?.status === 'running';
  const activeStageIdx = activeJob ? stageIndex(activeJob.stage) : -1;
  const failedValidations = nexusReport?.validation_results?.filter(v => v.result !== 'PASS').length ?? 0;
  const implementedEntryPoints = architectureReport?.entry_points?.filter(e => e.status === 'Implemented').length ?? 0;
  const totalEntryPoints = architectureReport?.entry_points?.length ?? 0;

  return (
    <div className="h-full w-full overflow-y-auto p-6" style={{ background: '#030609' }}>
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-black tracking-[0.3em] uppercase text-white/85">
            Ingestion Pipeline
          </h2>
          <p className="text-[10px] font-mono mt-1" style={{ color: 'rgba(255,255,255,0.3)', letterSpacing: '0.15em' }}>
            RAW JSON → SEMANTIC BRICKS → KNOWLEDGE GRAPH
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { alert('Stopping sync is not yet implemented.'); }}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg font-bold uppercase transition-all text-red-400 bg-red-500/0 hover:bg-red-500/10 border border-red-500/40"
            style={{ fontSize: 11, letterSpacing: '0.2em' }}
          >
            <XCircle size={14} />
            <span>STOP</span>
          </button>
          <button
            onClick={() => triggerSync.mutate()}
            disabled={isRunning || triggerSync.isPending}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg font-bold uppercase transition-all disabled:opacity-50"
            style={{
              fontSize: 11,
              letterSpacing: '0.2em',
              background: 'linear-gradient(135deg, #00D9FF, #00A9FF)',
              color: '#030609',
              border: '1px solid #00D9FF',
              boxShadow: '0 0 20px 0 #00D9FF40',
            }}
          >
            {isRunning ? (
              <><RefreshCw size={14} className="animate-spin" /> SYNCING...</>
            ) : (
              <><PlayCircle size={14} /> RUN SYNC</>
            )}
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Runs',       value: stats?.total_runs ?? '—',          color: '#22d3ee', icon: Activity },
          { label: 'Total Bricks',     value: stats?.total_bricks?.toLocaleString() ?? '—', color: '#a78bfa', icon: Box },
          { label: 'Total Nodes',      value: stats?.total_nodes?.toLocaleString() ?? '—',  color: '#34d399', icon: Network },
          { label: 'Avg Duration',     value: stats?.avg_run_duration_s ? `${stats.avg_run_duration_s.toFixed(1)}s` : '—', color: '#fbbf24', icon: Clock },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} className="flex items-center gap-3 p-4 rounded-lg border"
            style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
            <div className="p-2 rounded-lg" style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
              <Icon style={{ width: 14, height: 14, color }} />
            </div>
            <div>
              <div className="text-[18px] font-black font-mono" style={{ color }}>{value}</div>
              <div className="text-[9px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.3)' }}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Pipeline Stages */}
        <div className="lg:col-span-1 rounded-lg border p-4"
          style={{ background: 'rgba(4,8,14,0.8)', borderColor: 'rgba(255,255,255,0.06)' }}>
          <div className="text-[9px] font-bold uppercase tracking-[0.25em] mb-4" style={{ color: 'rgba(255,255,255,0.3)' }}>
            — Pipeline Stages
          </div>
          <div className="flex flex-col gap-2">
            {PIPELINE_STAGES.map((stage, i) => (
              <PipelineStageRow key={stage.key} stage={stage} index={i} activeIndex={activeStageIdx} />
            ))}
          </div>

          {/* Progress bar */}
          {isRunning && activeStageIdx >= 0 && (
            <div className="mt-4">
              <div className="flex justify-between text-[8px] mb-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
                <span>PROGRESS</span>
                <span>{Math.round((activeStageIdx / (PIPELINE_STAGES.length - 1)) * 100)}%</span>
              </div>
              <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: 'linear-gradient(90deg, #22d3ee, #34d399)' }}
                  animate={{ width: `${Math.round((activeStageIdx / (PIPELINE_STAGES.length - 1)) * 100)}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Active Job + Run History */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {/* Active job */}
          {activeJob && (
            <div className="rounded-lg border p-4" style={{ background: 'rgba(4,8,14,0.8)', borderColor: 'rgba(34,211,238,0.15)' }}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[9px] font-bold uppercase tracking-[0.25em]" style={{ color: 'rgba(255,255,255,0.3)' }}>
                  — Active Job
                </span>
                <StatusBadge status={activeJob.status} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                {[
                  { label: 'Files',   value: activeJob.stats.files_processed },
                  { label: 'Bricks',  value: activeJob.stats.bricks_extracted },
                  { label: 'Nodes',   value: activeJob.stats.nodes_created },
                  { label: 'Errors',  value: activeJob.stats.errors, warn: activeJob.stats.errors > 0 },
                ].map(({ label, value, warn }) => (
                  <div key={label} className="text-center p-2 rounded border"
                    style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.05)' }}>
                    <div className="text-[16px] font-black font-mono" style={{ color: warn ? '#f87171' : '#22d3ee' }}>{value}</div>
                    <div className="text-[8px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.3)' }}>{label}</div>
                  </div>
                ))}
              </div>

              {/* Log viewer */}
              <div>
                <button
                  onClick={() => setLogExpanded(v => !v)}
                  className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-widest mb-2"
                  style={{ color: 'rgba(255,255,255,0.3)' }}
                >
                  <Terminal style={{ width: 10, height: 10 }} />
                  Logs
                  <ChevronRight style={{ width: 10, height: 10, transform: logExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
                </button>
                <AnimatePresence>
                  {logExpanded && activeJob.logs?.length > 0 && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="rounded p-3 font-mono text-[9px] overflow-y-auto max-h-48"
                        style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.05)' }}>
                        {[...activeJob.logs].reverse().map((log, i) => (
                          <div key={i} className="mb-0.5" style={{ color: log.includes('ERROR') ? '#f87171' : log.includes('WARN') ? '#fbbf24' : '#34d399' }}>
                            {log}
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )}

          {/* Run History */}
          <div className="rounded-lg border p-4" style={{ background: 'rgba(4,8,14,0.8)', borderColor: 'rgba(255,255,255,0.06)' }}>
            <div className="text-[9px] font-bold uppercase tracking-[0.25em] mb-3" style={{ color: 'rgba(255,255,255,0.3)' }}>
              — Run History
            </div>
            {!runHistory || runHistory.length === 0 ? (
              <div className="py-8 text-center text-[10px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.12)' }}>
                No sync runs recorded yet
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {runHistory.map((job) => (
                  <div key={job.run_id}
                    onClick={() => setSelectedJob(selectedJob?.run_id === job.run_id ? null : job)}
                    className="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all"
                    style={{
                      background: selectedJob?.run_id === job.run_id ? 'rgba(34,211,238,0.04)' : 'rgba(255,255,255,0.02)',
                      borderColor: selectedJob?.run_id === job.run_id ? 'rgba(34,211,238,0.2)' : 'rgba(255,255,255,0.05)',
                    }}
                  >
                    {job.status === 'completed'
                      ? <CheckCircle2 style={{ width: 12, height: 12, color: '#34d399', flexShrink: 0 }} />
                      : job.status === 'failed'
                      ? <XCircle style={{ width: 12, height: 12, color: '#f87171', flexShrink: 0 }} />
                      : <Clock style={{ width: 12, height: 12, color: '#fbbf24', flexShrink: 0 }} />
                    }
                    <span className="text-[10px] font-mono flex-1 truncate" style={{ color: 'rgba(255,255,255,0.5)' }}>
                      {job.run_id.slice(0, 12)}…
                    </span>
                    <span className="text-[9px] font-mono shrink-0" style={{ color: 'rgba(255,255,255,0.3)' }}>
                      {new Date(job.started_at).toLocaleTimeString()}
                    </span>
                    <div className="flex gap-2 shrink-0">
                      <span className="text-[9px] font-mono" style={{ color: '#a78bfa' }}>{job.stats.bricks_extracted}B</span>
                      <span className="text-[9px] font-mono" style={{ color: '#34d399' }}>{job.stats.nodes_created}N</span>
                    </div>
                    <StatusBadge status={job.status} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Nexus processing report section (integrated into existing page, no new navigation) */}
      <div className="mt-6 rounded-lg border p-4" style={{ background: 'rgba(4,8,14,0.8)', borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[9px] font-bold uppercase tracking-[0.25em]" style={{ color: 'rgba(255,255,255,0.3)' }}>
              — Latest Nexus Processing Report
            </div>
            <div className="text-[9px] mt-1 font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
              Source Run: {nexusReport?.source_run ?? 'Not available'}
            </div>
          </div>
          {nexusReport && (
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-bold px-2 py-0.5 rounded border"
                style={{
                  color: failedValidations > 0 ? '#f87171' : '#34d399',
                  borderColor: failedValidations > 0 ? 'rgba(248,113,113,0.3)' : 'rgba(52,211,153,0.3)',
                  background: failedValidations > 0 ? 'rgba(248,113,113,0.08)' : 'rgba(52,211,153,0.08)',
                  letterSpacing: '0.1em'
                }}>
                {failedValidations > 0 ? 'VALIDATION ISSUES' : 'VALIDATION PASS'}
              </span>
            </div>
          )}
        </div>

        {reportLoading ? (
          <div className="py-8 text-center text-[10px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.18)' }}>
            Loading report artifacts...
          </div>
        ) : !nexusReport ? (
          <div className="py-8 text-center text-[10px] uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.18)' }}>
            No processing report found. Run `scripts/process_memory_context.py` first.
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {/* Summary */}
            <div className="rounded-lg border p-3" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
              <div className="text-[9px] uppercase tracking-widest mb-3" style={{ color: 'rgba(255,255,255,0.28)' }}>
                Summary
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="text-center p-2 rounded border" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                  <div className="text-[14px] font-black font-mono" style={{ color: '#22d3ee' }}>{nexusReport.graph_nodes_created.length}</div>
                  <div className="text-[8px] uppercase" style={{ color: 'rgba(255,255,255,0.28)' }}>Nodes</div>
                </div>
                <div className="text-center p-2 rounded border" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                  <div className="text-[14px] font-black font-mono" style={{ color: '#a78bfa' }}>{nexusReport.edges_created.length}</div>
                  <div className="text-[8px] uppercase" style={{ color: 'rgba(255,255,255,0.28)' }}>Edges</div>
                </div>
                <div className="text-center p-2 rounded border" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                  <div className="text-[14px] font-black font-mono" style={{ color: '#fbbf24' }}>{nexusReport.tables_updated.length}</div>
                  <div className="text-[8px] uppercase" style={{ color: 'rgba(255,255,255,0.28)' }}>Tables</div>
                </div>
                <div className="text-center p-2 rounded border" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                  <div className="text-[14px] font-black font-mono" style={{ color: failedValidations > 0 ? '#f87171' : '#34d399' }}>{failedValidations}</div>
                  <div className="text-[8px] uppercase" style={{ color: 'rgba(255,255,255,0.28)' }}>Validation Fail</div>
                </div>
              </div>
            </div>

            {/* Validation */}
            <div className="rounded-lg border p-3" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
              <div className="text-[9px] uppercase tracking-widest mb-3" style={{ color: 'rgba(255,255,255,0.28)' }}>
                Validation Results
              </div>
              <div className="flex flex-col gap-2">
                {nexusReport.validation_results.map((v) => (
                  <div key={v.check} className="flex items-start justify-between gap-2 text-[9px] rounded border p-2"
                    style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.2)' }}>
                    <div className="min-w-0">
                      <div className="font-semibold" style={{ color: 'rgba(255,255,255,0.8)' }}>{v.check}</div>
                      {v.notes && <div style={{ color: 'rgba(255,255,255,0.35)' }}>{v.notes}</div>}
                    </div>
                    <span className="text-[8px] font-bold px-2 py-0.5 rounded border shrink-0"
                      style={{
                        color: v.result === 'PASS' ? '#34d399' : '#f87171',
                        borderColor: v.result === 'PASS' ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)',
                        background: v.result === 'PASS' ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)',
                      }}>
                      {v.result}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Architecture snapshot */}
            <div className="rounded-lg border p-3" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.06)' }}>
              <div className="text-[9px] uppercase tracking-widest mb-3" style={{ color: 'rgba(255,255,255,0.28)' }}>
                Architecture Coverage
              </div>
              {!architectureReport ? (
                <div className="text-[9px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  Architecture comparison not available.
                </div>
              ) : (
                <>
                  <div className="text-[10px] font-mono mb-3" style={{ color: '#22d3ee' }}>
                    Entry Points: {implementedEntryPoints}/{totalEntryPoints} implemented
                  </div>
                  <div className="max-h-48 overflow-y-auto flex flex-col gap-1 pr-1">
                    {architectureReport.entry_points.map((ep) => (
                      <div key={ep.item} className="flex items-center justify-between text-[9px] rounded border p-1.5"
                        style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.2)' }}>
                        <span className="truncate pr-2" style={{ color: 'rgba(255,255,255,0.7)' }}>{ep.item}</span>
                        <span style={{ color: ep.status === 'Implemented' ? '#34d399' : ep.status === 'Partial' ? '#fbbf24' : '#f87171' }}>
                          {ep.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
