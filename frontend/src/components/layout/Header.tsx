// frontend/src/components/layout/Header.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';
import { api, HealthStatus } from '@/lib/api';
import {
  Activity,
  Sun,
  Moon,
  LogIn,
  LogOut,
  User as UserIcon,
  Shield,
  MessageSquare,
  FileText,
  Layers,
  X,
  History,
  Sparkles,
  ChevronRight,
} from 'lucide-react';

export type WorkspaceTab = 'chat' | 'unified';

interface HeaderProps {
  activeTab?: WorkspaceTab;
  onTabChange?: (tab: WorkspaceTab) => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab = 'chat', onTabChange }) => {
  const { theme, toggleTheme } = useTheme();
  const { user, logout, openAuthModal } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isWaking, setIsWaking] = useState<boolean>(false);

  // Sources & History Slide-over Drawer
  const [isSourcesDrawerOpen, setIsSourcesDrawerOpen] = useState(false);
  const [historyDocs, setHistoryDocs] = useState<Array<{ id: string; filename: string }>>([]);
  const [historyChats, setHistoryChats] = useState<Array<{ id: string; content: string }>>([]);

  // Probe backend health periodically (adaptive: 6s when waking/connecting, 20s when online)
  useEffect(() => {
    let mounted = true;
    let timerId: ReturnType<typeof setTimeout> | null = null;

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
      const nextDelay = res.ok ? 20000 : (res.isWaking ? 6000 : 15000);
      timerId = setTimeout(probe, nextDelay);
    };

    probe();
    return () => {
      mounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, []);

  // Sync workspace documents & history from persistent storage & events
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const loadHistory = () => {
      try {
        const memKey = user?.email ? `ai_diagnoser_memory_${user.email}` : 'ai_diagnoser_memory_guest';
        const stored = localStorage.getItem(memKey);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed.uploadedDocs)) {
            setHistoryDocs(parsed.uploadedDocs.slice(0, 10));
          } else {
            setHistoryDocs([]);
          }
          if (Array.isArray(parsed.messages)) {
            const userQueries = parsed.messages.filter((m: any) => m.role === 'user').slice(-5).reverse();
            setHistoryChats(userQueries);
          }
        } else {
          setHistoryDocs([]);
        }
      } catch {
        // ignore
      }
    };

    loadHistory();

    const handleSync = (e: any) => {
      const payload = e.detail;
      if (payload && Array.isArray(payload.uploadedDocs)) {
        setHistoryDocs(payload.uploadedDocs.slice(0, 10));
      }
      if (payload && Array.isArray(payload.messages)) {
        const userQueries = payload.messages.filter((m: any) => m.role === 'user').slice(-5).reverse();
        setHistoryChats(userQueries);
      }
    };

    window.addEventListener('ai_diagnoser_workspace_sync', handleSync);
    window.addEventListener('storage', loadHistory);

    if (user?.email) {
      api.getDocuments().then((serverDocs) => {
        if (serverDocs && serverDocs.length > 0) {
          setHistoryDocs((prev) => {
            const combined = [...serverDocs, ...prev];
            const uniqueMap = new Map<string, { id: string; filename: string }>();
            combined.forEach((d: any) => {
              const docId = (d && (d.id || d.filename)) ? String(d.id || d.filename) : '';
              if (docId && !uniqueMap.has(docId)) {
                uniqueMap.set(docId, { id: docId, filename: d.filename || 'document' });
              }
            });
            return Array.from(uniqueMap.values()).slice(0, 10);
          });
        }
      }).catch(() => {});
    }

    return () => {
      window.removeEventListener('ai_diagnoser_workspace_sync', handleSync);
      window.removeEventListener('storage', loadHistory);
    };
  }, [user]);

  return (
    <>
      <header className="header-bar">
        {/* Left: Brand Identity */}
        <div className="brand-wrapper">
          <div className="brand-icon-box">
            <Activity size={18} />
          </div>
          <div>
            <span className="brand-title">AI Data Analyst</span>
          </div>
          <span className="version-badge">v2.4</span>
        </div>

        {/* Center: Sleek Top Navigation Pill Switcher */}
        <div className="header-nav-pill">
          <button
            type="button"
            onClick={() => onTabChange?.('chat')}
            className={`header-nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
          >
            <MessageSquare size={14} />
            <span>AI Chat Assistant</span>
          </button>
          <button
            type="button"
            onClick={() => onTabChange?.('unified')}
            className={`header-nav-tab ${activeTab === 'unified' ? 'active' : ''}`}
          >
            <FileText size={14} />
            <span>Document Intelligence</span>
          </button>
        </div>

        {/* Right: Actions Cluster */}
        <div className="header-actions">
          {/* Workspace Sources Drawer Trigger */}
          <button
            type="button"
            onClick={() => setIsSourcesDrawerOpen(true)}
            className="btn btn-secondary btn-sm"
            style={{ gap: 6, padding: '5px 12px', borderRadius: 'var(--radius-full)' }}
            title="Open Workspace Sources & History"
          >
            <Layers size={14} style={{ color: 'var(--accent-red)' }} />
            <span className="header-action-label">Sources</span>
            {historyDocs.length > 0 && (
              <span
                style={{
                  fontSize: '0.72rem',
                  padding: '1px 6px',
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--accent-red)',
                  color: '#fff',
                  fontWeight: 700,
                }}
              >
                {historyDocs.length}
              </span>
            )}
          </button>

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
                ? `FastAPI engine: operational (${latency ? `${latency}ms` : 'ready'})`
                : isWaking
                  ? 'Backend service is waking up (Render cold start)...'
                  : 'Backend offline or unreachable'
            }
          >
            <span
              className={`status-dot ${isOnline ? '' : isWaking ? 'waking' : 'offline'}`}
              style={
                isOnline
                  ? { background: '#10b981', boxShadow: '0 0 6px rgba(16, 185, 129, 0.4)' }
                  : isWaking
                  ? { background: '#f59e0b', boxShadow: '0 0 6px rgba(245, 158, 11, 0.4)' }
                  : { background: '#ef4444', boxShadow: '0 0 6px rgba(239, 68, 68, 0.4)' }
              }
            />
            <span className="header-status-label" style={{ color: isOnline ? '#10b981' : isWaking ? '#f59e0b' : 'var(--text-secondary)' }}>
              {isOnline
                ? `Operational ${latency ? `(${latency}ms)` : ''}`
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
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt={user.name}
                    referrerPolicy="no-referrer"
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: '50%',
                      objectFit: 'cover',
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #4285F4 0%, #34A853 100%)',
                      color: '#fff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                    }}
                  >
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <span className="header-username" style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={user.name}>
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
                <span className="header-logout-label">Sign Out</span>
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

      {/* Sources & History Slide-over Drawer */}
      {isSourcesDrawerOpen && (
        <>
          <div
            className="sources-drawer-backdrop"
            onClick={() => setIsSourcesDrawerOpen(false)}
          />
          <aside className="sources-drawer">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Layers size={18} style={{ color: 'var(--accent-red)' }} />
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                  Workspace Sources
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsSourcesDrawerOpen(false)}
                className="btn btn-secondary btn-icon"
                style={{ width: 30, height: 30, borderRadius: '50%' }}
                title="Close"
              >
                <X size={15} />
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Documents Section */}
              <div>
                <div style={{ padding: '0 4px 8px 4px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
                  ACTIVE DOCUMENTS ({historyDocs.length})
                </div>
                {historyDocs.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {historyDocs.map((doc) => (
                      <button
                        key={doc.id}
                        type="button"
                        onClick={() => {
                          onTabChange?.('unified');
                          setIsSourcesDrawerOpen(false);
                        }}
                        className="nav-item"
                        style={{ fontSize: '0.82rem', padding: '8px 12px', gap: 8, borderRadius: 'var(--radius-sm)' }}
                        title={doc.filename}
                      >
                        <FileText size={15} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'left', flex: 1 }}>
                          {doc.filename}
                        </span>
                        <ChevronRight size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                      </button>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: '14px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-subtle)', border: '1px solid var(--border-soft)', fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                    No documents currently ingested. Upload in Document Intelligence to ground insights.
                  </div>
                )}
              </div>

              {/* Past Chats Section */}
              {historyChats.length > 0 && (
                <div>
                  <div style={{ padding: '0 4px 8px 4px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <History size={13} />
                    <span>RECENT INQUIRIES</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {historyChats.map((chat) => (
                      <button
                        key={chat.id}
                        type="button"
                        onClick={() => {
                          onTabChange?.('chat');
                          setIsSourcesDrawerOpen(false);
                        }}
                        className="nav-item"
                        style={{ fontSize: '0.82rem', padding: '8px 12px', gap: 8, borderRadius: 'var(--radius-sm)' }}
                        title={chat.content}
                      >
                        <Sparkles size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'left', flex: 1 }}>
                          {chat.content}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Quick Action Button */}
            <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--border-soft)' }}>
              <button
                type="button"
                onClick={() => {
                  onTabChange?.('unified');
                  setIsSourcesDrawerOpen(false);
                }}
                className="btn btn-primary"
                style={{ width: '100%', gap: 8 }}
              >
                <FileText size={15} />
                <span>Manage &amp; Upload Documents</span>
              </button>
            </div>
          </aside>
        </>
      )}
    </>
  );
};
