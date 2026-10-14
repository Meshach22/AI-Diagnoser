// frontend/src/components/workspaces/UnifiedWorkspace.tsx
'use client';

import React, { useState } from 'react';
import { DataWorkspace } from './DataWorkspace';
import { DocWorkspace } from './DocWorkspace';
import { FileSpreadsheet, FileText } from 'lucide-react';

interface UnifiedWorkspaceProps {
  initialFile?: File | null;
  initialType?: 'data' | 'document' | 'vision';
  onSendToChat?: (text: string) => void;
}

export const UnifiedWorkspace: React.FC<UnifiedWorkspaceProps> = ({
  initialFile = null,
  initialType = 'data',
  onSendToChat,
}) => {
  const resolvedType = initialType === 'vision' ? 'document' : (initialType || 'data');
  const [activeTab, setActiveTab] = useState<'data' | 'document'>(
    resolvedType as 'data' | 'document'
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
      </div>

      {/* Render active sub-workspace */}
      {activeTab === 'data' && (
        <DataWorkspace initialFile={initialType === 'data' ? initialFile : null} onSendToChat={onSendToChat} />
      )}
      {activeTab === 'document' && (
        <DocWorkspace initialFile={initialType === 'document' || initialType === 'vision' ? initialFile : null} />
      )}
    </div>
  );
};
