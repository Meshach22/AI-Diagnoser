// frontend/src/components/workspaces/HomeWorkspace.tsx
'use client';

import React, { useEffect, useRef, useState } from 'react';
import { WorkspaceTab } from '../layout/Sidebar';
import { useAuth } from '@/context/AuthContext';
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
  MessageSquare,
  Sparkles,
} from 'lucide-react';

interface HomeWorkspaceProps {
  onSelectTab: (tab: WorkspaceTab) => void;
  onFileLoaded: (file: File, type: 'data' | 'document' | 'vision') => void;
  onQuerySubmit: (query: string) => void;
}

interface RecentUploadItem {
  name: string;
  type: 'data' | 'document' | 'vision';
  time: string;
  size: string;
  status: string;
}

interface PastChatThread {
  id: string;
  query: string;
  answerSnippet: string;
  time: string;
}

export const HomeWorkspace: React.FC<HomeWorkspaceProps> = ({
  onSelectTab,
  onFileLoaded,
  onQuerySubmit,
}) => {
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [recentItems, setRecentItems] = useState<RecentUploadItem[]>([]);
  const [pastChats, setPastChats] = useState<PastChatThread[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let items: RecentUploadItem[] = [];
    try {
      const stored = localStorage.getItem('ai_diagnoser_upload_history');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          items = parsed;
        }
      }
    } catch {
      items = [];
    }

    // Load persistent user memory documents and chats
    try {
      const memKey = user?.email ? `ai_diagnoser_memory_${user.email}` : 'ai_diagnoser_memory_guest';
      const userMemRaw = localStorage.getItem(memKey);
      if (userMemRaw) {
        const mem = JSON.parse(userMemRaw);
        if (Array.isArray(mem.uploadedDocs)) {
          mem.uploadedDocs.forEach((doc: any) => {
            if (!items.some((it) => it.name === doc.filename)) {
              items.unshift({
                name: doc.filename,
                type: 'document',
                time: doc.uploadedAt || 'Saved Session',
                size: `${doc.page_count} pages • ${doc.word_count?.toLocaleString() || 0} words`,
                status: 'Persistent',
              });
            }
          });
        }
        if (Array.isArray(mem.messages)) {
          const chats: PastChatThread[] = [];
          for (let i = 0; i < mem.messages.length; i++) {
            if (mem.messages[i].role === 'user') {
              const nextMsg = mem.messages[i + 1]?.role === 'assistant' ? mem.messages[i + 1].content : '';
              chats.push({
                id: mem.messages[i].id,
                query: mem.messages[i].content,
                answerSnippet: nextMsg ? nextMsg.slice(0, 110) + '...' : '',
                time: mem.messages[i].timestamp || 'Saved',
              });
            }
          }
          setPastChats(chats.reverse().slice(0, 4));
        }
      }
    } catch {
      // ignore
    }

    setRecentItems(items.slice(0, 10));
  }, [user]);

  const formatBytes = (bytes: number): string => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const recordUpload = (file: File, type: 'data' | 'document' | 'vision') => {
    const newItem: RecentUploadItem = {
      name: file.name,
      type,
      time: 'Just now',
      size: formatBytes(file.size),
      status: 'Uploaded',
    };
    try {
      const stored = localStorage.getItem('ai_diagnoser_upload_history');
      const existing: RecentUploadItem[] = stored ? JSON.parse(stored) : [];
      const updated = [newItem, ...existing.filter((item) => item.name !== file.name)].slice(0, 10);
      localStorage.setItem('ai_diagnoser_upload_history', JSON.stringify(updated));
      setRecentItems(updated);
    } catch {
      // ignore
    }
  };

  const chips = [
    { label: 'Create a summary', prompt: 'Provide a concise executive summary with key metrics, conclusions, and next steps.', icon: <FileText size={14} /> },
    { label: 'Find trends', prompt: 'Identify primary trends, notable changes over time, and outliers in this dataset.', icon: <TrendingUp size={14} /> },
    { label: 'Compare values', prompt: 'Compare performance across segments and summarize key differences against baseline averages.', icon: <FileSearch size={14} /> },
  ];

  const handleFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    let detectedType: 'data' | 'document' | 'vision' = 'data';
    if (['csv', 'xlsx', 'xls', 'parquet'].includes(ext)) {
      detectedType = 'data';
    } else if (['pdf', 'docx', 'doc', 'txt'].includes(ext)) {
      detectedType = 'document';
    } else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
      detectedType = 'vision';
    }
    recordUpload(file, detectedType);
    onFileLoaded(file, detectedType);
    onSelectTab('unified');
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
          Drop documents or spreadsheets here to begin analysis
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 18 }}>
          Supports PDF, Word (DOCX), Plaintext, CSV, and Excel
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
            placeholder="Ask a question about your documents, operations, or files..."
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

        {recentItems.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--text-muted)' }}>
            <FileSpreadsheet size={32} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
            <p style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-secondary)' }}>No documents uploaded yet</p>
            <p style={{ fontSize: '0.8rem', marginTop: 4 }}>Upload your datasets, documents, or images above to start analyzing and see your history here.</p>
          </div>
        ) : (
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
        )}

        {/* Past Diagnostic Console Sessions */}
        {pastChats.length > 0 && (
          <div style={{ marginTop: 28 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div>
                <h4 style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                  Recent Diagnostic Console Threads
                </h4>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                  Pick up right where you left off with multi-turn conversational reasoning
                </p>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => onSelectTab('unified')}>
                Open Console
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
              {pastChats.map((chat) => (
                <div
                  key={chat.id}
                  onClick={() => onSelectTab('unified')}
                  style={{
                    padding: '14px 16px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-soft)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = 'var(--accent-red)')}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = 'var(--border-soft)')}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <MessageSquare size={15} style={{ color: 'var(--accent-red)' }} />
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>{chat.time}</span>
                  </div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {chat.query}
                  </div>
                  {chat.answerSnippet && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                      {chat.answerSnippet}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
