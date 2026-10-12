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
  logout: () => Promise<void>;
  openAuthModal: () => void;
  closeAuthModal: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = api.getToken();
      if (storedToken) {
        api.setToken(storedToken);
        setTokenState(storedToken);
      }

      // Check active session via token or cookie
      if (storedToken || typeof window !== 'undefined') {
        try {
          const userData = await api.getMe();
          setUser(userData);
        } catch (err: any) {
          // Never prematurely wipe stored token on page reloads or transient backend failures.
          // Token is strictly wiped only when the user explicitly triggers logout().
          console.warn('Initial session validation check failed; preserving token for subsequent requests:', err?.message);
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api.login(email, password);
    setTokenState(data.token);
    setUser(data.user);
    setIsAuthModalOpen(false);
  };

  const register = async (email: string, name: string, password: string) => {
    const data = await api.register(email, name, password);
    setTokenState(data.token);
    setUser(data.user);
    setIsAuthModalOpen(false);
  };

  const logout = async () => {
    await api.logout();
    setTokenState(null);
    setUser(null);
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
