// frontend/src/components/layout/Sidebar.tsx
'use client';

import React from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  BarChart3,
  FileText,
  Activity,
  Layers,
  ChevronRight,
} from 'lucide-react';

export type WorkspaceTab = 'home' | 'chat' | 'unified' | 'reports' | 'system';

interface SidebarProps {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const navItems: { id: WorkspaceTab; label: string; icon: React.ReactNode }[] = [
    { id: 'home', label: 'Home Workspace', icon: <LayoutDashboard size={18} /> },
    { id: 'chat', label: 'Chat with Data', icon: <MessageSquare size={18} /> },
    { id: 'unified', label: 'Unified Analysis', icon: <Layers size={18} /> },
    { id: 'reports', label: 'Reports & Artifacts', icon: <FileText size={18} /> },
    { id: 'system', label: 'System & Blueprints', icon: <Activity size={18} /> },
  ];

  return (
    <aside className="sidebar-container">
      <div className="nav-group">
        <div style={{ padding: '0 10px 14px 10px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
          Workspace Navigation
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

      <div className="sidebar-status-card">
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
