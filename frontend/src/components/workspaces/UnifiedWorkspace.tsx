// frontend/src/components/workspaces/UnifiedWorkspace.tsx
'use client';

import React, { useState } from 'react';
import { DataWorkspace } from './DataWorkspace';
import { DocWorkspace } from './DocWorkspace';
import { ReportsWorkspace } from './ReportsWorkspace';
import { FileSpreadsheet, FileText, FileCheck } from 'lucide-react';

interface UnifiedWorkspaceProps {
  initialFile?: File | null;
  initialType?: 'data' | 'document' | 'reports' | 'vision';
  onSendToChat?: (text: string) => void;
}

export const UnifiedWorkspace: React.FC<UnifiedWorkspaceProps> = ({
  initialFile = null,
  initialType = 'data',
  onSendToChat,
}) => {
  const resolvedType = initialType === 'vision' ? 'document' : (initialType || 'data');
  const [activeTab, setActiveTab] = useState<'data' | 'document' | 'reports'>(
    resolvedType as 'data' | 'document' | 'reports'
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Tab Switcher */}
      <div className="tabs-nav" style={{ marginBottom: 12 }}>
        <button
          className={`tab-btn ${activeTab === 'data' ? 'active' : ''}`}
          onClick={() => setActiveTab('data')}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <FileSpreadsheet size={16} />
          <span>Tabular Data Diagnostics</span>
        </button>

        <button
          className={`tab-btn ${activeTab === 'document' ? 'active' : ''}`}
          onClick={() => setActiveTab('document')}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <FileText size={16} />
          <span>Document Intelligence</span>
        </button>

        <button
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
        >
          <FileCheck size={16} />
          <span>Diagnostic Reports</span>
        </button>
      </div>

      {/* Render active sub-workspace */}
      {activeTab === 'data' && (
        <DataWorkspace initialFile={initialType === 'data' ? initialFile : null} onSendToChat={onSendToChat} />
      )}
      {activeTab === 'document' && (
        <DocWorkspace initialFile={initialType === 'document' || initialType === 'vision' ? initialFile : null} />
      )}
      {activeTab === 'reports' && (
        <ReportsWorkspace />
      )}
    </div>
  );
};
