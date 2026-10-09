// frontend/src/app/layout.tsx
import React from 'react';
import type { Metadata } from 'next';
import '@/styles/globals.css';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider } from '@/context/AuthContext';
import { AuthModal } from '@/components/auth/AuthModal';

export const metadata: Metadata = {
  title: 'AI Data Analyst | Enterprise Multimodal Diagnostics',
  description: 'Executive Multimodal Data Diagnostic Platform powered by Next.js and FastAPI.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AuthProvider>
            {children}
            <AuthModal />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
