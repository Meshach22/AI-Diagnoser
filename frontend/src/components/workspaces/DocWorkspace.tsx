// frontend/src/components/workspaces/DocWorkspace.tsx
'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api, DocumentParseResult } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  FileText,
  Upload,
  BookOpen,
  Sparkles,
  HelpCircle,
  CheckCircle,
  AlertTriangle,
  Lock,
  RefreshCw,
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

  // Track the exact File instance that was last ingested to prevent effect loops and duplicate processing
  const processedFileRef = useRef<File | null>(null);

  // Ingestion executor
  const executeIngestion = useCallback(async (targetFile: File) => {
    setLoading(true);
    setError(null);
    setParsed(null);
    setSummary(null);
    setQaAnswer(null);

    try {
      const res = await api.parseDocument(targetFile);
      setParsed(res);
    } catch (err: any) {
      setError(err.message || 'Failed to process document.');
      // Allow retry if this specific run failed
      processedFileRef.current = null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Synchronize incoming initialFile from props (e.g., when selected from HomeWorkspace)
  useEffect(() => {
    if (initialFile && initialFile !== file) {
      setFile(initialFile);
    }
  }, [initialFile, file]);

  // Trigger ingestion exactly once per new file when authenticated
  useEffect(() => {
    const activeFile = initialFile || file;
    if (!activeFile) return;

    // Already processed this file instance or currently loading
    if (processedFileRef.current === activeFile) return;

    // Authentication guard: if unauthenticated, retain file in state and wait for login
    if (!user) return;

    processedFileRef.current = activeFile;
    executeIngestion(activeFile);
  }, [initialFile, file, user, executeIngestion]);

  // Handler for manual file upload / replacement inside the workspace
  const handleManualUpload = (selectedFile: File) => {
    setFile(selectedFile);
    if (!user) {
      openAuthModal();
      return;
    }
    processedFileRef.current = selectedFile;
    executeIngestion(selectedFile);
  };

  const handleSummarize = async (type: string) => {
    const docText = parsed?.preview || parsed?.full_text;
    if (!docText || !user) return;
    setLoading(true);
    setSummaryType(type);
    try {
      const res = await api.summarizeDocument(docText, type);
      setSummary(res);
    } catch (err: any) {
      setError(err.message || 'Failed to generate summary.');
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    const docText = parsed?.preview || parsed?.full_text;
    if (!docText || !docQuestion.trim() || !user) return;
    setLoading(true);
    try {
      const res = await api.askDocument(docText, docQuestion.trim());
      setQaAnswer(res);
    } catch (err: any) {
      setError(err.message || 'Failed to answer question.');
    } finally {
      setLoading(false);
    }
  };

  const docTextAvailable = Boolean((parsed?.preview || parsed?.full_text)?.trim());

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
                {file
                  ? `${(file.size / 1024).toFixed(1)} KB • Structural text & page extraction`
                  : 'Upload PDF, Word (DOCX), or Plaintext corporate reports'}
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
              onChange={(e) => e.target.files?.[0] && handleManualUpload(e.target.files[0])}
            />
          </label>
        </div>
      </div>

      {/* Unauthenticated Notification */}
      {!user && file && (
        <div className="card" style={{ padding: 24, textAlign: 'center', background: 'var(--bg-subtle)' }}>
          <div style={{ maxWidth: 440, margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <Lock size={26} style={{ color: 'var(--accent-red)' }} />
            <h4 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Authentication Required
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Sign in or register to extract structured text, generate executive summaries, and query document contents.
            </p>
            <button className="btn btn-primary" onClick={openAuthModal}>
              Sign In to Analyze Document
            </button>
          </div>
        </div>
      )}

      {/* Error Banner with Retry */}
      {error && (
        <div style={{ padding: '14px 18px', background: 'rgba(239, 68, 68, 0.12)', color: 'var(--accent-red)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239, 68, 68, 0.25)', fontSize: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <span>{error}</span>
            {file && user && (
              <button
                className="btn btn-outline btn-sm"
                onClick={() => {
                  processedFileRef.current = null;
                  executeIngestion(file);
                }}
                disabled={loading}
              >
                <RefreshCw size={13} />
                <span>Retry Analysis</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="card animate-pulse" style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>
          Extracting document structure, pages, and textual content...
        </div>
      )}

      {/* Scanned PDF Warning (when no extractable text is present) */}
      {parsed && !loading && !docTextAvailable && (
        <div className="card" style={{ padding: 18, background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 'var(--radius-md)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#d97706', fontWeight: 600 }}>
            <AlertTriangle size={18} />
            <span>No Extractable Text Detected (Scanned PDF)</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.5 }}>
            This document appears to contain rasterized/scanned images without embedded digital text. Optical Character Recognition (OCR) is not currently implemented; please upload a digitally generated PDF, Microsoft Word (.docx), or plain text file to enable AI summarization and Q&amp;A.
          </p>
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
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                {(parsed.character_count ?? parsed.char_count ?? 0).toLocaleString()} characters
              </div>
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
                disabled={!docTextAvailable || loading}
              >
                <Sparkles size={14} />
                <span>Executive Overview</span>
              </button>
              <button
                className={`btn ${summaryType === 'key_takeaways' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => handleSummarize('key_takeaways')}
                disabled={!docTextAvailable || loading}
              >
                <BookOpen size={14} />
                <span>Key Takeaways</span>
              </button>
              <button
                className={`btn ${summaryType === 'action_items' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => handleSummarize('action_items')}
                disabled={!docTextAvailable || loading}
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
                placeholder={
                  docTextAvailable
                    ? 'e.g. What were the total operational expenditures mentioned in Section 3?'
                    : 'Text extraction required for Q&A...'
                }
                value={docQuestion}
                onChange={(e) => setDocQuestion(e.target.value)}
                disabled={!docTextAvailable || loading}
              />
              <button type="submit" className="btn btn-primary" disabled={!docQuestion.trim() || !docTextAvailable || loading}>
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
