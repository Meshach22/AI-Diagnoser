// frontend/src/components/workspaces/ChatWorkspace.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { api, ChatResponse } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  Send,
  Bot,
  User,
  Clock,
  Sparkles,
  AlertCircle,
  FileSpreadsheet,
  FileText,
} from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  provider?: string;
  latencyMs?: number;
  timestamp: string;
}

interface ChatWorkspaceProps {
  initialPrompt?: string;
  activeContextText?: string;
}

interface UploadedDocMeta {
  id: string;
  filename: string;
  full_text?: string;
  preview?: string;
  page_count?: number;
  word_count?: number;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  initialPrompt = '',
  activeContextText = '',
}) => {
  const { user, openAuthModal } = useAuth();
  const [selectedProvider, setSelectedProvider] = useState('Google Gemini');
  const [selectedModel, setSelectedModel] = useState('gemini-3.8-flash');
  const [inputPrompt, setInputPrompt] = useState(initialPrompt);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'assistant',
      text: 'Hello! I am your AI Data Diagnostics Copilot. You can ask me to evaluate financial indicators, synthesize unstructured documents, or explain anomalies across your data.',
      timestamp: 'Just now',
    },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [persistedDocs, setPersistedDocs] = useState<UploadedDocMeta[]>([]);
  const [activeDocContext, setActiveDocContext] = useState<UploadedDocMeta | null>(null);

  // Auto-discover uploaded documents from persistent workspace memory
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const memKey = user?.email ? `ai_diagnoser_memory_${user.email}` : 'ai_diagnoser_memory_guest';
      const raw = localStorage.getItem(memKey) || localStorage.getItem('ai_diagnoser_memory_guest');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed?.uploadedDocs) && parsed.uploadedDocs.length > 0) {
          setPersistedDocs(parsed.uploadedDocs);
          const active = parsed.activeDocId && parsed.activeDocId !== 'all'
            ? parsed.uploadedDocs.find((d: any) => d.id === parsed.activeDocId)
            : parsed.uploadedDocs[0];
          setActiveDocContext(active || parsed.uploadedDocs[0]);
        }
      }
    } catch (e) {
      console.warn('Failed to load persisted document context for chat:', e);
    }
  }, [user?.email]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputPrompt.trim() || loading) return;

    if (!user) {
      openAuthModal();
      return;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: inputPrompt.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt('');
    setLoading(true);
    setError(null);

    // Resolve document context to inject cleanly for Gemini 3.8 Flash
    let promptToSend = userMsg.text;
    let docToUse = activeDocContext;

    if (persistedDocs.length > 0) {
      const q = userMsg.text.toLowerCase();
      // Match document if filename or base name is referenced in query (e.g. "Shalom resume.pdf", "resume")
      const matched = persistedDocs.find((d) => {
        if (!d.filename) return false;
        const baseName = d.filename.toLowerCase().replace(/\.[^/.]+$/, '');
        return q.includes(d.filename.toLowerCase()) || (baseName.length >= 3 && q.includes(baseName));
      });
      if (matched) {
        docToUse = matched;
      } else if (!docToUse) {
        docToUse = persistedDocs[0];
      }
    }

    if (docToUse && (docToUse.full_text || docToUse.preview)) {
      const docFilename = docToUse.filename || 'Uploaded Document';
      const docRaw = docToUse.full_text || docToUse.preview || '';
      const cappedDocText = docRaw.slice(0, 25000);
      promptToSend = `System Context: The user has uploaded the following document: ${docFilename}\n---\n${cappedDocText}\n---\nUser Query: ${userMsg.text}`;
    } else if (activeContextText && activeContextText.trim()) {
      const cappedContext = activeContextText.trim().slice(0, 25000);
      promptToSend = `System Context: The user has uploaded the following document: ${activeDocContext?.filename || 'Document Context'}\n---\n${cappedContext}\n---\nUser Query: ${userMsg.text}`;
    }

    try {
      const resp: ChatResponse = await api.queryRouter(
        promptToSend,
        selectedProvider,
        selectedProvider === 'Google Gemini' ? (selectedModel || 'gemini-3.8-flash') : undefined
      );
      const responseText = resp.result || resp.response;
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: responseText || 'No content returned from router.',
        provider: resp.active_provider || resp.provider,
        latencyMs: resp.telemetry?.latency_ms,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setError(err.message || 'Failed to query core router.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: 'calc(100vh - 140px)' }}>
      {/* Top Controls */}
      <div
        className="card"
        style={{
          padding: '14px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="brand-icon-box" style={{ width: 30, height: 30 }}>
            <Sparkles size={16} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Chat with Core LLM Router
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Direct access to multimodal diagnostic pipelines with automatic session injection
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Inference Engine:
          </label>
          <select
            className="select"
            value={selectedProvider}
            onChange={(e) => {
              const val = e.target.value;
              setSelectedProvider(val);
              if (val === 'Google Gemini') {
                setSelectedModel('gemini-3.8-flash');
              }
            }}
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <option value="Google Gemini">Google Gemini 3.8 Flash</option>
            <option value="Groq">Groq LLaMA 3.3 (Fast)</option>
            <option value="OpenAI">OpenAI GPT-4o</option>
          </select>
        </div>
      </div>

      {(activeContextText || activeDocContext) && (
        <div
          style={{
            padding: '8px 14px',
            background: 'var(--bg-subtle)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-soft)',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={14} style={{ color: 'var(--accent-red)' }} />
            <span>
              Connected Document:{' '}
              <strong style={{ color: 'var(--text-primary)' }}>
                {activeDocContext ? activeDocContext.filename : 'Active Injected Context'}
              </strong>
              {activeDocContext?.word_count ? ` (${activeDocContext.word_count.toLocaleString()} words)` : ''}
            </span>
          </div>

          {persistedDocs.length > 1 && (
            <select
              value={activeDocContext?.id || ''}
              onChange={(e) => {
                const target = persistedDocs.find((d) => d.id === e.target.value);
                if (target) setActiveDocContext(target);
              }}
              style={{
                fontSize: '0.75rem',
                padding: '2px 8px',
                borderRadius: 'var(--radius-xs)',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-soft)',
                color: 'var(--text-primary)',
              }}
            >
              {persistedDocs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Message Thread */}
      <div
        className="card"
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          padding: 24,
        }}
      >
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              display: 'flex',
              gap: 12,
              alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
            }}
          >
            {m.sender === 'assistant' && (
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
                <Bot size={18} />
              </div>
            )}

            <div
              style={{
                background: m.sender === 'user' ? 'var(--accent-red)' : 'var(--bg-subtle)',
                color: m.sender === 'user' ? '#FFFFFF' : 'var(--text-primary)',
                padding: '12px 16px',
                borderRadius: varRadii(m.sender),
                border: m.sender === 'assistant' ? '1px solid var(--border-soft)' : 'none',
                fontSize: '0.92rem',
                lineHeight: 1.5,
                whiteSpace: 'pre-wrap',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              {m.text}

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  gap: 8,
                  marginTop: 6,
                  fontSize: '0.72rem',
                  opacity: 0.75,
                }}
              >
                {m.provider && <span>via {m.provider}</span>}
                {m.latencyMs && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <Clock size={11} /> {m.latencyMs}ms
                  </span>
                )}
                <span>{m.timestamp}</span>
              </div>
            </div>

            {m.sender === 'user' && (
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-soft)',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <User size={18} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
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
              }}
            >
              <Bot size={18} />
            </div>
            <div
              style={{
                background: 'var(--bg-subtle)',
                padding: '10px 18px',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-secondary)',
                fontSize: '0.85rem',
                border: '1px solid var(--border-soft)',
              }}
              className="animate-pulse"
            >
              Consulting {selectedProvider} neural pipeline...
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              color: 'var(--accent-red)',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} style={{ display: 'flex', gap: 10 }}>
        <input
          type="text"
          className="input"
          placeholder={user ? "Ask a question about trends, variance, or executive takeaways..." : "Sign in to query the AI diagnostic engine..."}
          value={inputPrompt}
          onChange={(e) => setInputPrompt(e.target.value)}
          disabled={loading}
          style={{ padding: '14px 18px', fontSize: '0.95rem' }}
        />
        <button
          type="submit"
          className="btn btn-primary btn-icon"
          disabled={loading || !inputPrompt.trim()}
          style={{ width: 50, height: 50, flexShrink: 0 }}
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  );
};

function varRadii(sender: 'user' | 'assistant') {
  return sender === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px';
}
