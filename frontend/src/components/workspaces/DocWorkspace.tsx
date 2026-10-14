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
  Plus,
  Layers,
  FileCheck,
  Clock,
} from 'lucide-react';

export interface UploadedDoc {
  id: string;
  filename: string;
  full_text: string;
  preview?: string;
  word_count: number;
  page_count: number;
  format: string;
  uploadedAt: string;
}

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
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [activeDocId, setActiveDocId] = useState<string | 'all'>('all');
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryType, setSummaryType] = useState<string>('executive');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [docQuestion, setDocQuestion] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('Analyzing document intelligence...');
  const [error, setError] = useState<string | null>(null);

  const chatScrollRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Track ingested file to prevent duplicate processing
  const processedFileRef = useRef<File | null>(null);

  // Helper: Memory persistence key
  const getMemoryKey = useCallback(() => {
    return user?.email ? `ai_diagnoser_memory_${user.email}` : 'ai_diagnoser_memory_guest';
  }, [user?.email]);

  // Save workspace memory to localStorage and backend
  const persistMemory = useCallback(
    (
      docsToSave: UploadedDoc[],
      msgsToSave: ChatMessage[],
      summaryToSave: string | null,
      activeIdToSave: string | 'all',
      typeToSave: string
    ) => {
      if (typeof window === 'undefined') return;
      const memKey = getMemoryKey();
      const memoryPayload = {
        uploadedDocs: docsToSave,
        messages: msgsToSave,
        summary: summaryToSave,
        activeDocId: activeIdToSave,
        summaryType: typeToSave,
        updatedAt: new Date().toISOString(),
      };

      try {
        localStorage.setItem(memKey, JSON.stringify(memoryPayload));
      } catch (err) {
        console.warn('Failed to save to localStorage:', err);
      }

      // Sync to backend if authenticated
      if (user) {
        api.saveWorkspaceMemory(memoryPayload).catch(() => { });
      }
    },
    [getMemoryKey, user]
  );

  // Restore memory on user sign-in or initial mount
  useEffect(() => {
    let isMounted = true;

    const restoreMemory = async () => {
      if (typeof window === 'undefined') return;
      const memKey = getMemoryKey();
      let restoredData: any = null;

      // 1. Try local storage first for instant load
      try {
        const localRaw = localStorage.getItem(memKey);
        if (localRaw) {
          restoredData = JSON.parse(localRaw);
        }
      } catch {
        // ignore
      }

      // 2. If authenticated, fetch latest from backend
      if (user) {
        try {
          const backendMem = await api.getWorkspaceMemory();
          if (backendMem && Array.isArray(backendMem.uploadedDocs) && backendMem.uploadedDocs.length > 0) {
            restoredData = backendMem;
            localStorage.setItem(memKey, JSON.stringify(backendMem));
          } else {
            // Also check SQLite user_documents table
            const serverDocs = await api.getUserDocuments();
            if (serverDocs && serverDocs.length > 0) {
              const mappedDocs: UploadedDoc[] = serverDocs.map((d: any) => ({
                id: d.id,
                filename: d.filename,
                full_text: d.full_text || d.preview || '',
                word_count: d.word_count || 0,
                page_count: d.page_count || 1,
                format: d.format || 'text',
                uploadedAt: new Date(d.created_at ? d.created_at * 1000 : Date.now()).toISOString(),
              }));
              restoredData = {
                uploadedDocs: mappedDocs,
                messages: (restoredData && restoredData.messages) || [],
                summary: (restoredData && restoredData.summary) || null,
                activeDocId: 'all',
                summaryType: 'executive',
              };
              localStorage.setItem(memKey, JSON.stringify(restoredData));
            }
          }
        } catch {
          // ignore
        }
      }

      if (isMounted && restoredData && Array.isArray(restoredData.uploadedDocs) && restoredData.uploadedDocs.length > 0) {
        setUploadedDocs(restoredData.uploadedDocs);
        setActiveDocId(restoredData.activeDocId || 'all');
        if (Array.isArray(restoredData.messages)) {
          setMessages(restoredData.messages);
        }
        if (restoredData.summary) {
          setSummary(restoredData.summary);
        }
        if (restoredData.summaryType) {
          setSummaryType(restoredData.summaryType);
        }
      }
    };

    restoreMemory();
    return () => {
      isMounted = false;
    };
  }, [user, getMemoryKey]);

  // Execute document ingestion and append to uploadedDocs
  const executeIngestion = useCallback(
    async (targetFile: File) => {
      setLoading(true);
      setLoadingMessage(`Extracting textual structure & tables from "${targetFile.name}"...`);
      setError(null);

      try {
        const res: DocumentParseResult = await api.parseDocument(targetFile);
        const fullText = (res.full_text || res.preview || '').trim();
        const wordCount = res.word_count || (fullText ? fullText.split(/\s+/).length : 0);
        const pageCount = res.page_count || 1;
        const format = (res.file_type || targetFile.name.split('.').pop() || 'TXT').toUpperCase();

        const newDoc: UploadedDoc = {
          id: `doc-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
          filename: targetFile.name,
          full_text: fullText,
          word_count: wordCount,
          page_count: pageCount,
          format,
          uploadedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        setUploadedDocs((prevDocs) => {
          // Replace document with same filename if re-uploaded, else append
          const filtered = prevDocs.filter((d) => d.filename !== targetFile.name);
          const updated = [...filtered, newDoc];
          const newActiveId = updated.length > 1 ? 'all' : newDoc.id;
          setActiveDocId(newActiveId);

          persistMemory(updated, messages, summary, newActiveId, summaryType);

          // Update upload history for HomeWorkspace & Sidebar
          if (typeof window !== 'undefined') {
            try {
              const k = 1024;
              const sizes = ['B', 'KB', 'MB', 'GB'];
              const i = targetFile.size > 0 ? Math.floor(Math.log(targetFile.size) / Math.log(k)) : 0;
              const formattedSize =
                targetFile.size > 0 ? parseFloat((targetFile.size / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i] : '0 B';
              const newItem = {
                name: targetFile.name,
                type: 'document' as const,
                time: 'Just now',
                size: formattedSize,
                status: 'Uploaded',
              };
              const stored = localStorage.getItem('ai_diagnoser_upload_history');
              const existing = stored ? JSON.parse(stored) : [];
              const updatedHistory = [newItem, ...existing.filter((item: any) => item.name !== targetFile.name)].slice(0, 10);
              localStorage.setItem('ai_diagnoser_upload_history', JSON.stringify(updatedHistory));
            } catch {
              // ignore
            }
          }

          return updated;
        });
      } catch (err: any) {
        setError(err.message || `Failed to process document "${targetFile.name}".`);
        processedFileRef.current = null;
      } finally {
        setLoading(false);
      }
    },
    [messages, persistMemory, summary, summaryType]
  );

  // Auto-scroll chat feed to newest message
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, chatLoading]);

  // Handle incoming initialFile from props (e.g., from HomeWorkspace)
  useEffect(() => {
    if (!initialFile) return;
    if (processedFileRef.current === initialFile) return;

    if (!user) {
      // If unauthenticated, prompt login
      openAuthModal();
      return;
    }

    processedFileRef.current = initialFile;
    executeIngestion(initialFile);
  }, [initialFile, user, executeIngestion, openAuthModal]);

  // Handle file uploads (both new doc and add doc)
  const handleFileUpload = (selectedFile: File) => {
    if (!user) {
      openAuthModal();
      return;
    }
    processedFileRef.current = selectedFile;
    executeIngestion(selectedFile);
  };

  // Remove an uploaded document
  const handleRemoveDoc = (docId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setUploadedDocs((prevDocs) => {
      const remaining = prevDocs.filter((d) => d.id !== docId);
      const nextActiveId = remaining.length === 0 ? 'all' : activeDocId === docId ? (remaining.length > 1 ? 'all' : remaining[0].id) : activeDocId;
      setActiveDocId(nextActiveId);
      persistMemory(remaining, messages, summary, nextActiveId, summaryType);
      return remaining;
    });
  };

  // Compute active document text context
  const getContextForAnalysis = useCallback((): { text: string; label: string; docCount: number } => {
    if (uploadedDocs.length === 0) {
      return { text: '', label: 'No documents', docCount: 0 };
    }

    if (activeDocId === 'all' || uploadedDocs.length === 1) {
      if (uploadedDocs.length === 1) {
        return {
          text: uploadedDocs[0].full_text,
          label: uploadedDocs[0].filename,
          docCount: 1,
        };
      }
      // Combine multiple documents with explicit labels
      const combined = uploadedDocs
        .map((doc, idx) => {
          return `=== Document ${idx + 1}: ${doc.filename} (Format: ${doc.format}, Pages: ${doc.page_count}, Words: ${doc.word_count}) ===\n${doc.full_text}`;
        })
        .join('\n\n----------------------------------------\n\n');
      return {
        text: combined,
        label: `All ${uploadedDocs.length} Documents Combined`,
        docCount: uploadedDocs.length,
      };
    }

    const selected = uploadedDocs.find((d) => d.id === activeDocId) || uploadedDocs[0];
    return {
      text: selected.full_text,
      label: selected.filename,
      docCount: 1,
    };
  }, [activeDocId, uploadedDocs]);

  // Summarize documents
  const handleSummarize = async (type: string) => {
    const { text: docText, label } = getContextForAnalysis();
    if (!docText || !user) return;
    setLoading(true);
    setLoadingMessage(`Synthesizing ${type.replace('_', ' ')} across "${label}"...`);
    setSummaryType(type);

    try {
      const res = await api.summarizeDocument(docText, type, 'Google Gemini');
      setSummary(res);
      persistMemory(uploadedDocs, messages, res, activeDocId, type);
    } catch (err: any) {
      setError(err.message || 'Failed to generate summary.');
    } finally {
      setLoading(false);
    }
  };

  // Clear Chat conversation
  const handleClearChat = () => {
    setMessages([]);
    setDocQuestion('');
    persistMemory(uploadedDocs, [], summary, activeDocId, summaryType);
    chatInputRef.current?.focus();
  };

  // Send query to AI Chat Assistant
  const handleSendChat = async (promptOverride?: string) => {
    const query = (promptOverride || docQuestion).trim();
    const { text: docText } = getContextForAnalysis();
    if (!query || !docText || !user || chatLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const assistantMsgId = `assistant-${Date.now()}`;
    const initialAssistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const currentThread = [...messages, userMsg, initialAssistantMsg];
    setMessages(currentThread);
    setDocQuestion('');
    setChatLoading(true);

    let streamedText = '';
    let promptToSend = query;

    // Multi-source cross-document grounding: bundle ALL uploaded documents
    if (uploadedDocs.length > 0) {
      const sourcesBlock = uploadedDocs
        .map((doc, idx) => {
          const title = doc.filename || `Source_${idx + 1}`;
          const content = (doc.full_text || doc.preview || '').trim().slice(0, 25000);
          return `--- Source ${idx + 1}: ${title} ---\n${content}`;
        })
        .join('\n\n');

      promptToSend = `[GROUNDED SOURCES KNOWLEDGE BASE]\n${sourcesBlock}\n-------------------------------\nUser Query: ${query}`;
    } else {
      const cappedContext = docText.slice(0, 30000);
      promptToSend = `[GROUNDED SOURCES KNOWLEDGE BASE]\n--- Source 1: Active Document ---\n${cappedContext}\n-------------------------------\nUser Query: ${query}`;
    }

    try {
      await api.streamRouter(
        promptToSend,
        'Google Gemini',
        'gemini-3.8-flash',
        (token: string) => {
          streamedText += token;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, content: streamedText } : msg
            )
          );
        }
      );

      setMessages((prev) => {
        const updated = prev.map((msg) =>
          msg.id === assistantMsgId
            ? { ...msg, content: streamedText || 'No response returned from model.' }
            : msg
        );
        persistMemory(uploadedDocs, updated, summary, activeDocId, summaryType);
        return updated;
      });
    } catch (err: any) {
      if (!streamedText) {
        try {
          const answer = await api.askDocument(docText, query, 'Google Gemini', undefined, 'gemini-3.8-flash');
          setMessages((prev) => {
            const updated = prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, content: answer } : msg
            );
            persistMemory(uploadedDocs, updated, summary, activeDocId, summaryType);
            return updated;
          });
        } catch (unaryErr: any) {
          setMessages((prev) => {
            const updated = prev.map((msg) =>
              msg.id === assistantMsgId
                ? { ...msg, content: `⚠️ Failed to get answer: ${unaryErr.message || err.message}` }
                : msg
            );
            persistMemory(uploadedDocs, updated, summary, activeDocId, summaryType);
            return updated;
          });
        }
      } else {
        setMessages((prev) => {
          persistMemory(uploadedDocs, prev, summary, activeDocId, summaryType);
          return prev;
        });
      }
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

  const { text: activeContextText, label: activeLabel, docCount: activeDocCount } = getContextForAnalysis();
  const docTextAvailable = Boolean(activeContextText.trim());

  // Aggregate metrics
  const totalPages = uploadedDocs.reduce((acc, d) => acc + d.page_count, 0);
  const totalWords = uploadedDocs.reduce((acc, d) => acc + d.word_count, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Upload Header Card */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div className="brand-icon-box" style={{ width: 42, height: 42 }}>
              <Layers size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Document Intelligence &amp; Multi-File Analysis
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                {uploadedDocs.length > 0
                  ? `${uploadedDocs.length} document${uploadedDocs.length > 1 ? 's' : ''} loaded • Cross-document reasoning & persistent synthesis`
                  : 'Upload PDF, Word (DOCX), or Plaintext corporate reports to analyze'}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: 'none' }}
              accept=".pdf,.docx,.txt"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFileUpload(f);
                if (e.target) e.target.value = '';
              }}
            />

            <button
              type="button"
              className="btn btn-primary"
              onClick={() => fileInputRef.current?.click()}
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              {uploadedDocs.length > 0 ? <Plus size={16} /> : <Upload size={16} />}
              <span>{uploadedDocs.length > 0 ? 'Add Document' : 'Upload Document'}</span>
            </button>
          </div>
        </div>

        {/* Multi-Document Selectable Chips / Cards */}
        {uploadedDocs.length > 0 && (
          <div
            style={{
              marginTop: 18,
              paddingTop: 16,
              borderTop: '1px solid var(--border-soft)',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                Active Document Scope
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Currently analyzing: <strong>{activeLabel}</strong>
              </span>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
              {/* Option to view/analyze all documents together */}
              <button
                type="button"
                onClick={() => setActiveDocId('all')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '7px 14px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: activeDocId === 'all' ? '2px solid var(--accent-red)' : '1px solid var(--border-medium)',
                  background: activeDocId === 'all' ? 'var(--accent-red-subtle)' : 'var(--bg-elevated)',
                  color: activeDocId === 'all' ? 'var(--accent-red)' : 'var(--text-primary)',
                  transition: 'all 0.15s ease',
                }}
              >
                <Layers size={15} />
                <span>All Uploaded Documents</span>
                <span
                  style={{
                    fontSize: '0.74rem',
                    padding: '1px 6px',
                    borderRadius: 10,
                    background: activeDocId === 'all' ? 'var(--accent-red)' : 'var(--bg-subtle)',
                    color: activeDocId === 'all' ? '#FFFFFF' : 'var(--text-muted)',
                  }}
                >
                  {uploadedDocs.length}
                </span>
              </button>

              {/* Individual Document Chips */}
              {uploadedDocs.map((d) => {
                const isActive = activeDocId === d.id;
                return (
                  <div
                    key={d.id}
                    onClick={() => setActiveDocId(d.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '7px 12px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.85rem',
                      fontWeight: 500,
                      cursor: 'pointer',
                      border: isActive ? '2px solid var(--accent-red)' : '1px solid var(--border-medium)',
                      background: isActive ? 'var(--accent-red-subtle)' : 'var(--bg-elevated)',
                      color: isActive ? 'var(--accent-red)' : 'var(--text-primary)',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <FileText size={14} />
                    <span style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={d.filename}>
                      {d.filename}
                    </span>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      ({d.page_count}p)
                    </span>
                    <button
                      type="button"
                      onClick={(e) => handleRemoveDoc(d.id, e)}
                      title="Remove document"
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '2px',
                        display: 'flex',
                        alignItems: 'center',
                        color: 'var(--text-muted)',
                      }}
                      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--accent-red)')}
                      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-muted)')}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Unauthenticated Notification */}
      {!user && uploadedDocs.length > 0 && (
        <div className="card" style={{ padding: 24, textAlign: 'center', background: 'var(--bg-subtle)' }}>
          <div style={{ maxWidth: 440, margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <Lock size={26} style={{ color: 'var(--accent-red)' }} />
            <h4 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Authentication Required
            </h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Sign in or register to enable AI cross-document reasoning, multi-turn memory, and executive summaries.
            </p>
            <button className="btn btn-primary" onClick={openAuthModal}>
              Sign In to Analyze Documents
            </button>
          </div>
        </div>
      )}

      {/* Error Banner with Retry */}
      {error && (
        <div
          style={{
            padding: '14px 18px',
            background: 'rgba(239, 68, 68, 0.12)',
            color: 'var(--accent-red)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            fontSize: '0.85rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <span>{error}</span>
            <button
              className="btn btn-outline btn-sm"
              onClick={() => {
                setError(null);
                if (fileInputRef.current) fileInputRef.current.click();
              }}
            >
              <RefreshCw size={13} />
              <span>Retry / Re-upload</span>
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="card animate-pulse" style={{ padding: 32, textAlign: 'center', color: 'var(--text-secondary)' }}>
          {loadingMessage}
        </div>
      )}

      {uploadedDocs.length > 0 && !loading && (
        <>
          {/* Document Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Scope</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {activeDocId === 'all' ? `${uploadedDocs.length} Documents` : 'Single File'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                {activeDocId === 'all' ? 'Cross-document reasoning' : activeLabel}
              </div>
            </div>

            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Pages</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {activeDocId === 'all'
                  ? totalPages
                  : (uploadedDocs.find((d) => d.id === activeDocId)?.page_count || 1)}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Extracted pages</div>
            </div>

            <div className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Word Count</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>
                {activeDocId === 'all'
                  ? totalWords.toLocaleString()
                  : (uploadedDocs.find((d) => d.id === activeDocId)?.word_count || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Tokens parsed</div>
            </div>
          </div>

          {/* Quick Action Summarization Buttons */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Executive AI Summarization Actions ({activeLabel})
              </div>
              {summary && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setSummary(null);
                    persistMemory(uploadedDocs, messages, null, activeDocId, summaryType);
                  }}
                  style={{ fontSize: '0.78rem' }}
                >
                  Clear Summary
                </button>
              )}
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
                <span>Action Items &amp; Risks</span>
              </button>
            </div>

            {summary && (
              <div
                style={{
                  marginTop: 18,
                  padding: 18,
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
                  <span>Synthesized {summaryType.replace('_', ' ').toUpperCase()} ({activeLabel})</span>
                </div>
                {summary}
              </div>
            )}
          </div>

          {/* AI Chat Assistant with Cross-Document Reasoning */}
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
                <div className="brand-icon-box" style={{ width: 36, height: 36 }}>
                  <Sparkles size={18} />
                </div>
                <div>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                    AI Chat Assistant
                  </h4>
                  <p style={{ fontSize: '0.78rem', margin: 0, color: 'var(--text-secondary)' }}>
                    Intelligent document reasoning &amp; conversational memory
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    fontSize: '0.75rem',
                    padding: '4px 10px',
                    borderRadius: 12,
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-soft)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  Scope: <strong>{activeLabel}</strong>
                </span>
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
                <div style={{ textAlign: 'center', margin: 'auto', padding: '32px 16px', maxWidth: 560 }}>
                  <HelpCircle size={36} style={{ margin: '0 auto 12px', color: 'var(--accent-red)', opacity: 0.8 }} />
                  <h5 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
                    Ask Anything Across Your Documents
                  </h5>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 20, lineHeight: 1.5 }}>
                    The AI Chat Assistant reasons intelligently across your active documents, connecting related concepts, analyzing impact, and recalling multi-turn context.
                  </p>

                  {/* Starter Chips */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                    {[
                      'What are the primary findings and core subjects?',
                      'Compare and synthesize key takeaways across documents',
                      'What are the core technical projects, skills, and impact?',
                      'Summarize actionable recommendations in 3 bullet points',
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
                          {!isUser && <span>Grounded in Documents</span>}
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
                    Reasoning across documents and synthesizing response...
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
                    ? `Ask anything across ${activeLabel} (e.g. "synthesize findings", "compare projects")...`
                    : 'Upload a document to chat...'
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
