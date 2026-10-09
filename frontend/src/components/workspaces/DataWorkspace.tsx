// frontend/src/components/workspaces/DataWorkspace.tsx
'use client';

import React, { useState } from 'react';
import { api, DataProfileResult, CorrelationResult } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  FileSpreadsheet,
  Upload,
  BarChart2,
  Table,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  FileCheck,
  TrendingUp,
} from 'lucide-react';

interface DataWorkspaceProps {
  initialFile?: File | null;
  onSendToChat?: (text: string) => void;
}

export const DataWorkspace: React.FC<DataWorkspaceProps> = ({
  initialFile = null,
  onSendToChat,
}) => {
  const { user, openAuthModal } = useAuth();
  const [file, setFile] = useState<File | null>(initialFile);
  const [profile, setProfile] = useState<DataProfileResult | null>(null);
  const [correlation, setCorrelation] = useState<CorrelationResult | null>(null);
  const [insights, setInsights] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeSubTab, setActiveSubTab] = useState<'preview' | 'stats' | 'correlation' | 'ai'>('preview');
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (selectedFile: File) => {
    if (!user) {
      openAuthModal();
      return;
    }
    setFile(selectedFile);
    setLoading(true);
    setError(null);
    setProfile(null);
    setCorrelation(null);
    setInsights(null);

    try {
      const prof = await api.profileData(selectedFile);
      setProfile(prof);
    } catch (err: any) {
      setError(err.message || 'Failed to profile dataset.');
    } finally {
      setLoading(false);
    }
  };

  const handleComputeCorrelation = async () => {
    if (!file || !user) return;
    setLoading(true);
    try {
      const corr = await api.computeCorrelation(file);
      setCorrelation(corr);
      setActiveSubTab('correlation');
    } catch (err: any) {
      setError(err.message || 'Failed to compute correlation matrix.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInsights = async () => {
    if (!profile || !user) return;
    setLoading(true);
    try {
      // Build sample CSV string from head rows
      const headers = profile.columns.join(',');
      const rows = profile.head.map((r) => profile.columns.map((c) => JSON.stringify(r[c] ?? '')).join(',')).join('\n');
      const csvSnippet = `${headers}\n${rows}`;

      const res = await api.getDataInsights(csvSnippet, 'Generate executive insights and highlight risks');
      setInsights(res);
      setActiveSubTab('ai');
    } catch (err: any) {
      setError(err.message || 'Failed to generate AI insights.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* File Upload Banner */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div className="brand-icon-box" style={{ width: 40, height: 40 }}>
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {file ? file.name : 'Dataset Explorer & Profiler'}
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                {file ? `${(file.size / 1024).toFixed(1)} KB • In-memory diagnostic session` : 'Upload CSV or Excel files to extract column schemas and statistical insights'}
              </p>
            </div>
          </div>

          <label className="btn btn-outline" style={{ cursor: 'pointer' }}>
            <Upload size={15} />
            <span>{file ? 'Replace Dataset' : 'Upload Spreadsheet'}</span>
            <input
              type="file"
              style={{ display: 'none' }}
              accept=".csv,.xlsx,.xls"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
            />
          </label>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.12)', color: 'var(--accent-red)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239, 68, 68, 0.25)', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {loading && (
        <div className="card animate-pulse" style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>
          Computing high-performance statistical profiles across rows and columns...
        </div>
      )}

      {profile && !loading && (
        <>
          {/* Metrics summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Total Records</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {profile.row_count.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Observed row observations</div>
            </div>

            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Dimensions</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {profile.column_count} cols
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                {profile.numeric_columns.length} numeric, {profile.categorical_columns.length} categorical
              </div>
            </div>

            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Missing Values</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {Object.values(profile.missing_values).reduce((a, b) => a + b, 0)}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Null or NaN data points</div>
            </div>

            <div className="card" style={{ padding: 18, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={handleGenerateInsights} style={{ width: '100%' }}>
                <Sparkles size={14} />
                <span>AI Executive Insights</span>
              </button>
              <button className="btn btn-secondary btn-sm" onClick={handleComputeCorrelation} style={{ width: '100%' }}>
                <BarChart2 size={14} />
                <span>Correlation Matrix</span>
              </button>
            </div>
          </div>

          {/* Subtabs for data inspection */}
          <div className="card">
            <div className="tabs-nav">
              <button
                className={`tab-btn ${activeSubTab === 'preview' ? 'active' : ''}`}
                onClick={() => setActiveSubTab('preview')}
              >
                Sample Data Table
              </button>
              <button
                className={`tab-btn ${activeSubTab === 'stats' ? 'active' : ''}`}
                onClick={() => setActiveSubTab('stats')}
              >
                Column Distribution Stats
              </button>
              {correlation && (
                <button
                  className={`tab-btn ${activeSubTab === 'correlation' ? 'active' : ''}`}
                  onClick={() => setActiveSubTab('correlation')}
                >
                  Correlation Matrix
                </button>
              )}
              {insights && (
                <button
                  className={`tab-btn ${activeSubTab === 'ai' ? 'active' : ''}`}
                  onClick={() => setActiveSubTab('ai')}
                >
                  AI Insights Summary
                </button>
              )}
            </div>

            {/* SubTab 1: Table Preview */}
            {activeSubTab === 'preview' && (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      {profile.columns.map((col, idx) => (
                        <th key={idx}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {profile.head.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {profile.columns.map((col, cIdx) => (
                          <td key={cIdx}>{row[col] !== null ? String(row[col]) : <em style={{ opacity: 0.5 }}>null</em>}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* SubTab 2: Stats */}
            {activeSubTab === 'stats' && (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Mean</th>
                      <th>Std Dev</th>
                      <th>Min</th>
                      <th>Median</th>
                      <th>Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.numeric_columns.map((col, idx) => {
                      const st = profile.summary_statistics[col] || {};
                      return (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{col}</td>
                          <td>{st.mean !== undefined ? st.mean.toFixed(2) : '—'}</td>
                          <td>{st.std !== undefined ? st.std.toFixed(2) : '—'}</td>
                          <td>{st.min !== undefined ? st.min.toFixed(2) : '—'}</td>
                          <td>{st['50%'] !== undefined ? st['50%'].toFixed(2) : '—'}</td>
                          <td>{st.max !== undefined ? st.max.toFixed(2) : '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* SubTab 3: Correlation */}
            {activeSubTab === 'correlation' && correlation && (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      {correlation.columns.map((col, i) => (
                        <th key={i}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {correlation.columns.map((rowCol, rI) => (
                      <tr key={rI}>
                        <td style={{ fontWeight: 600 }}>{rowCol}</td>
                        {correlation.columns.map((colCol, cI) => {
                          const val = correlation.correlation_matrix[rowCol]?.[colCol] ?? 0;
                          const isHigh = Math.abs(val) > 0.7 && rowCol !== colCol;
                          return (
                            <td
                              key={cI}
                              style={{
                                color: isHigh ? 'var(--accent-red)' : 'var(--text-primary)',
                                fontWeight: isHigh ? 700 : 400,
                              }}
                            >
                              {val.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* SubTab 4: AI Insights */}
            {activeSubTab === 'ai' && insights && (
              <div style={{ padding: 16, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-soft)', whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: '0.92rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, fontWeight: 700, color: 'var(--accent-red)' }}>
                  <Sparkles size={18} />
                  <span>Executive Anomaly & Opportunity Findings</span>
                </div>
                {insights}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
