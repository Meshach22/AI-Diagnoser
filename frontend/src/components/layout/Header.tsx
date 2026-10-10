// frontend/src/components/layout/Header.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';
import { api, HealthStatus } from '@/lib/api';
import { Activity, Sun, Moon, LogIn, LogOut, User as UserIcon, Shield } from 'lucide-react';

export const Header: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { user, logout, openAuthModal } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isWaking, setIsWaking] = useState<boolean>(false);

  // Probe backend health periodically (20s interval to avoid excessive traffic)
  useEffect(() => {
    let mounted = true;
    const probe = async () => {
      const res = await api.checkHealth();
      if (!mounted) return;
      setIsOnline(res.ok);
      setIsWaking(!!res.isWaking);
      if (res.ok && res.status) {
        setHealth(res.status);
        setLatency(res.latencyMs);
      } else {
        setLatency(null);
      }
    };

    probe();
    const interval = setInterval(probe, 20000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="header-bar">
      <div className="brand-wrapper">
        <div className="brand-icon-box">
          <Activity size={18} />
        </div>
        <div>
          <span className="brand-title">AI Data Analyst</span>
        </div>
        <span className="version-badge">v2.4</span>
      </div>

      <div className="header-actions">
        {/* Backend health status pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '5px 12px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--bg-subtle)',
            border: '1px solid var(--border-soft)',
            fontSize: '0.78rem',
            fontWeight: 600,
          }}
          title={
            isOnline
              ? `FastAPI core latency: ${latency}ms`
              : isWaking
                ? 'Backend service is waking up (Render cold start)...'
                : 'Backend offline or unreachable'
          }
        >
          <span
            className={`status-dot ${isOnline ? '' : isWaking ? 'waking' : 'offline'}`}
            style={isWaking ? { background: '#f59e0b', boxShadow: '0 0 6px rgba(245, 158, 11, 0.6)' } : undefined}
          />
          <span style={{ color: 'var(--text-secondary)' }}>
            {isOnline
              ? `Online ${latency ? `(${latency}ms)` : ''}`
              : isWaking
                ? 'Connecting...'
                : 'Offline'}
          </span>
        </div>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="btn btn-secondary btn-icon"
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>

        {/* Authentication button / Profile */}
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '4px 10px 4px 6px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-soft)',
                fontSize: '0.82rem',
                fontWeight: 600,
              }}
            >
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: '50%',
                  background: 'var(--accent-red)',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                }}
              >
                {user.name.charAt(0).toUpperCase()}
              </div>
              <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.name}
              </span>
              {user.is_admin && (
                <span title="Administrator" style={{ display: 'inline-flex', alignItems: 'center' }}>
                  <Shield size={13} style={{ color: 'var(--accent-red)' }} />
                </span>
              )}
            </div>

            <button
              onClick={logout}
              className="btn btn-outline btn-sm"
              title="Sign Out of Session"
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        ) : (
          <button onClick={openAuthModal} className="btn btn-primary btn-sm">
            <LogIn size={14} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
};
