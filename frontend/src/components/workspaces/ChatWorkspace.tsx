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
  ChevronDown,
  Check,
} from 'lucide-react';

interface ModelOption {
  id: string;
  label: string;
  description: string;
  provider: string;
}

const MODEL_OPTIONS: ModelOption[] = [
  { id: 'gemini-3.8-flash', label: 'Gemini 3.8 Flash (Analytical)', description: 'Google DeepMind • Multimodal Reasoning', provider: 'Google Gemini' },
  { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', description: 'Google DeepMind • Ultra-fast responses', provider: 'Google Gemini' },
  { id: 'llama-3.3-70b-versatile', label: 'Groq LLaMA 3.3', description: 'Meta • High-throughput inference', provider: 'Groq' },
  { id: 'gpt-4o', label: 'OpenAI GPT-4o', description: 'OpenAI • Multimodal flagship', provider: 'OpenAI' },
];

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
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
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

  // Click outside and escape handler for custom model dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setIsModelDropdownOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsModelDropdownOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

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
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100dvh - 110px)',
        position: 'relative',
      }}
    >
      {/* Sleek Minimalist Toolbar - Model Selector & Grounded Context Pills */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
          padding: '4px 0 12px 0',
          borderBottom: '1px solid var(--border-subtle)',
          maxWidth: 860,
          margin: '0 auto',
          width: '100%',
        }}
      >
        {/* Custom React Dark-Themed Model Dropdown */}
        <div style={{ position: 'relative' }} ref={modelDropdownRef}>
          <button
            type="button"
            onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              background: 'rgba(18, 18, 20, 0.75)',
              backdropFilter: 'blur(16px)',
              WebkitBackdropFilter: 'blur(16px)',
              border: `1px solid ${isModelDropdownOpen ? 'rgba(220, 38, 38, 0.6)' : 'rgba(255, 255, 255, 0.1)'}`,
              fontSize: '0.82rem',
              color: 'var(--text-primary)',
              boxShadow: isModelDropdownOpen
                ? '0 0 0 2px rgba(220, 38, 38, 0.2), 0 4px 16px rgba(0, 0, 0, 0.4)'
                : '0 2px 8px rgba(0, 0, 0, 0.3)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            title="Select AI Model"
          >
            <Sparkles size={14} style={{ color: 'var(--accent-red)' }} />
            <span style={{ fontWeight: 600 }}>
              {MODEL_OPTIONS.find((m) => m.id === selectedModel)?.label || selectedModel}
            </span>
            <ChevronDown
              size={13}
              style={{
                color: 'var(--text-muted)',
                transform: isModelDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s ease',
              }}
            />
          </button>

          {isModelDropdownOpen && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                left: 0,
                minWidth: 280,
                background: '#121214',
                backgroundColor: 'rgba(18, 18, 20, 0.95)',
                backdropFilter: 'blur(24px) saturate(180%)',
                WebkitBackdropFilter: 'blur(24px) saturate(180%)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: 'var(--radius-md)',
                boxShadow: '0 16px 40px rgba(0, 0, 0, 0.65), 0 0 16px rgba(0, 0, 0, 0.4)',
                padding: '6px',
                zIndex: 60,
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
              }}
            >
              <div
                style={{
                  padding: '6px 10px 4px 10px',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: 'var(--text-muted)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                  marginBottom: 4,
                }}
              >
                Select AI Engine
              </div>

              {MODEL_OPTIONS.map((opt) => {
                const isSelected = selectedModel === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => {
                      setSelectedModel(opt.id);
                      setSelectedProvider(opt.provider);
                      setIsModelDropdownOpen(false);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      background: isSelected ? 'var(--accent-red-subtle)' : 'transparent',
                      border: 'none',
                      color: isSelected ? 'var(--accent-red)' : 'var(--text-primary)',
                      cursor: 'pointer',
                      textAlign: 'left',
                      width: '100%',
                      transition: 'all 0.12s ease',
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.background = 'transparent';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <span style={{ fontSize: '0.84rem', fontWeight: isSelected ? 600 : 500 }}>
                        {opt.label}
                      </span>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          color: isSelected ? 'var(--accent-red)' : 'var(--text-muted)',
                          opacity: 0.85,
                        }}
                      >
                        {opt.description}
                      </span>
                    </div>
                    {isSelected && (
                      <Check size={15} style={{ color: 'var(--accent-red)', flexShrink: 0, marginLeft: 8 }} />
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Grounded Evidence Sources Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              background: groundedDocs.length > 0 ? 'var(--accent-red-subtle)' : 'rgba(18, 18, 20, 0.65)',
              backdropFilter: 'blur(16px)',
              WebkitBackdropFilter: 'blur(16px)',
              border: `1px solid ${groundedDocs.length > 0 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(255, 255, 255, 0.08)'}`,
              fontSize: '0.8rem',
              color: groundedDocs.length > 0 ? 'var(--accent-red)' : 'var(--text-muted)',
              fontWeight: 500,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.25)',
            }}
          >
            <Layers size={13} />
            <span>
              {groundedDocs.length > 0
                ? `${groundedDocs.length} Grounded Source${groundedDocs.length > 1 ? 's' : ''}`
                : 'Direct Mode'}
            </span>
            {totalGroundedWords > 0 && (
              <span style={{ opacity: 0.8, fontSize: '0.74rem' }}>
                ({totalGroundedWords.toLocaleString()} words)
              </span>
            )}
          </div>

          {groundedDocs.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {groundedDocs.slice(0, 2).map((d) => (
                <span
                  key={d.id}
                  title={d.filename}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-soft)',
                    fontSize: '0.72rem',
                    color: 'var(--text-secondary)',
                    maxWidth: 120,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <FileText size={11} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.filename}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Floating Canvas Message Stream - Borderless */}
      <div
        ref={chatContainerRef}
        onScroll={handleChatScroll}
        className="chat-scroll-container"
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
          padding: '20px 0 24px 0',
          maxWidth: 860,
          margin: '0 auto',
          width: '100%',
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
              maxWidth: m.sender === 'user' ? '80%' : '90%',
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
                  marginTop: 2,
                }}
              >
                <Bot size={17} />
              </div>
            )}

            <div
              className="message-bubble"
              style={{
                background: m.sender === 'user' ? 'linear-gradient(135deg, var(--accent-red) 0%, var(--accent-red-hover) 100%)' : 'rgba(18, 18, 20, 0.65)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                color: m.sender === 'user' ? '#FFFFFF' : 'var(--text-primary)',
                padding: '14px 18px',
                borderRadius: varRadii(m.sender),
                border: m.sender === 'assistant' ? '1px solid rgba(255, 255, 255, 0.08)' : 'none',
                fontSize: '0.92rem',
                lineHeight: 1.6,
                boxShadow: m.sender === 'assistant' ? '0 4px 20px rgba(0, 0, 0, 0.35)' : '0 4px 16px var(--accent-red-glow)',
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
                  marginTop: 8,
                  fontSize: '0.72rem',
                  opacity: 0.75,
                }}
              >
                {m.provider && (
                  <span>via {m.provider}</span>
                )}
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
                  background: 'rgba(18, 18, 20, 0.65)',
                  backdropFilter: 'blur(16px)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  marginTop: 2,
                }}
              >
                <User size={17} />
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
              <Bot size={17} />
            </div>
            <div
              style={{
                background: 'rgba(18, 18, 20, 0.65)',
                backdropFilter: 'blur(16px)',
                padding: '10px 18px',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-secondary)',
                fontSize: '0.85rem',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: 'var(--shadow-card)',
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
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
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

      {/* Floating Glassmorphic Prompt Capsule */}
      <div
        style={{
          maxWidth: 860,
          margin: '0 auto',
          width: '100%',
          paddingBottom: 14,
          paddingTop: 8,
        }}
      >
        <form onSubmit={handleSend} className="floating-prompt-bar">
          <input
            type="text"
            className="floating-prompt-input"
            placeholder={user ? "Ask anything about variance, executive KPIs, or correlations..." : "Sign in to query the AI assistant..."}
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="floating-prompt-btn"
            disabled={loading || !inputPrompt.trim()}
            title="Send inquiry"
          >
            <Send size={16} />
          </button>
        </form>

        <div
          style={{
            textAlign: 'center',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            marginTop: 8,
            letterSpacing: '0.01em',
          }}
        >
          Gemini 3.8 Flash • Multi-Source Cognitive Synthesis &amp; Enterprise Diagnostics
        </div>
      </div>
    </div>
  );
};

function varRadii(sender: 'user' | 'assistant') {
  return sender === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px';
}
