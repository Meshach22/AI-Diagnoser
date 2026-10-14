// frontend/src/components/layout/Sidebar.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Activity,
  Layers,
  ChevronRight,
  History,
  Sparkles,
} from 'lucide-react';

export type WorkspaceTab = 'chat' | 'unified';

interface SidebarProps {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const { user } = useAuth();
  const [historyDocs, setHistoryDocs] = useState<Array<{ id: string; filename: string }>>([]);
  const [historyChats, setHistoryChats] = useState<Array<{ id: string; content: string }>>([]);

  const navItems: { id: WorkspaceTab; label: string; icon: React.ReactNode }[] = [
    { id: 'chat', label: 'AI Chat Assistant', icon: <MessageSquare size={18} /> },
    { id: 'unified', label: 'Document Intelligence', icon: <FileText size={18} /> },
  ];

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const memKey = user?.email ? `ai_diagnoser_memory_${user.email}` : 'ai_diagnoser_memory_guest';
      const stored = localStorage.getItem(memKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed.uploadedDocs)) {
          setHistoryDocs(parsed.uploadedDocs.slice(0, 5));
        }
        if (Array.isArray(parsed.messages)) {
          const userQueries = parsed.messages.filter((m: any) => m.role === 'user').slice(-4).reverse();
          setHistoryChats(userQueries);
        }
      }
    } catch {
      // ignore
    }
  }, [user, activeTab]);

  return (
    <aside className="sidebar-container" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="nav-group">
        <div style={{ padding: '0 10px 14px 10px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
          WORKSPACE
        </div>

        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              {item.icon}
              <span style={{ flex: 1 }}>{item.label}</span>
              {isActive && <ChevronRight size={14} style={{ opacity: 0.8 }} />}
            </button>
          );
        })}
      </div>

      {/* Persistent Workspace History (ChatGPT / Gemini Style) */}
      {(historyDocs.length > 0 || historyChats.length > 0) && (
        <div className="nav-group" style={{ marginTop: 12, flex: 1, overflowY: 'auto' }}>
          <div style={{ padding: '0 10px 10px 10px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <History size={13} />
            <span>Workspace History</span>
          </div>

          {historyDocs.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ padding: '0 10px 6px 10px', fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                DOCUMENTS
              </div>
              {historyDocs.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => onTabChange('unified')}
                  className="nav-item"
                  style={{ fontSize: '0.82rem', padding: '7px 10px', gap: 8 }}
                  title={doc.filename}
                >
                  <FileText size={14} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'left', flex: 1 }}>
                    {doc.filename}
                  </span>
                </button>
              ))}
            </div>
          )}

          {historyChats.length > 0 && (
            <div>
              <div style={{ padding: '0 10px 6px 10px', fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                PAST CHATS
              </div>
              {historyChats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => onTabChange('chat')}
                  className="nav-item"
                  style={{ fontSize: '0.82rem', padding: '7px 10px', gap: 8 }}
                  title={chat.content}
                >
                  <Sparkles size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'left', flex: 1 }}>
                    {chat.content}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="sidebar-status-card" style={{ marginTop: 'auto' }}>
        <div className="status-row">
          <span className="status-dot" />
          <span>System Operational</span>
        </div>
        <div className="status-subtext">
          FastAPI Engine Active (v2.4)
        </div>
      </div>
    </aside>
  );
};
