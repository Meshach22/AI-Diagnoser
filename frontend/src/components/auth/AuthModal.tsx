// frontend/src/components/auth/AuthModal.tsx
'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { X, Lock, Mail, User as UserIcon, AlertCircle, ArrowRight } from 'lucide-react';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, closeAuthModal, login, register } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>('login');
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (tab === 'login') {
        if (!email || !password) {
          throw new Error('Please enter both email and password.');
        }
        await login(email.trim(), password);
      } else {
        if (!email || !name || !password) {
          throw new Error('Please fill in all registration fields.');
        }
        if (password.length < 12) {
          throw new Error('Password must be at least 12 characters long.');
        }
        await register(email.trim(), name.trim(), password);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication request failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={closeAuthModal}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="brand-icon-box" style={{ width: 28, height: 28 }}>
              <Lock size={15} />
            </div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
              {tab === 'login' ? 'Sign In to Workspace' : 'Create Enterprise Account'}
            </h2>
          </div>
          <button
            onClick={closeAuthModal}
            className="btn btn-secondary btn-icon"
            style={{ width: 30, height: 30 }}
            title="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab switch */}
        <div className="tabs-nav" style={{ marginBottom: 20 }}>
          <button
            className={`tab-btn ${tab === 'login' ? 'active' : ''}`}
            onClick={() => { setTab('login'); setError(null); }}
          >
            Existing Analyst Sign In
          </button>
          <button
            className={`tab-btn ${tab === 'register' ? 'active' : ''}`}
            onClick={() => { setTab('register'); setError(null); }}
          >
            New Registration
          </button>
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              color: 'var(--accent-red)',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 16,
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {tab === 'register' && (
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                Full Name
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="input"
                  placeholder="Jane Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  style={{ paddingLeft: 36 }}
                  required
                />
                <UserIcon size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
              </div>
            </div>
          )}

          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Work Email
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="email"
                className="input"
                placeholder="analyst@enterprise.local"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ paddingLeft: 36 }}
                required
              />
              <Mail size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
            </div>
          </div>

          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Password {tab === 'register' ? '(Minimum 12 characters)' : ''}
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                className="input"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingLeft: 36 }}
                required
              />
              <Lock size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 8 }}
            disabled={submitting}
          >
            {submitting ? 'Authenticating...' : tab === 'login' ? 'Sign In' : 'Create Account'}
            {!submitting && <ArrowRight size={16} />}
          </button>
        </form>

        <div style={{ marginTop: 18, textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Authoritative backend session authentication with Argon2id cryptographic hashing.
        </div>
      </div>
    </div>
  );
};
