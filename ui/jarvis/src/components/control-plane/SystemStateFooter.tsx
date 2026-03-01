import { useControlPlaneStore } from '../../store/controlPlaneStore';
import { HealthStatus } from '../../types/controlPlane';
import { Database, BrainCircuit, Wallet, Cpu, CheckCircle, XCircle, AlertCircle, HelpCircle } from 'lucide-react';

const getStatusConfig = (status: HealthStatus) => {
  switch (status) {
    case 'healthy':
      return { color: '#00D9FF', Icon: CheckCircle, label: 'HEALTHY' };
    case 'warn':
    case 'empty':
      return { color: '#FFA500', Icon: AlertCircle, label: 'DEGRADED' };
    case 'fail':
    case 'unavailable':
      return { color: '#FF0000', Icon: XCircle, label: 'ERROR' };
    default:
      return { color: '#4A4A5E', Icon: HelpCircle, label: 'UNKNOWN' };
  }
};

export default function SystemStateFooter() {
  const { result } = useControlPlaneStore();
  const s = result?.system_state;

  const graphStatus = getStatusConfig(s?.graph_index ?? 'unknown');
  const memStatus = getStatusConfig(s?.memory_index ?? 'unknown');
  const budgetOk = s?.budget_pressure === 'low' || s?.budget_pressure === 'normal';
  const budgetStatus = budgetOk ? getStatusConfig('healthy') : getStatusConfig('warn');

  const lastCheck = s?.last_health_check ? new Date(s.last_health_check).toLocaleTimeString() : 'never';

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-3 items-center p-3 bg-black/30 border border-white/10 rounded-lg text-xs">
      <span className="font-bold text-[9px] tracking-widest text-white/30 pr-4">SYSTEM STATE</span>

      <Indicator
        Icon={Database}
        status={graphStatus}
        label="GRAPH"
        value={s?.graph_node_count !== undefined ? `${s.graph_node_count.toLocaleString()} nodes` : ''}
      />
      <Indicator
        Icon={BrainCircuit}
        status={memStatus}
        label="MEMORY"
        value={s?.memory_vector_count !== undefined ? `${s.memory_vector_count.toLocaleString()} vectors` : ''}
      />
      <Indicator Icon={Wallet} status={budgetStatus} label="BUDGET" value={s?.budget_pressure?.toUpperCase() ?? ''} />
      <Indicator
        Icon={Cpu}
        status={getStatusConfig('healthy')}
        label="MODEL"
        value={s?.embedding_model ?? 'nomic-embed-text'}
      />

      <span className="ml-auto text-[9px] font-mono text-white/20">
        Last Check: <span className="text-white/40">{lastCheck}</span>
      </span>
    </div>
  );
}

function Indicator({ Icon, status, label, value }: { Icon: any; status: any; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={14} className="text-white/40" />
      <span className="font-semibold tracking-wider text-white/60">{label}</span>
      <div
        className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold"
        style={{ background: `${status.color}20`, color: status.color }}
      >
        <status.Icon size={10} />
        <span>{status.label}</span>
      </div>
      {value && <span className="font-mono text-[10px] text-white/40">{value}</span>}
    </div>
  );
}
