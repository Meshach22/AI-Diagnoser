// frontend/src/components/workspaces/DocWorkspace.tsx
'use client';

import React, { useState } from 'react';
import { api, DocumentParseResult } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  FileText,
  Upload,
  BookOpen,
  Sparkles,
  HelpCircle,
  CheckCircle,
  Layers,
  FileCheck2,
} from 'lucide-react';

interface DocWorkspaceProps {
  initialFile?: File | null;
}

export const DocWorkspace: React.FC<DocWorkspaceProps> = ({ initialFile = null }) => {
  const { user, openAuthModal } = useAuth();
  const [file, setFile] = useState<File | null>(initialFile);
  const [parsed, setParsed] = useState<DocumentParseResult | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryType, setSummaryType] = useState<string>('executive');
  const [docQuestion, setDocQuestion] = useState<string>('');
  const [qaAnswer, setQaAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (selectedFile: File) => {
    if (!user) {
      openAuthModal();
      return;
    }
    setFile(selectedFile);
    setLoading(true);
    setError(null);
    setParsed(null);
    setSummary(null);
    setQaAnswer(null);

    try {
      const res = await api.parseDocument(selectedFile);
      setParsed(res);
    } catch (err: any) {
      setError(err.message || 'Failed to parse document.');
    } finally {
      setLoading(false);
    }
  };

  const handleSummarize = async (type: string) => {
    if (!parsed || !user) return;
    setLoading(true);
    setSummaryType(type);
    try {
      const res = await api.summarizeDocument(parsed.preview, type);
      setSummary(res);
    } catch (err: any) {
      setError(err.message || 'Failed to generate summary.');
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!parsed || !docQuestion.trim() || !user) return;
    setLoading(true);
    try {
      const res = await api.askDocument(parsed.preview, docQuestion.trim());
      setQaAnswer(res);
    } catch (err: any) {
      setError(err.message || 'Failed to answer question.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Upload Header */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div className="brand-icon-box" style={{ width: 40, height: 40 }}>
              <FileText size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {file ? file.name : 'Document Intelligence & Synthesis'}
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                {file ? `${(file.size / 1024).toFixed(1)} KB • OCR and structural text extraction` : 'Upload PDF, Word (DOCX), or Plaintext corporate reports'}
              </p>
            </div>
          </div>

          <label className="btn btn-outline" style={{ cursor: 'pointer' }}>
            <Upload size={15} />
            <span>{file ? 'Replace Document' : 'Upload Document'}</span>
            <input
              type="file"
              style={{ display: 'none' }}
              accept=".pdf,.docx,.txt"
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
          Processing multi-page document structure, tokens, and semantic embeddings...
        </div>
      )}

      {parsed && !loading && (
        <>
          {/* Document Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Format</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {parsed.file_type.toUpperCase()}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Parsed file type</div>
            </div>

            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Page Count</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {parsed.page_count}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Rendered pages</div>
            </div>

            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Word Count</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {parsed.word_count.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>{parsed.character_count.toLocaleString()} characters</div>
            </div>
          </div>

          {/* Quick Action Summarization Buttons */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
              Executive AI Summarization Actions
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              <button
                className={`btn ${summaryType === 'executive' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => handleSummarize('executive')}
              >
                <Sparkles size={14} />
                <span>Executive Overview</span>
              </button>
              <button
                className={`btn ${summaryType === 'key_takeaways' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => handleSummarize('key_takeaways')}
              >
                <BookOpen size={14} />
                <span>Key Takeaways</span>
              </button>
              <button
                className={`btn ${summaryType === 'action_items' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => handleSummarize('action_items')}
              >
                <CheckCircle size={14} />
                <span>Action Items & Risks</span>
              </button>
            </div>

            {summary && (
              <div
                style={{
                  marginTop: 18,
                  padding: 16,
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-soft)',
                  lineHeight: 1.6,
                  fontSize: '0.92rem',
                  whiteSpace: 'pre-wrap',
                }}
              >
                <div style={{ fontWeight: 700, color: 'var(--accent-red)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Sparkles size={16} />
                  <span>Synthesized {summaryType.replace('_', ' ').toUpperCase()}</span>
                </div>
                {summary}
              </div>
            )}
          </div>

          {/* Document Q&A Box */}
          <div className="card">
            <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <HelpCircle size={17} style={{ color: 'var(--accent-red)' }} />
              <span>Ask Specific Questions Against This Document</span>
            </h4>
            <form onSubmit={handleAsk} style={{ display: 'flex', gap: 10 }}>
              <input
                type="text"
                className="input"
                placeholder="e.g. What were the total operational expenditures mentioned in Section 3?"
                value={docQuestion}
                onChange={(e) => setDocQuestion(e.target.value)}
              />
              <button type="submit" className="btn btn-primary" disabled={!docQuestion.trim() || loading}>
                <span>Ask AI</span>
              </button>
            </form>

            {qaAnswer && (
              <div
                style={{
                  marginTop: 16,
                  padding: 14,
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-soft)',
                  fontSize: '0.9rem',
                  lineHeight: 1.5,
                }}
              >
                <div style={{ fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>AI Answer:</div>
                {qaAnswer}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
