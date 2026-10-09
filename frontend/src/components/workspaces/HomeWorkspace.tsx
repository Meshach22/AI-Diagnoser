// frontend/src/components/workspaces/HomeWorkspace.tsx
'use client';

import React, { useRef, useState } from 'react';
import { WorkspaceTab } from '../layout/Sidebar';
import {
  UploadCloud,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  ArrowUp,
  TrendingUp,
  FileSearch,
  PieChart,
  BarChart,
  CheckCircle2,
  Clock,
  ExternalLink,
} from 'lucide-react';

interface HomeWorkspaceProps {
  onSelectTab: (tab: WorkspaceTab) => void;
  onFileLoaded: (file: File, type: 'data' | 'document' | 'vision') => void;
  onQuerySubmit: (query: string) => void;
}

export const HomeWorkspace: React.FC<HomeWorkspaceProps> = ({
  onSelectTab,
  onFileLoaded,
  onQuerySubmit,
}) => {
  const [query, setQuery] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const chips = [
    { label: 'Show key insights', prompt: 'Provide a comprehensive breakdown of the key executive insights, operational risks, and highest-priority opportunities.', icon: <BarChart size={14} /> },
    { label: 'Create a summary', prompt: 'Generate an executive briefing highlighting key metrics, strategic conclusions, and actionable recommendations.', icon: <FileText size={14} /> },
    { label: 'Find trends', prompt: 'Identify major statistical trends, growth trajectories, and abnormal patterns across the provided data.', icon: <TrendingUp size={14} /> },
    { label: 'Visualize this data', prompt: 'Recommend the top 3 statistical visualizations for this dataset and summarize key variable distributions.', icon: <PieChart size={14} /> },
    { label: 'Compare values', prompt: 'Perform a comparative variance analysis between high-performing segments and baseline averages.', icon: <FileSearch size={14} /> },
  ];

  const recentItems = [
    { name: 'sample_business_metrics.csv', type: 'data', time: '10 mins ago', size: '1.2 KB', status: 'Cataloged' },
    { name: 'sample_financial_report.txt', type: 'document', time: '1 hour ago', size: '2.4 KB', status: 'Analyzed' },
    { name: 'sample_performance_chart.png', type: 'vision', time: 'Yesterday', size: '6.0 KB', status: 'Diagnosed' },
  ];

  const handleFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (['csv', 'xlsx', 'xls', 'parquet'].includes(ext)) {
      onFileLoaded(file, 'data');
      onSelectTab('unified');
    } else if (['pdf', 'docx', 'doc', 'txt'].includes(ext)) {
      onFileLoaded(file, 'document');
      onSelectTab('unified');
    } else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
      onFileLoaded(file, 'vision');
      onSelectTab('unified');
    } else {
      onFileLoaded(file, 'data');
      onSelectTab('unified');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChipClick = (prompt: string) => {
    setQuery(prompt);
    onQuerySubmit(prompt);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onQuerySubmit(query.trim());
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      {/* Hero Welcome */}
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.025em', color: 'var(--text-primary)', marginBottom: 6 }}>
          What would you like to analyze today?
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          Multimodal intelligence for enterprise spreadsheets, financial documents, and visual telemetry.
        </p>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        className={`dropzone ${isDragging ? 'drag-active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          accept=".csv,.xlsx,.xls,.pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
        />
        <UploadCloud className="dropzone-icon" />
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)' }}>
          Drop datasets, reports, or charts here to begin analysis
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 18 }}>
          Supports CSV, Excel, PDF, Word, Plaintext, and Image telemetry
        </p>
        <button
          type="button"
          className="btn btn-outline"
          onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
        >
          Select from Computer
        </button>
      </div>

      {/* Question Input + Chips */}
      <div className="card">
        <form onSubmit={handleFormSubmit} style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input
            type="text"
            className="input"
            placeholder="Ask a diagnostic question about your data or operational files..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ fontSize: '0.95rem', padding: '12px 18px' }}
          />
          <button type="submit" className="btn btn-primary btn-icon" style={{ width: 46, height: 46, flexShrink: 0 }}>
            <ArrowUp size={18} />
          </button>
        </form>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {chips.map((chip, idx) => (
            <button
              key={idx}
              className="chip"
              onClick={() => handleChipClick(chip.prompt)}
              type="button"
            >
              {chip.icon}
              <span>{chip.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Recent Analyses List */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Recent Workspace Analyses</h3>
            <p className="card-subtitle">Persisted sessions and active multi-modal catalogs</p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => onSelectTab('unified')}>
            View All
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {recentItems.map((item, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-soft)',
                transition: 'background var(--transition-fast)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-soft)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent-red)',
                  }}
                >
                  {item.type === 'data' ? <FileSpreadsheet size={18} /> : item.type === 'document' ? <FileText size={18} /> : <ImageIcon size={18} />}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                    {item.name}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', gap: 10, marginTop: 2 }}>
                    <span>{item.size}</span>
                    <span>•</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={12} /> {item.time}
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-full)',
                    background: 'rgba(16, 185, 129, 0.12)',
                    color: '#059669',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <CheckCircle2 size={12} />
                  {item.status}
                </span>

                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => onSelectTab('unified')}
                >
                  <span>Explore</span>
                  <ExternalLink size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
