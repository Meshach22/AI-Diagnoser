// frontend/src/components/workspaces/ReportsWorkspace.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { api, ReportItem } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  FileText,
  Plus,
  Trash2,
  Download,
  Eye,
  Calendar,
  Lock,
  CheckCircle2,
  X,
  FileCode,
} from 'lucide-react';

export const ReportsWorkspace: React.FC = () => {
  const { user, openAuthModal } = useAuth();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New report creation modal state
  const [isCreateOpen, setIsCreateOpen] = useState<boolean>(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [reportType, setReportType] = useState('markdown');
  const [creating, setCreating] = useState(false);

  // Active view modal
  const [viewReport, setViewReport] = useState<ReportItem | null>(null);

  const fetchReports = async () => {
    if (!user) {
      setReports([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const items = await api.listReports();
      setReports(items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch cataloged reports.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [user]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim() || !user) return;
    setCreating(true);
    try {
      const newReport = await api.generateReport(title.trim(), content.trim(), reportType);
      setIsCreateOpen(false);
      setTitle('');
      setContent('');
      await fetchReports();
      setViewReport(newReport);
    } catch (err: any) {
      alert(err.message || 'Failed to synthesize report.');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (reportId: string) => {
    if (!confirm('Are you sure you want to permanently delete this diagnostic report?')) return;
    try {
      await api.deleteReport(reportId);
      if (viewReport?.report_id === reportId) {
        setViewReport(null);
      }
      setReports((prev) => prev.filter((r) => r.report_id !== reportId));
    } catch (err: any) {
      alert(err.message || 'Failed to delete report.');
    }
  };

  const handleDownload = (report: ReportItem) => {
    const element = document.createElement('a');
    const file = new Blob([report.content], { type: 'text/markdown;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `${report.title.toLowerCase().replace(/\s+/g, '_')}.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  if (!user) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
        <div className="brand-icon-box" style={{ width: 48, height: 48, margin: '0 auto 16px' }}>
          <Lock size={22} />
        </div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: 8, color: 'var(--text-primary)' }}>
          Session Authentication Required
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: 440, margin: '0 auto 24px' }}>
          Diagnostic reports and executive summaries are protected by user ownership isolation. Sign in to view and synthesize reports.
        </p>
        <button className="btn btn-primary" onClick={openAuthModal}>
          Sign In to Access Reports
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header Bar */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Diagnostic Reports Catalog
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Persistent SQLite catalog with authenticated owner isolation and export pipelines
            </p>
          </div>

          <button className="btn btn-primary btn-sm" onClick={() => setIsCreateOpen(true)}>
            <Plus size={15} />
            <span>Synthesize New Report</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.12)', color: 'var(--accent-red)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239, 68, 68, 0.25)', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {loading && (
        <div className="card animate-pulse" style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>
          Retrieving user-isolated persistent reports from SQLite backend...
        </div>
      )}

      {!loading && reports.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-secondary)' }}>
          <FileText size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
          <p style={{ fontWeight: 600, fontSize: '0.95rem' }}>No diagnostic reports generated yet.</p>
          <p style={{ fontSize: '0.82rem', marginTop: 4 }}>Run a dataset or document analysis, or click "Synthesize New Report".</p>
        </div>
      )}

      {/* Reports Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
        {reports.map((report) => (
          <div key={report.report_id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--accent-red-subtle)',
                    color: 'var(--accent-red)',
                    textTransform: 'uppercase',
                  }}
                >
                  {report.report_type}
                </span>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <Calendar size={12} />
                  <span>{new Date(report.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, lineHeight: 1.4 }}>
                {report.title}
              </h4>

              <p
                style={{
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  lineHeight: 1.5,
                }}
              >
                {report.content}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, paddingTop: 12, borderTop: '1px solid var(--border-soft)' }}>
              <button className="btn btn-outline btn-sm" onClick={() => setViewReport(report)}>
                <Eye size={13} />
                <span>View</span>
              </button>

              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-secondary btn-sm" onClick={() => handleDownload(report)} title="Download Markdown">
                  <Download size={13} />
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ color: '#DC2626' }}
                  onClick={() => handleDelete(report.report_id)}
                  title="Delete Report"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Report View Modal */}
      {viewReport && (
        <div className="modal-overlay" onClick={() => setViewReport(null)}>
          <div className="modal-content" style={{ maxWidth: 680, maxHeight: '85vh', display: 'flex', flexDirection: 'column' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {viewReport.title}
                </h3>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                  Report ID: {viewReport.report_id} • Created: {new Date(viewReport.created_at).toLocaleString()}
                </div>
              </div>
              <button className="btn btn-secondary btn-icon" onClick={() => setViewReport(null)}>
                <X size={16} />
              </button>
            </div>

            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: 18,
                background: 'var(--bg-subtle)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-soft)',
                fontSize: '0.92rem',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                fontFamily: viewReport.report_type === 'json' ? 'var(--font-mono)' : 'inherit',
              }}
            >
              {viewReport.content}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => handleDownload(viewReport)}>
                <Download size={14} />
                <span>Download .md</span>
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => setViewReport(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Report Modal */}
      {isCreateOpen && (
        <div className="modal-overlay" onClick={() => setIsCreateOpen(false)}>
          <div className="modal-content" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Synthesize Diagnostic Report
              </h3>
              <button className="btn btn-secondary btn-icon" onClick={() => setIsCreateOpen(false)}>
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Report Title
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="e.g. Q3 Financial Performance & Risk Evaluation"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Format
                </label>
                <select className="select" value={reportType} onChange={(e) => setReportType(e.target.value)}>
                  <option value="markdown">Markdown (.md)</option>
                  <option value="pdf">PDF Document (.pdf)</option>
                  <option value="docx">Microsoft Word (.docx)</option>
                  <option value="json">Structured JSON (.json)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Diagnostic Content & Findings
                </label>
                <textarea
                  className="textarea"
                  placeholder="Paste or write analytical executive findings, tables, and risk metrics..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  style={{ minHeight: 140 }}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsCreateOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={creating}>
                  {creating ? 'Synthesizing...' : 'Save & Catalog'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
