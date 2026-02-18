import { useEffect, useState } from 'react';
import { Database, Server, Cpu, Activity, Clock } from 'lucide-react';

interface SystemHealth {
  db: 'healthy' | 'unhealthy';
  redis: 'healthy' | 'unhealthy';
  celery_workers: number;
  llm: 'available' | 'degraded';
  last_sync: string;
}

export function TopStatusBar() {
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          setHealth(await res.json());
        }
      } catch (e) {
        console.error("Health check failed", e);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // 30s refresh
    return () => clearInterval(interval);
  }, []);

  if (!health) return <div className="h-8 bg-black/50 border-b border-white/5" />;

  return (
    <div className="h-8 flex items-center justify-between px-4 bg-black/80 backdrop-blur border-b border-white/10 text-[10px] uppercase font-bold tracking-wider text-white/60">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Database className="w-3 h-3" />
          <span className={health.db === 'healthy' ? 'text-green-500' : 'text-red-500'}>DB</span>
        </div>
        
        <div className="flex items-center gap-2">
          <Server className="w-3 h-3" />
          <span className={health.redis === 'healthy' ? 'text-green-500' : 'text-red-500'}>REDIS</span>
        </div>

        <div className="flex items-center gap-2">
          <Activity className="w-3 h-3" />
          <span>WRK: {health.celery_workers}</span>
        </div>

        <div className="flex items-center gap-2">
          <Cpu className="w-3 h-3" />
          <span className={health.llm === 'available' ? 'text-green-500' : 'text-amber-500'}>LLM</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Clock className="w-3 h-3" />
        <span>SYNC: {new Date(health.last_sync).toLocaleTimeString()}</span>
      </div>
    </div>
  );
}
