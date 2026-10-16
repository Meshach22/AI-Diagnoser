// frontend/src/app/page.tsx
'use client';

import React, { useState } from 'react';
import { Header } from '@/components/layout/Header';
import { Sidebar, WorkspaceTab } from '@/components/layout/Sidebar';
import { ChatWorkspace } from '@/components/workspaces/ChatWorkspace';
import { DocWorkspace } from '@/components/workspaces/DocWorkspace';

export default function AppHome() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('chat');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeChatPrompt, setActiveChatPrompt] = useState<string>('');

  const handleQuerySubmit = (query: string) => {
    setActiveChatPrompt(query);
    setActiveTab('chat');
  };

  return (
    <div className="app-container w-full max-w-full overflow-hidden">
      {/* Left Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Viewport */}
      <div className="main-layout w-full max-w-full overflow-hidden">
        <Header />

        <main className="content-viewport w-full max-w-full overflow-hidden">
          <div
            style={{
              display: activeTab === 'chat' ? 'flex' : 'none',
              flexDirection: 'column',
              height: '100%',
              minHeight: 0,
            }}
          >
            <ChatWorkspace initialPrompt={activeChatPrompt} />
          </div>

          <div
            style={{
              display: activeTab === 'unified' ? 'block' : 'none',
              height: '100%',
              minHeight: 0,
            }}
          >
            <DocWorkspace initialFile={selectedFile} />
          </div>
        </main>
      </div>
    </div>
  );
}
