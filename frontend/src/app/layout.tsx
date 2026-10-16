// frontend/src/app/layout.tsx
import React from 'react';
import type { Metadata } from 'next';
import Script from 'next/script';
import '@/styles/globals.css';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider } from '@/context/AuthContext';
import { AuthModal } from '@/components/auth/AuthModal';

export const metadata: Metadata = {
  title: 'AI Data Analyst | Intelligent Data Diagnostic Platform',
  description: 'AI Data Analyst - Multimodal Data Diagnostics and Document Intelligence powered by Gemini.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
      </head>
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
