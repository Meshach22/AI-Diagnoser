// frontend/src/components/workspaces/ChatWorkspace.tsx
'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api, ChatResponse } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send,
  Bot,
  User,
  Clock,
  Sparkles,
  AlertCircle,
  FileSpreadsheet,
  FileText,
  Layers,
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

export function buildMultiDocContext(bundledDocumentSources: string, query: string): string {
  return `[CONTEXTUAL EVIDENCE DOSSIER]\nThe following are reference documents provided by the user. Do NOT quote or repeat this text directly. Analyze, synthesize, evaluate, and extract high-level strategic intelligence to answer the query below:\n---\n${bundledDocumentSources}\n---\nUSER INQUIRY: ${query}`;
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
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'assistant',
      text: 'Hello! I am your AI Chat Assistant powered by Gemini 3.8 Flash. I can synthesize cross-document insights across all your uploaded files, identify hidden correlations, and provide strategic recommendations.',
      timestamp: 'Just now',
    },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [persistedDocs, setPersistedDocs] = useState<UploadedDocMeta[]>([]);
  const [activeDocContext, setActiveDocContext] = useState<UploadedDocMeta | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUpRef = useRef<boolean>(false);

  // Non-intrusive auto-scrolling: preserves user scroll position if reading historical messages
  const scrollToBottom = useCallback((force: boolean = false, instant: boolean = false) => {
    if (!force && isUserScrolledUpRef.current) {
      return;
    }
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: instant ? 'auto' : 'smooth',
      });
    } else if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: instant ? 'auto' : 'smooth',
        block: 'end',
      });
    }
  }, []);

  const handleChatScroll = () => {
    const el = chatContainerRef.current;
    if (!el) return;
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isUserScrolledUpRef.current = distanceToBottom > 80;
  };

  // Auto-scroll when messages change or loading state toggles (unless user scrolled up)
  useEffect(() => {
    scrollToBottom(false, true);
  }, [messages, loading, scrollToBottom]);

  // Synchronize documents from memory / storage
  const syncDocumentsFromStorage = useCallback(() => {
    if (typeof window === 'undefined') return;
    try {
      const memKey = user?.email ? `ai_diagnoser_memory_${user.email}` : 'ai_diagnoser_memory_guest';
      const raw = localStorage.getItem(memKey) || localStorage.getItem('ai_diagnoser_memory_guest');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed?.uploadedDocs)) {
          setPersistedDocs(parsed.uploadedDocs);
          if (parsed.uploadedDocs.length > 0) {
            const active = parsed.activeDocId && parsed.activeDocId !== 'all'
              ? parsed.uploadedDocs.find((d: any) => d.id === parsed.activeDocId)
              : parsed.uploadedDocs[0];
            setActiveDocContext(active || parsed.uploadedDocs[0]);
          } else {
            setActiveDocContext(null);
          }
          return;
        }
      }
      setPersistedDocs([]);
      setActiveDocContext(null);
    } catch (e) {
      console.warn('Failed to load persisted document context for chat:', e);
    }
  }, [user?.email]);

  // Live cross-workspace synchronization listener
  useEffect(() => {
    syncDocumentsFromStorage();

    const handleSync = (e: any) => {
      const payload = e.detail;
      if (payload && Array.isArray(payload.uploadedDocs)) {
        setPersistedDocs(payload.uploadedDocs);
        if (payload.uploadedDocs.length > 0) {
          const active = payload.activeDocId && payload.activeDocId !== 'all'
            ? payload.uploadedDocs.find((d: any) => d.id === payload.activeDocId)
            : payload.uploadedDocs[0];
          setActiveDocContext(active || payload.uploadedDocs[0]);
        } else {
          setActiveDocContext(null);
        }
      }
    };

    window.addEventListener('ai_diagnoser_workspace_sync', handleSync);
    window.addEventListener('storage', syncDocumentsFromStorage);

    return () => {
      window.removeEventListener('ai_diagnoser_workspace_sync', handleSync);
      window.removeEventListener('storage', syncDocumentsFromStorage);
    };
  }, [syncDocumentsFromStorage]);

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

    isUserScrolledUpRef.current = false;
    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt('');
    setLoading(true);
    setError(null);
    scrollToBottom(true, true);

    // Multi-Source Grounding: Bundle ALL currently uploaded documents belonging to the user
    let promptToSend = userMsg.text;
    const docsWithText = persistedDocs.filter(
      (d) => (d.full_text || d.preview || '').trim().length > 0
    );

    if (docsWithText.length > 0) {
      const sourcesBlock = docsWithText
        .map((doc, idx) => {
          const title = doc.filename || `Source_${idx + 1}`;
          const content = (doc.full_text || doc.preview || '').trim().slice(0, 25000);
          return `--- Source ${idx + 1}: ${title} ---\n${content}`;
        })
        .join('\n\n');

      promptToSend = buildMultiDocContext(sourcesBlock, userMsg.text);
    } else if (activeContextText && activeContextText.trim()) {
      const cappedContext = activeContextText.trim().slice(0, 30000);
      promptToSend = buildMultiDocContext(`--- Source 1: Active Context ---\n${cappedContext}`, userMsg.text);
    }

    const assistantMsgId = (Date.now() + 1).toString();
    const startTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let streamedText = '';

    // Create an initial placeholder assistant message that will stream in real-time
    const initialAssistantMsg: Message = {
      id: assistantMsgId,
      sender: 'assistant',
      text: '',
      provider: selectedProvider,
      timestamp: startTimestamp,
    };
    setMessages((prev) => [...prev, initialAssistantMsg]);
    setStreamingMsgId(assistantMsgId);

    try {
      const startTime = performance.now();
      const streamRes = await api.streamRouter(
        promptToSend,
        selectedProvider,
        selectedModel || 'gemini-3.8-flash',
        (token: string) => {
          streamedText += token;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, text: streamedText } : msg
            )
          );
        }
      );

      const elapsedMs = Math.round(performance.now() - startTime);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                text: streamedText || 'No response returned from stream.',
                provider: streamRes.provider || selectedProvider,
                latencyMs: streamRes.latencyMs || elapsedMs,
              }
            : msg
        )
      );
    } catch (streamErr: any) {
      console.warn('Streaming encountered an issue, evaluating fallback:', streamErr);
      if (!streamedText) {
        try {
          const resp: ChatResponse = await api.queryRouter(
            promptToSend,
            selectedProvider,
            selectedProvider === 'Google Gemini' ? (selectedModel || 'gemini-3.8-flash') : undefined
          );
          const responseText = resp.result || resp.response;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    text: responseText || 'No content returned from router.',
                    provider: resp.active_provider || resp.provider,
                    latencyMs: resp.telemetry?.latency_ms,
                  }
                : msg
            )
          );
        } catch (unaryErr: any) {
          setError(unaryErr.message || streamErr.message || 'Failed to query core router.');
          setMessages((prev) => prev.filter((msg) => msg.id !== assistantMsgId));
        }
      } else {
        setError(`Stream interrupted: ${streamErr.message || 'Connection lost'}`);
      }
    } finally {
      setLoading(false);
      setStreamingMsgId(null);
    }
  };

  const groundedDocs = persistedDocs.filter(
    (d) => (d.full_text || d.preview || '').trim().length > 0
  );
  const totalGroundedWords = groundedDocs.reduce((acc, d) => acc + (d.word_count || 0), 0);

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
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              AI Chat Assistant
            </h2>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <label style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Model:
          </label>
          <select
            className="select"
            value={selectedModel}
            onChange={(e) => {
              const modelId = e.target.value;
              setSelectedModel(modelId);
              if (modelId.startsWith('gemini')) {
                setSelectedProvider('Google Gemini');
              } else if (modelId.startsWith('llama')) {
                setSelectedProvider('Groq');
              } else if (modelId.startsWith('gpt')) {
                setSelectedProvider('OpenAI');
              }
            }}
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <option value="gemini-3.8-flash">Google Gemini 3.8 Flash</option>
            <option value="gemini-2.5-flash">Google Gemini 2.5 Flash</option>
            <option value="llama-3.3-70b-versatile">Groq LLaMA 3.3 (Fast)</option>
            <option value="gpt-4o">OpenAI GPT-4o</option>
          </select>
        </div>
      </div>

      {/* Grounded Evidence Dossier Bar */}
      <div
        style={{
          padding: '10px 16px',
          background: 'var(--bg-card)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-soft)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '3px 10px',
              borderRadius: 'var(--radius-full)',
              background: groundedDocs.length > 0 ? 'var(--accent-red-subtle)' : 'var(--bg-subtle)',
              border: `1px solid ${groundedDocs.length > 0 ? 'rgba(239, 68, 68, 0.25)' : 'var(--border-soft)'}`,
              color: groundedDocs.length > 0 ? 'var(--accent-red)' : 'var(--text-muted)',
              fontWeight: 600,
              fontSize: '0.75rem',
            }}
          >
            <Layers size={13} />
            <span>
              {groundedDocs.length > 0
                ? `${groundedDocs.length} Grounded Source${groundedDocs.length > 1 ? 's' : ''}`
                : 'Direct Mode'}
            </span>
          </div>

          <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
            {groundedDocs.length > 0 ? (
              <>
                Grounding answers in {groundedDocs.length} document{groundedDocs.length > 1 ? 's' : ''}
                {totalGroundedWords > 0 && (
                  <span style={{ color: 'var(--text-muted)', marginLeft: 5 }}>
                    ({totalGroundedWords.toLocaleString()} words analyzed)
                  </span>
                )}
              </>
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>
                No documents uploaded. Responses draw from foundational intelligence.
              </span>
            )}
          </span>
        </div>

        {groundedDocs.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            {groundedDocs.slice(0, 3).map((d) => (
              <span
                key={d.id}
                title={d.filename}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-soft)',
                  fontSize: '0.74rem',
                  maxWidth: 160,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: 'var(--text-secondary)',
                }}
              >
                <FileText size={11} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.filename}</span>
              </span>
            ))}
            {groundedDocs.length > 3 && (
              <span
                style={{
                  fontSize: '0.74rem',
                  color: 'var(--text-muted)',
                  padding: '2px 6px',
                }}
              >
                +{groundedDocs.length - 3} more
              </span>
            )}
          </div>
        )}
      </div>

      {/* Message Thread */}
      <div
        ref={chatContainerRef}
        onScroll={handleChatScroll}
        className="card chat-scroll-container"
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
            className="chat-message"
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
              className="message-bubble"
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
              {m.sender === 'user' ? (
                <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
              ) : (
                <div className="chat-markdown">
                  {m.text ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {m.text}
                    </ReactMarkdown>
                  ) : (
                    <span style={{ fontStyle: 'italic', opacity: 0.75 }}>
                      Reasoning with {selectedProvider}...
                    </span>
                  )}
                  {loading && streamingMsgId === m.id && (
                    <span
                      style={{
                        display: 'inline-block',
                        width: 7,
                        height: 15,
                        backgroundColor: 'var(--accent-red)',
                        marginLeft: 4,
                        verticalAlign: 'text-bottom',
                        animation: 'pulse 1s infinite',
                      }}
                    />
                  )}
                </div>
              )}

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

        {loading && !streamingMsgId && (
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

        <div ref={messagesEndRef} style={{ height: 1 }} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} style={{ display: 'flex', gap: 10 }}>
        <input
          type="text"
          className="input"
          placeholder={user ? "Ask a question about trends, variance, or executive takeaways..." : "Sign in to query the AI assistant..."}
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
