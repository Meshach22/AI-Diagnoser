// frontend/src/components/auth/AuthModal.tsx
'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { X, Lock, Mail, User as UserIcon, AlertCircle, ArrowRight } from 'lucide-react';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, closeAuthModal, login, register, loginWithGoogle } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>('login');
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);

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
        if (password.length < 8) {
          throw new Error('Password must be at least 8 characters long.');
        }
        await register(email.trim(), name.trim(), password);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication request failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError(null);
    setGoogleSubmitting(true);
    try {
      await loginWithGoogle('google.analyst@workspace.ai', 'Workspace Analyst');
    } catch (err: any) {
      setError(err.message || 'Google sign-in could not be completed.');
    } finally {
      setGoogleSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={closeAuthModal}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: 420,
          padding: '28px 26px',
          borderRadius: 'var(--radius-lg)',
          boxShadow: '0 20px 40px -15px rgba(0,0,0,0.3)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              {tab === 'login' ? 'Welcome Back' : 'Create an Account'}
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              {tab === 'login' ? 'Sign in to access your persistent workspaces & documents' : 'Get started with intelligent document synthesis'}
            </p>
          </div>
          <button
            onClick={closeAuthModal}
            className="btn btn-secondary btn-icon"
            style={{ width: 32, height: 32, borderRadius: '50%' }}
            title="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* One-Click Google Sign-In */}
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={googleSubmitting || submitting}
          className="btn btn-outline"
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            padding: '11px 16px',
            fontSize: '0.9rem',
            fontWeight: 600,
            borderRadius: 'var(--radius-md)',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-medium)',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>{googleSubmitting ? 'Signing in with Google...' : 'Continue with Google'}</span>
        </button>

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', margin: '18px 0', gap: 10 }}>
          <div style={{ flex: 1, height: 1, background: 'var(--border-soft)' }} />
          <span style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
            or continue with email
          </span>
          <div style={{ flex: 1, height: 1, background: 'var(--border-soft)' }} />
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
              <label htmlFor="auth-name" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                Full Name
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="auth-name"
                  type="text"
                  name="name"
                  autoComplete="name"
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
            <label htmlFor="auth-email" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Email Address
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="auth-email"
                type="email"
                name="email"
                autoComplete="email"
                className="input"
                placeholder="analyst@enterprise.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ paddingLeft: 36 }}
                required
              />
              <Mail size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
            </div>
          </div>

          <div>
            <label htmlFor="auth-password" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="auth-password"
                type="password"
                name="password"
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
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

          {/* Remember Me */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                id="rememberMe"
                name="rememberMe"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                style={{ accentColor: 'var(--accent-red)' }}
              />
              <span>Remember me</span>
            </label>
            {tab === 'login' && (
              <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                Auto-saved session
              </span>
            )}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 4, padding: '11px 16px' }}
            disabled={submitting || googleSubmitting}
          >
            {submitting ? 'Please wait...' : tab === 'login' ? 'Sign In' : 'Create Account'}
            {!submitting && <ArrowRight size={16} />}
          </button>
        </form>

        {/* Footer Toggle */}
        <div style={{ marginTop: 18, textAlign: 'center', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          {tab === 'login' ? (
            <span>
              Don&apos;t have an account?{' '}
              <button
                type="button"
                onClick={() => { setTab('register'); setError(null); }}
                style={{ background: 'none', border: 'none', color: 'var(--accent-red)', fontWeight: 600, cursor: 'pointer', padding: 0 }}
              >
                Sign up
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => { setTab('login'); setError(null); }}
                style={{ background: 'none', border: 'none', color: 'var(--accent-red)', fontWeight: 600, cursor: 'pointer', padding: 0 }}
              >
                Sign in
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

