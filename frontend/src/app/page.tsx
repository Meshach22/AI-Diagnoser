// frontend/src/app/page.tsx
'use client';

import React, { useState } from 'react';
import { Header } from '@/components/layout/Header';
import { Sidebar, WorkspaceTab } from '@/components/layout/Sidebar';
import { HomeWorkspace } from '@/components/workspaces/HomeWorkspace';
import { ChatWorkspace } from '@/components/workspaces/ChatWorkspace';
import { UnifiedWorkspace } from '@/components/workspaces/UnifiedWorkspace';
import { ReportsWorkspace } from '@/components/workspaces/ReportsWorkspace';
import { SystemWorkspace } from '@/components/workspaces/SystemWorkspace';

export default function AppHome() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('home');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileType, setSelectedFileType] = useState<'data' | 'document' | 'vision'>('data');
  const [activeChatPrompt, setActiveChatPrompt] = useState<string>('');

  const handleFileLoaded = (file: File, type: 'data' | 'document' | 'vision') => {
    setSelectedFile(file);
    setSelectedFileType(type);
    setActiveTab('unified');
  };

  const handleQuerySubmit = (query: string) => {
    setActiveChatPrompt(query);
    setActiveTab('chat');
  };

  return (
    <div className="app-container">
      {/* Left Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Viewport */}
      <div className="main-layout">
        <Header />

        <main className="content-viewport">
          {activeTab === 'home' && (
            <HomeWorkspace
              onSelectTab={setActiveTab}
              onFileLoaded={handleFileLoaded}
              onQuerySubmit={handleQuerySubmit}
            />
          )}

          {activeTab === 'chat' && (
            <ChatWorkspace
              initialPrompt={activeChatPrompt}
            />
          )}

          {activeTab === 'unified' && (
            <UnifiedWorkspace
              initialFile={selectedFile}
              initialType={selectedFileType}
              onSendToChat={handleQuerySubmit}
            />
          )}

          {activeTab === 'reports' && (
            <ReportsWorkspace />
          )}

          {activeTab === 'system' && (
            <SystemWorkspace />
          )}
        </main>
      </div>
    </div>
  );
}
