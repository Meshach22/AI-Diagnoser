// frontend/src/components/workspaces/ChatWorkspace.tsx
'use client';

import React, { useState } from 'react';
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

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  initialPrompt = '',
  activeContextText = '',
}) => {
  const { user, openAuthModal } = useAuth();
  const [provider, setProvider] = useState('Google Gemini');
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

    // Combine user query with active context if present
    const promptToSend = activeContextText
      ? `Context Document / Dataset:\n${activeContextText.slice(0, 3000)}\n\nUser Question:\n${userMsg.text}`
      : userMsg.text;

    try {
      const resp: ChatResponse = await api.queryRouter(promptToSend, provider);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: resp.result || 'No content returned from router.',
        provider: resp.provider,
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
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <option value="Google Gemini">Google Gemini 2.5</option>
            <option value="Groq">Groq LLaMA 3.3 (Fast)</option>
            <option value="OpenAI">OpenAI GPT-4o</option>
          </select>
        </div>
      </div>

      {activeContextText && (
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
            gap: 8,
          }}
        >
          <FileText size={14} style={{ color: 'var(--accent-red)' }} />
          <span>Active context injected into LLM query ({activeContextText.length} characters)</span>
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
              Consulting {provider} neural pipeline...
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
