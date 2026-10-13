// frontend/src/context/AuthContext.tsx
'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, User } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthModalOpen: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  loginWithGoogle: (email?: string, name?: string, picture?: string, credential?: string) => Promise<void>;
  logout: () => Promise<void>;
  openAuthModal: () => void;
  closeAuthModal: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Synchronous initialization from localStorage prevents flash of unauthenticated state on page reload
  const [token, setTokenState] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('ai_diagnoser_token');
    }
    return null;
  });

  const [user, setUser] = useState<User | null>(() => {
    if (typeof window !== 'undefined') {
      try {
        const storedUser = localStorage.getItem('ai_diagnoser_user');
        if (storedUser) {
          return JSON.parse(storedUser);
        }
      } catch {
        return null;
      }
    }
    return null;
  });

  const [loading, setLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = api.getToken() || (typeof window !== 'undefined' ? localStorage.getItem('ai_diagnoser_token') : null);
      if (storedToken) {
        api.setToken(storedToken);
        setTokenState(storedToken);
      }

      // Immediately hydrate user state from localStorage so the user is NEVER logged out on refresh
      if (typeof window !== 'undefined') {
        try {
          const cachedUser = localStorage.getItem('ai_diagnoser_user');
          if (cachedUser) {
            const parsed = JSON.parse(cachedUser);
            if (parsed && parsed.email) {
              setUser(parsed);
            }
          }
        } catch {
          // ignore
        }
      }

      // Verify and refresh session in background
      if (storedToken || typeof window !== 'undefined') {
        try {
          const userData = await api.getMe();
          if (userData) {
            setUser(userData);
            if (typeof window !== 'undefined') {
              localStorage.setItem('ai_diagnoser_user', JSON.stringify(userData));
            }
          }
        } catch (err: any) {
          // Crucial: NEVER log out or clear user or token on refresh or temporary server sleep.
          // Session is strictly cleared ONLY if user explicitly clicks Sign Out.
          console.warn('Background session refresh warning; preserved local session:', err?.message);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleAuthExpired = (e: Event) => {
      const customEvent = e as CustomEvent;
      const endpoint = customEvent.detail?.endpoint || '';
      // Only pop modal if the request wasn't an automatic background health/me probe
      if (!endpoint.includes('/auth/me') && !endpoint.includes('/health')) {
        console.warn('Session expired or requires authentication:', customEvent.detail?.message);
        setIsAuthModalOpen(true);
      }
    };

    window.addEventListener('ai_diagnoser_auth_expired', handleAuthExpired);
    return () => {
      window.removeEventListener('ai_diagnoser_auth_expired', handleAuthExpired);
    };
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api.login(email, password);
    setTokenState(data.token);
    setUser(data.user);
    if (typeof window !== 'undefined') {
      localStorage.setItem('ai_diagnoser_token', data.token);
      localStorage.setItem('ai_diagnoser_user', JSON.stringify(data.user));
    }
    setIsAuthModalOpen(false);
  };

  const register = async (email: string, name: string, password: string) => {
    const data = await api.register(email, name, password);
    setTokenState(data.token);
    setUser(data.user);
    if (typeof window !== 'undefined') {
      localStorage.setItem('ai_diagnoser_token', data.token);
      localStorage.setItem('ai_diagnoser_user', JSON.stringify(data.user));
    }
    setIsAuthModalOpen(false);
  };

  const loginWithGoogle = async (
    email?: string,
    name?: string,
    picture?: string,
    credential?: string
  ) => {
    const data = await api.loginWithGoogle(email, name, picture, credential);
    setTokenState(data.token);
    setUser(data.user);
    if (typeof window !== 'undefined') {
      localStorage.setItem('ai_diagnoser_token', data.token);
      localStorage.setItem('ai_diagnoser_user', JSON.stringify(data.user));
    }
    setIsAuthModalOpen(false);
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    } finally {
      setTokenState(null);
      setUser(null);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('ai_diagnoser_token');
        localStorage.removeItem('ai_diagnoser_user');
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthModalOpen,
        login,
        register,
        loginWithGoogle,
        logout,
        openAuthModal: () => setIsAuthModalOpen(true),
        closeAuthModal: () => setIsAuthModalOpen(false),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

