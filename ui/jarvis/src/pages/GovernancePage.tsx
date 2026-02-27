// ============================================================
//  GovernancePage — Governance & Prompt Management
//  Sections:
//    1. UI Rules viewer/editor (ui_rules.json)
//    2. System prompts browser
//    3. Active governance violations log
//    4. Role configuration (Read-Only vs Admin)
// ============================================================

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck, ShieldAlert, FileEdit, Save, RefreshCw,
  AlertTriangle, CheckCircle2, Eye, EyeOff, ChevronRight,
  Lock, Unlock, FileText, Zap
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────
interface GovernanceRule {
  id: string;
  name: string;
  description: string;
  condition: string;
  action: 'BLOCK' | 'WARN' | 'LOG';
  enabled: boolean;
}

interface SystemPrompt {
  id: string;
  name: string;
  role: 'extraction' | 'synthesis' | 'rerank' | 'l3_sage';
  content: string;
  version: number;
  last_modified: string;
}

interface Violation {
  id: string;
  timestamp: string;
  rule_id: string;
  rule_name: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  context: string;
  action_taken: string;
}

// ─── Section: Rules Editor ─────────────────────────────────────
function RulesSection() {
  const queryClient = useQueryClient();
  const [editingRule, setEditingRule] = useState<GovernanceRule | null>(null);
  const [draftContent, setDraftContent] = useState('');

  const { data: rules = [] } = useQuery<GovernanceRule[]>({
    queryKey: ['governance-rules'],
    queryFn: async () => {
      const res = await fetch('/api/governance/rules');
      if (!res.ok) return [];
      return res.json();
    },
  });

  const toggleRule = useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      const res = await fetch(`/api/governance/rules/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!res.ok) throw new Error('Toggle failed');
      return res.json();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['governance-rules'] }),
  });

  const saveRule = useMutation({
    mutationFn: async (rule: GovernanceRule) => {
      const res = await fetch(`/api/governance/rules/${rule.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule),
      });
      if (!res.ok) throw new Error('Save failed');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['governance-rules'] });
      setEditingRule(null);
    },
  });

  const ACTION_COLORS = {
    BLOCK: { color: '#f87171', bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.3)' },
    WARN:  { color: '#fbbf24', bg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.3)' },
    LOG:   { color: '#22d3ee', bg: 'rgba(34,211,238,0.08)',  border: 'rgba(34,211,238,0.3)' },
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-[9px] font-bold uppercase tracking-[0.25em]" style={{ color: 'rgba(255,255,255,0.3)' }}>
          — Governance Rules ({rules.length} active)
        </div>
      </div>

      {rules.length === 0 ? (
        <div className="py-8 text-center text-[10px] uppercase tracking-widest rounded-lg border border-dashed"
          style={{ color: 'rgba(255,255,255,0.12)', borderColor: 'rgba(255,255,255,0.06)' }}>
          No governance rules loaded — check /api/governance/rules
        </div>
      ) : (
        rules.map((rule) => {
          const ac = ACTION_COLORS[rule.action] ?? ACTION_COLORS.LOG;
          const isEditing = editingRule?.id === rule.id;
          return (
            <div key={rule.id} className="rounded-lg border transition-all"
              style={{
                background: rule.enabled ? 'rgba(4,8,14,0.8)' : 'rgba(255,255,255,0.01)',
                borderColor: rule.enabled ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)',
                opacity: rule.enabled ? 1 : 0.5,
              }}>
              <div className="flex items-center gap-3 p-3">
                <button
                  onClick={() => toggleRule.mutate({ id: rule.id, enabled: !rule.enabled })}
                  className="shrink-0 w-8 h-5 rounded-full transition-all relative"
                  style={{ background: rule.enabled ? '#22d3ee40' : 'rgba(255,255,255,0.08)', border: `1px solid ${rule.enabled ? '#22d3ee60' : 'rgba(255,255,255,0.1)'}` }}
                >
                  <div className="absolute top-0.5 rounded-full w-4 h-4 transition-all"
                    style={{ background: rule.enabled ? '#22d3ee' : 'rgba(255,255,255,0.2)', left: rule.enabled ? '12px' : '2px' }} />
                </button>
                <span className="text-[11px] font-bold flex-1 min-w-0 truncate" style={{ color: rule.enabled ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.3)' }}>
                  {rule.name}
                </span>
                <span className="text-[8px] font-black px-1.5 py-0.5 rounded border shrink-0"
                  style={{ color: ac.color, borderColor: ac.border, background: ac.bg, letterSpacing: '0.1em' }}>
                  {rule.action}
                </span>
                <button
                  onClick={() => { setEditingRule(isEditing ? null : rule); setDraftContent(rule.condition); }}
                  className="p-1 rounded transition-colors shrink-0"
                  style={{ color: isEditing ? '#22d3ee' : 'rgba(255,255,255,0.2)' }}
                >
                  <FileEdit style={{ width: 12, height: 12 }} />
                </button>
              </div>

              <AnimatePresence>
                {isEditing && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                    <div className="px-3 pb-3 flex flex-col gap-2 border-t" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                      <div className="text-[9px] mt-2" style={{ color: 'rgba(255,255,255,0.4)' }}>{rule.description}</div>
                      <textarea
                        value={draftContent}
                        onChange={e => setDraftContent(e.target.value)}
                        rows={3}
                        className="w-full rounded p-2 font-mono text-[10px] resize-none outline-none"
                        style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', color: '#22d3ee' }}
                        placeholder="Condition expression..."
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => saveRule.mutate({ ...rule, condition: draftContent })}
                          disabled={saveRule.isPending}
                          className="flex items-center gap-1.5 px-3 py-1 rounded text-[9px] font-bold uppercase"
                          style={{ background: 'rgba(34,211,238,0.12)', border: '1px solid rgba(34,211,238,0.3)', color: '#22d3ee', letterSpacing: '0.1em' }}
                        >
                          <Save style={{ width: 10, height: 10 }} />
                          {saveRule.isPending ? 'Saving…' : 'Save'}
                        </button>
                        <button onClick={() => setEditingRule(null)} className="px-3 py-1 rounded text-[9px] font-bold uppercase"
                          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.4)', letterSpacing: '0.1em' }}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })
      )}
    </div>
  );
}

// ─── Section: System Prompts ───────────────────────────────────
function PromptsSection() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<SystemPrompt | null>(null);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  const ROLE_COLORS: Record<string, string> = {
    extraction: '#22d3ee',
    synthesis:  '#a78bfa',
    rerank:     '#fbbf24',
    l3_sage:    '#34d399',
  };

  const { data: prompts = [] } = useQuery<SystemPrompt[]>({
    queryKey: ['system-prompts'],
    queryFn: async () => {
      const res = await fetch('/api/governance/prompts');
      if (!res.ok) return [];
      return res.json();
    },
  });

  const savePrompt = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await fetch(`/api/governance/prompts/${selected.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: draft }),
      });
      queryClient.invalidateQueries({ queryKey: ['system-prompts'] });
      setSelected(null);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="text-[9px] font-bold uppercase tracking-[0.25em]" style={{ color: 'rgba(255,255,255,0.3)' }}>
        — System Prompts ({prompts.length})
      </div>

      <div className="grid grid-cols-1 gap-2">
        {prompts.length === 0 ? (
          <div className="py-6 text-center text-[10px] uppercase tracking-widest rounded-lg border border-dashed"
            style={{ color: 'rgba(255,255,255,0.12)', borderColor: 'rgba(255,255,255,0.06)' }}>
            No prompts loaded — check /api/governance/prompts
          </div>
        ) : (
          prompts.map((p) => {
            const isSelected = selected?.id === p.id;
            const color = ROLE_COLORS[p.role] ?? '#ffffff50';
            return (
              <div key={p.id} className="rounded-lg border overflow-hidden"
                style={{ background: isSelected ? 'rgba(4,8,14,0.95)' : 'rgba(4,8,14,0.6)', borderColor: isSelected ? `${color}40` : 'rgba(255,255,255,0.06)' }}>
                <div className="flex items-center gap-3 p-3 cursor-pointer" onClick={() => { setSelected(isSelected ? null : p); setDraft(p.content); }}>
                  <FileText style={{ width: 12, height: 12, color, flexShrink: 0 }} />
                  <span className="text-[11px] font-bold flex-1" style={{ color: 'rgba(255,255,255,0.7)' }}>{p.name}</span>
                  <span className="text-[8px] font-bold px-1.5 py-0.5 rounded border"
                    style={{ color, borderColor: `${color}40`, background: `${color}10`, letterSpacing: '0.1em' }}>
                    {p.role.toUpperCase()}
                  </span>
                  <span className="text-[8px] font-mono" style={{ color: 'rgba(255,255,255,0.2)' }}>v{p.version}</span>
                  <ChevronRight style={{ width: 10, height: 10, color: 'rgba(255,255,255,0.2)', transform: isSelected ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
                </div>

                <AnimatePresence>
                  {isSelected && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                      <div className="px-3 pb-3 flex flex-col gap-2 border-t" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                        <div className="text-[8px] mt-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
                          Last modified: {new Date(p.last_modified).toLocaleString()}
                        </div>
                        <textarea
                          value={draft}
                          onChange={e => setDraft(e.target.value)}
                          rows={8}
                          className="w-full rounded p-2 font-mono text-[10px] resize-y outline-none"
                          style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}
                        />
                        <div className="flex gap-2">
                          <button onClick={savePrompt} disabled={saving}
                            className="flex items-center gap-1.5 px-3 py-1 rounded text-[9px] font-bold uppercase"
                            style={{ background: `${color}18`, border: `1px solid ${color}40`, color, letterSpacing: '0.1em' }}>
                            <Save style={{ width: 10, height: 10 }} />
                            {saving ? 'Saving…' : 'Save Prompt'}
                          </button>
                          <button onClick={() => setSelected(null)}
                            className="px-3 py-1 rounded text-[9px] font-bold uppercase"
                            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.4)', letterSpacing: '0.1em' }}>
                            Discard
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ─── Section: Violations Log ───────────────────────────────────
const VIOLATIONS_PAGE_SIZE = 10;

function ViolationsSection() {
  const [page, setPage] = useState(0);
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');

  const skip = page * VIOLATIONS_PAGE_SIZE;

  const { data: violations = [] } = useQuery<Violation[]>({
    queryKey: ['governance-violations', skip, VIOLATIONS_PAGE_SIZE],
    queryFn: async () => {
      const res = await fetch(`/api/governance/violations?skip=${skip}&limit=${VIOLATIONS_PAGE_SIZE}`);
      if (!res.ok) return [];
      return res.json();
    },
    refetchInterval: 15000,
  });

  const filtered = severityFilter === 'ALL'
    ? violations
    : violations.filter(v => v.severity === severityFilter);

  const SEV = {
    HIGH:   { color: '#f87171', border: 'rgba(248,113,113,0.3)', bg: 'rgba(248,113,113,0.06)' },
    MEDIUM: { color: '#fbbf24', border: 'rgba(251,191,36,0.3)',  bg: 'rgba(251,191,36,0.06)'  },
    LOW:    { color: '#22d3ee', border: 'rgba(34,211,238,0.3)',  bg: 'rgba(34,211,238,0.06)'  },
  };

  const SEV_FILTERS: Array<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'> = ['ALL', 'HIGH', 'MEDIUM', 'LOW'];

  return (
    <div className="flex flex-col gap-3">
      {/* Header + filter pills */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="text-[9px] font-bold uppercase tracking-[0.25em]" style={{ color: 'rgba(255,255,255,0.3)' }}>
          — Recent Violations
        </div>
        {violations.filter(v => v.severity === 'HIGH').length > 0 && (
          <span className="text-[8px] font-bold px-1.5 py-0.5 rounded border"
            style={{ color: '#f87171', borderColor: 'rgba(248,113,113,0.3)', background: 'rgba(248,113,113,0.08)' }}>
            {violations.filter(v => v.severity === 'HIGH').length} HIGH
          </span>
        )}
        <div className="ml-auto flex gap-1">
          {SEV_FILTERS.map(f => (
            <button key={f} onClick={() => setSeverityFilter(f)}
              className="px-2 py-0.5 rounded text-[8px] font-bold uppercase transition-all"
              style={{
                background: severityFilter === f ? 'rgba(34,211,238,0.12)' : 'transparent',
                border: `1px solid ${severityFilter === f ? 'rgba(34,211,238,0.3)' : 'rgba(255,255,255,0.08)'}`,
                color: severityFilter === f ? '#22d3ee' : 'rgba(255,255,255,0.3)',
                letterSpacing: '0.1em',
              }}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="py-6 text-center rounded-lg border" style={{ borderColor: 'rgba(52,211,153,0.15)', background: 'rgba(52,211,153,0.03)' }}>
          <CheckCircle2 style={{ width: 20, height: 20, color: '#34d399', margin: '0 auto 8px' }} />
          <div className="text-[10px] uppercase tracking-widest" style={{ color: 'rgba(52,211,153,0.6)' }}>No violations detected</div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((v) => {
            const s = SEV[v.severity] ?? SEV.LOW;
            return (
              <div key={v.id} className="flex items-start gap-3 p-3 rounded-lg border"
                style={{ background: s.bg, borderColor: s.border }}>
                <AlertTriangle style={{ width: 12, height: 12, color: s.color, flexShrink: 0, marginTop: 1 }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] font-bold" style={{ color: s.color }}>{v.rule_name}</span>
                    <span className="text-[8px] font-black px-1.5 py-0.5 rounded border"
                      style={{ color: s.color, borderColor: s.border, background: `${s.color}10`, letterSpacing: '0.1em' }}>
                      {v.severity}
                    </span>
                  </div>
                  <div className="text-[9px] truncate" style={{ color: 'rgba(255,255,255,0.4)' }}>{v.context}</div>
                  <div className="text-[8px] mt-0.5" style={{ color: 'rgba(255,255,255,0.25)' }}>
                    Action: <span style={{ color: 'rgba(255,255,255,0.5)' }}>{v.action_taken}</span> · {new Date(v.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination controls */}
      <div className="flex items-center justify-between mt-1">
        <button
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={page === 0}
          className="px-3 py-1 rounded text-[9px] font-bold uppercase transition-all"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: page === 0 ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.5)',
            letterSpacing: '0.1em',
          }}>
          ← Prev
        </button>
        <span className="text-[8px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
          Page {page + 1} · {skip + 1}–{skip + violations.length}
        </span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={violations.length < VIOLATIONS_PAGE_SIZE}
          className="px-3 py-1 rounded text-[9px] font-bold uppercase transition-all"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: violations.length < VIOLATIONS_PAGE_SIZE ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.5)',
            letterSpacing: '0.1em',
          }}>
          Next →
        </button>
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────
export default function GovernancePage() {
  const [activeSection, setActiveSection] = useState<'rules' | 'prompts' | 'violations'>('rules');

  const SECTIONS = [
    { id: 'rules' as const,      label: 'Rules',      icon: ShieldCheck,  color: '#22d3ee' },
    { id: 'prompts' as const,    label: 'Prompts',    icon: FileText,     color: '#a78bfa' },
    { id: 'violations' as const, label: 'Violations', icon: ShieldAlert,  color: '#f87171' },
  ];

  return (
    <div className="h-full w-full overflow-y-auto p-6" style={{ background: '#030609' }}>
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-black tracking-[0.3em] uppercase text-white/85">
            Governance Center
          </h2>
          <p className="text-[10px] font-mono mt-1" style={{ color: 'rgba(255,255,255,0.3)', letterSpacing: '0.15em' }}>
            RULES · PROMPTS · VIOLATIONS · ACCESS CONTROL
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
          style={{ borderColor: 'rgba(34,211,238,0.2)', background: 'rgba(34,211,238,0.04)' }}>
          <Lock style={{ width: 12, height: 12, color: '#22d3ee' }} />
          <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.15em', color: '#22d3ee' }}>
            MODE-1 ENFORCED
          </span>
        </div>
      </div>

      {/* Section tabs */}
      <div className="flex gap-2 mb-6 p-1 rounded-lg border w-fit"
        style={{ background: 'rgba(4,8,14,0.8)', borderColor: 'rgba(255,255,255,0.06)' }}>
        {SECTIONS.map(({ id, label, icon: Icon, color }) => {
          const active = activeSection === id;
          return (
            <button key={id} onClick={() => setActiveSection(id)}
              className="flex items-center gap-2 px-4 py-2 rounded-md transition-all"
              style={{
                background: active ? `${color}12` : 'transparent',
                border: `1px solid ${active ? `${color}40` : 'transparent'}`,
                color: active ? color : 'rgba(255,255,255,0.35)',
                fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
                boxShadow: active ? `0 0 8px ${color}20` : 'none',
              }}>
              <Icon style={{ width: 12, height: 12 }} />
              {label.toUpperCase()}
            </button>
          );
        })}
      </div>

      {/* Section content */}
      <AnimatePresence mode="wait">
        <motion.div key={activeSection} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
          {activeSection === 'rules'      && <RulesSection />}
          {activeSection === 'prompts'    && <PromptsSection />}
          {activeSection === 'violations' && <ViolationsSection />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
