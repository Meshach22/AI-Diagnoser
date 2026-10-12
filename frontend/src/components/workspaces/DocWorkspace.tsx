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
  Send,
  Trash2,
  User,
} from 'lucide-react';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface DocWorkspaceProps {
  initialFile?: File | null;
}

export const DocWorkspace: React.FC<DocWorkspaceProps> = ({ initialFile = null }) => {
  const { user, openAuthModal } = useAuth();
  const [file, setFile] = useState<File | null>(initialFile);
  const [parsed, setParsed] = useState<DocumentParseResult | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryType, setSummaryType] = useState<string>('executive');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [docQuestion, setDocQuestion] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('Extracting document structure, pages, and textual content...');
  const [error, setError] = useState<string | null>(null);

  const chatScrollRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Track the exact File instance that was last ingested to prevent effect loops and duplicate processing
  const processedFileRef = useRef<File | null>(null);

  // Ingestion executor
  const executeIngestion = useCallback(async (targetFile: File) => {
    setLoading(true);
    setLoadingMessage('Extracting document structure, pages, and textual content...');
    setError(null);
    setParsed(null);
    setSummary(null);
    setMessages([]);
    setDocQuestion('');

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

  // Auto-scroll chat feed to newest message
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, chatLoading]);

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
    if (typeof window !== 'undefined') {
      try {
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = selectedFile.size > 0 ? Math.floor(Math.log(selectedFile.size) / Math.log(k)) : 0;
        const formattedSize = selectedFile.size > 0 ? parseFloat((selectedFile.size / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i] : '0 B';
        const newItem = {
          name: selectedFile.name,
          type: 'document' as const,
          time: 'Just now',
          size: formattedSize,
          status: 'Uploaded',
        };
        const stored = localStorage.getItem('ai_diagnoser_upload_history');
        const existing = stored ? JSON.parse(stored) : [];
        const updated = [newItem, ...existing.filter((item: any) => item.name !== selectedFile.name)].slice(0, 10);
        localStorage.setItem('ai_diagnoser_upload_history', JSON.stringify(updated));
      } catch {
        // ignore
      }
    }
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
    setLoadingMessage('Synthesizing executive insights with Gemini 3.8 Flash...');
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

  const handleClearChat = () => {
    setMessages([]);
    setDocQuestion('');
    chatInputRef.current?.focus();
  };

  const handleSendChat = async (promptOverride?: string) => {
    const query = (promptOverride || docQuestion).trim();
    const docText = parsed?.preview || parsed?.full_text;
    if (!query || !docText || !user || chatLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const currentThread = [...messages, userMsg];
    setMessages(currentThread);
    setDocQuestion('');
    setChatLoading(true);

    try {
      // Pass previous turns as history payload
      const historyPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const answer = await api.askDocument(docText, query, 'Google Gemini', historyPayload);

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages([...currentThread, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ Failed to get answer: ${err.message || 'Error communicating with model.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages([...currentThread, errorMsg]);
    } finally {
      setChatLoading(false);
    }
  };

  const formatInlineMarkdown = (text: string) => {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*.*?\*\*|`.*?`)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      const token = match[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(<strong key={match.index} style={{ fontWeight: 600 }}>{token.slice(2, -2)}</strong>);
      } else if (token.startsWith('`') && token.endsWith('`')) {
        parts.push(
          <code
            key={match.index}
            style={{
              background: 'var(--bg-elevated)',
              padding: '2px 5px',
              borderRadius: 4,
              fontSize: '0.88em',
              fontFamily: 'monospace',
            }}
          >
            {token.slice(1, -1)}
          </code>
        );
      }
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }
    return parts.length > 0 ? parts : text;
  };

  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) {
            return <div key={idx} style={{ height: 6 }} />;
          }
          if (trimmed.startsWith('### ')) {
            return (
              <h4 key={idx} style={{ fontSize: '0.98rem', fontWeight: 700, margin: '8px 0 2px', color: 'var(--text-primary)' }}>
                {trimmed.substring(4)}
              </h4>
            );
          }
          if (trimmed.startsWith('## ')) {
            return (
              <h3 key={idx} style={{ fontSize: '1.05rem', fontWeight: 700, margin: '10px 0 3px', color: 'var(--text-primary)' }}>
                {trimmed.substring(3)}
              </h3>
            );
          }
          if (trimmed.startsWith('# ')) {
            return (
              <h2 key={idx} style={{ fontSize: '1.15rem', fontWeight: 800, margin: '12px 0 4px', color: 'var(--text-primary)' }}>
                {trimmed.substring(2)}
              </h2>
            );
          }
          if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
            return (
              <div key={idx} style={{ display: 'flex', gap: 8, paddingLeft: 4, alignItems: 'flex-start' }}>
                <span style={{ color: 'var(--accent-red)', fontWeight: 700 }}>•</span>
                <span style={{ flex: 1 }}>{formatInlineMarkdown(trimmed.substring(2))}</span>
              </div>
            );
          }
          const matchNum = trimmed.match(/^(\d+)\.\s+(.*)/);
          if (matchNum) {
            return (
              <div key={idx} style={{ display: 'flex', gap: 8, paddingLeft: 4, alignItems: 'flex-start' }}>
                <span style={{ color: 'var(--accent-red)', fontWeight: 700 }}>{matchNum[1]}.</span>
                <span style={{ flex: 1 }}>{formatInlineMarkdown(matchNum[2])}</span>
              </div>
            );
          }
          return (
            <p key={idx} style={{ margin: 0, lineHeight: 1.6 }}>
              {formatInlineMarkdown(line)}
            </p>
          );
        })}
      </div>
    );
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
          {loadingMessage}
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

          {/* NotebookLM-Style Multi-Turn Document Chat */}
          <div className="card" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {/* Thread Header */}
            <div
              style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--border-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 12,
                background: 'var(--bg-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div className="brand-icon-box" style={{ width: 34, height: 34 }}>
                  <Sparkles size={17} />
                </div>
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                    NotebookLM Document Companion
                  </h4>
                  <p style={{ fontSize: '0.78rem', margin: 0, color: 'var(--text-secondary)' }}>
                    Grounded conversational analysis with multi-turn memory
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {messages.length > 0 && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handleClearChat}
                    style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6 }}
                    title="Clear current conversation thread"
                  >
                    <Trash2 size={13} />
                    <span>Clear Chat</span>
                  </button>
                )}
              </div>
            </div>

            {/* Scrollable Conversation Feed */}
            <div
              ref={chatScrollRef}
              style={{
                minHeight: '280px',
                maxHeight: '480px',
                overflowY: 'auto',
                padding: 20,
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
                background: 'var(--bg-elevated)',
              }}
            >
              {messages.length === 0 ? (
                <div style={{ textAlign: 'center', margin: 'auto', padding: '32px 16px', maxWidth: 540 }}>
                  <HelpCircle size={36} style={{ margin: '0 auto 12px', color: 'var(--accent-red)', opacity: 0.8 }} />
                  <h5 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                    Ask Anything Grounded in This Document
                  </h5>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.5 }}>
                    Engage in a continuous multi-turn dialogue. Ask proportional questions, request clarifications, or drill into specific projects and metrics.
                  </p>

                  {/* Starter Chips */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                    {[
                      'What is in this document?',
                      'What are the core technical projects and impact?',
                      'What is his primary educational background?',
                      'Summarize key strengths in 3 bullet points',
                    ].map((chipPrompt, idx) => (
                      <button
                        key={idx}
                        type="button"
                        className="chip"
                        onClick={() => handleSendChat(chipPrompt)}
                        disabled={!docTextAvailable || chatLoading}
                        style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                      >
                        <Sparkles size={12} style={{ color: 'var(--accent-red)' }} />
                        <span>{chipPrompt}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((m) => {
                  const isUser = m.role === 'user';
                  return (
                    <div
                      key={m.id}
                      style={{
                        display: 'flex',
                        gap: 10,
                        alignSelf: isUser ? 'flex-end' : 'flex-start',
                        maxWidth: '85%',
                        flexDirection: isUser ? 'row-reverse' : 'row',
                      }}
                    >
                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: 'var(--radius-sm)',
                          background: isUser ? 'var(--accent-red)' : 'var(--accent-red-subtle)',
                          color: isUser ? '#FFFFFF' : 'var(--accent-red)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        {isUser ? <User size={16} /> : <Sparkles size={16} />}
                      </div>

                      <div
                        style={{
                          background: isUser ? 'var(--accent-red)' : 'var(--bg-subtle)',
                          color: isUser ? '#FFFFFF' : 'var(--text-primary)',
                          padding: '12px 16px',
                          borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                          border: isUser ? 'none' : '1px solid var(--border-soft)',
                          fontSize: '0.92rem',
                          lineHeight: 1.5,
                          boxShadow: 'var(--shadow-card)',
                        }}
                      >
                        {isUser ? (
                          <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
                        ) : (
                          renderFormattedText(m.content)
                        )}

                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: isUser ? 'flex-end' : 'space-between',
                            gap: 10,
                            marginTop: 8,
                            fontSize: '0.72rem',
                            opacity: 0.75,
                          }}
                        >
                          {!isUser && <span>Grounded in Document</span>}
                          <span>{m.timestamp}</span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}

              {/* Chat loading bubble */}
              {chatLoading && (
                <div style={{ display: 'flex', gap: 10, alignSelf: 'flex-start', maxWidth: '85%' }}>
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--accent-red-subtle)',
                      color: 'var(--accent-red)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Sparkles size={16} />
                  </div>
                  <div
                    style={{
                      background: 'var(--bg-subtle)',
                      padding: '12px 16px',
                      borderRadius: '16px 16px 16px 4px',
                      border: '1px solid var(--border-soft)',
                      fontSize: '0.88rem',
                      color: 'var(--text-secondary)',
                      fontStyle: 'italic',
                    }}
                  >
                    Analyzing document context and synthesizing response...
                  </div>
                </div>
              )}
            </div>

            {/* Sticky Bottom Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendChat();
              }}
              style={{
                padding: '14px 18px',
                borderTop: '1px solid var(--border-soft)',
                display: 'flex',
                gap: 10,
                background: 'var(--bg-surface)',
              }}
            >
              <input
                ref={chatInputRef}
                type="text"
                className="input"
                placeholder={
                  docTextAvailable
                    ? 'Ask a follow-up question (e.g. "what about his degree?", "summarize in 2 lines")...'
                    : 'Text extraction required for document Q&A...'
                }
                value={docQuestion}
                onChange={(e) => setDocQuestion(e.target.value)}
                disabled={!docTextAvailable || chatLoading}
                style={{ fontSize: '0.92rem' }}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!docQuestion.trim() || !docTextAvailable || chatLoading}
                style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}
              >
                <Send size={15} />
                <span>Send</span>
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
};
