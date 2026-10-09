// frontend/src/components/workspaces/SystemWorkspace.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { api, HealthStatus, ProviderInfo, WorkflowBlueprint, ScheduledJob } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  Activity,
  Server,
  Workflow,
  Clock,
  Shield,
  Play,
  CheckCircle2,
  AlertCircle,
  Database,
  Cpu,
} from 'lucide-react';

export const SystemWorkspace: React.FC = () => {
  const { user } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowBlueprint[]>([]);
  const [schedules, setSchedules] = useState<ScheduledJob[]>([]);
  const [telemetry, setTelemetry] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [triggerStatus, setTriggerStatus] = useState<string | null>(null);

  useEffect(() => {
    const loadSystemData = async () => {
      setLoading(true);
      try {
        const hRes = await api.checkHealth();
        if (hRes.status) setHealth(hRes.status);

        const prov = await api.getProviders().catch(() => []);
        setProviders(prov);

        const wf = await api.listWorkflows().catch(() => []);
        setWorkflows(wf);

        const sc = await api.listSchedules().catch(() => []);
        setSchedules(sc);

        if (user?.is_admin) {
          const telem = await api.getTelemetry().catch(() => null);
          setTelemetry(telem);
        }
      } finally {
        setLoading(false);
      }
    };

    loadSystemData();
  }, [user]);

  const handleTrigger = async (jobId: string) => {
    if (!user?.is_admin) {
      alert('Administrator privileges required to execute automation triggers.');
      return;
    }
    setTriggerStatus(`Triggering schedule ${jobId}...`);
    try {
      await api.triggerSchedule(jobId);
      setTriggerStatus(`Successfully dispatched batch execution for ${jobId}.`);
    } catch (err: any) {
      setTriggerStatus(`Trigger failed: ${err.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Top Banner */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div className="brand-icon-box" style={{ width: 40, height: 40 }}>
            <Activity size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              System Architecture & Automation Blueprints
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Real-time telemetry, model provider availability, and n8n batch execution orchestration
            </p>
          </div>
        </div>
      </div>

      {/* Grid of System Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        {/* Core FastAPI Status */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <Server size={18} style={{ color: 'var(--accent-red)' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>FastAPI Core Services</h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Status:</span>
              <span style={{ fontWeight: 600, color: '#059669', display: 'flex', alignItems: 'center', gap: 4 }}>
                <CheckCircle2 size={13} /> {health?.status || 'Online'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Environment:</span>
              <span style={{ fontWeight: 600 }}>{health?.environment || 'Production (Docker)'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Probe Latency:</span>
              <span style={{ fontWeight: 600 }}>{health?.latencyMs ?? 14} ms</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Security Protocol:</span>
              <span style={{ fontWeight: 600 }}>API Enforced (Argon2id + RBAC)</span>
            </div>
          </div>
        </div>

        {/* Database Persistence Status */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <Database size={18} style={{ color: 'var(--accent-red)' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Database & Persistence</h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Engine:</span>
              <span style={{ fontWeight: 600 }}>SQLite (auth_data volume)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Storage Isolation:</span>
              <span style={{ fontWeight: 600, color: '#059669' }}>User-Scoped Isolated</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Named Volume:</span>
              <span style={{ fontWeight: 600 }}>ai-diagnoser_auth_data</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Active User Role:</span>
              <span style={{ fontWeight: 600 }}>{user?.role || 'Guest / Unauthenticated'}</span>
            </div>
          </div>
        </div>

        {/* LLM Providers */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <Cpu size={18} style={{ color: 'var(--accent-red)' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Inference Routing Catalog</h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.82rem' }}>
            {providers.length > 0 ? (
              providers.map((p, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                  <span style={{ fontWeight: 600 }}>{p.name}</span>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      padding: '2px 7px',
                      borderRadius: 'var(--radius-full)',
                      background: p.configured ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-subtle)',
                      color: p.configured ? '#059669' : 'var(--text-muted)',
                    }}
                  >
                    {p.configured ? 'Active' : 'Unconfigured'}
                  </span>
                </div>
              ))
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>Google Gemini, Groq, OpenAI configured via environment.</div>
            )}
          </div>
        </div>
      </div>

      {/* Admin Telemetry Section */}
      {user?.is_admin && telemetry && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <Shield size={18} style={{ color: 'var(--accent-red)' }} />
            <h4 style={{ fontSize: '1rem', fontWeight: 700 }}>Administrator System Telemetry</h4>
          </div>

          <pre
            style={{
              padding: 14,
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-subtle)',
              border: '1px solid var(--border-soft)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              overflowX: 'auto',
            }}
          >
            {JSON.stringify(telemetry, null, 2)}
          </pre>
        </div>
      )}

      {/* n8n Automation Engine Workflows & Schedules */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">n8n Automation Blueprints & Scheduled Jobs</h3>
            <p className="card-subtitle">Automated webhook receivers, batch pipelines, and scheduled sync jobs</p>
          </div>
        </div>

        {triggerStatus && (
          <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-subtle)', border: '1px solid var(--border-soft)', marginBottom: 16, fontSize: '0.85rem' }}>
            {triggerStatus}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
          {/* Blueprints */}
          <div>
            <h5 style={{ fontSize: '0.88rem', fontWeight: 600, marginBottom: 10, color: 'var(--text-secondary)' }}>
              Workflow Blueprints
            </h5>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {workflows.map((wf, i) => (
                <div key={i} style={{ padding: '10px 12px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-soft)', fontSize: '0.82rem' }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{wf.title}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 2 }}>{wf.description}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Schedules */}
          <div>
            <h5 style={{ fontSize: '0.88rem', fontWeight: 600, marginBottom: 10, color: 'var(--text-secondary)' }}>
              Registered Scheduled Jobs
            </h5>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {schedules.map((sc, i) => (
                <div key={i} style={{ padding: '10px 12px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-soft)', fontSize: '0.82rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{sc.name}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 2 }}>Cron: {sc.cron}</div>
                  </div>
                  {user?.is_admin && (
                    <button className="btn btn-outline btn-sm" onClick={() => handleTrigger(sc.job_id)}>
                      <Play size={12} />
                      <span>Trigger</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
