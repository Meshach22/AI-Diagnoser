// frontend/src/components/auth/AuthModal.tsx
'use client';

import React, { useState } from 'react';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { useAuth } from '@/context/AuthContext';
import { X, Lock, Mail, User as UserIcon, AlertCircle, ArrowRight } from 'lucide-react';

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, closeAuthModal, login, register, loginWithGoogle } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>('login');

  // Traditional form fields
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

  // Google returns a signed ID token; the backend verifies it and derives email/name/picture itself.
  const handleGoogleSuccess = async (credential?: string) => {
    if (!credential) {
      setError('Google did not return a credential. Please try again.');
      return;
    }
    setError(null);
    setGoogleSubmitting(true);
    try {
      await loginWithGoogle(credential);
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

        {/* Real Google Sign-In (Google Identity Services) */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            minHeight: 44,
            opacity: googleSubmitting || submitting ? 0.6 : 1,
            pointerEvents: googleSubmitting || submitting ? 'none' : 'auto',
          }}
        >
          {GOOGLE_CLIENT_ID ? (
            <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
              <GoogleLogin
                onSuccess={(res) => handleGoogleSuccess(res.credential)}
                onError={() => setError('Google sign-in was cancelled or failed. Please try again.')}
                text="continue_with"
                shape="rectangular"
                size="large"
                width="368"
              />
            </GoogleOAuthProvider>
          ) : (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '10px 0' }}>
              Google sign-in is unavailable: set <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code>.
            </div>
          )}
        </div>
        {googleSubmitting && (
          <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 8 }}>
            Verifying your Google account...
          </div>
        )}

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
