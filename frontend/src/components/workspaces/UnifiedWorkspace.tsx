// frontend/src/components/workspaces/UnifiedWorkspace.tsx
'use client';

import React from 'react';
import { DocWorkspace } from './DocWorkspace';

interface UnifiedWorkspaceProps {
  initialFile?: File | null;
  initialType?: 'data' | 'document' | 'vision';
  onSendToChat?: (text: string) => void;
}

export const UnifiedWorkspace: React.FC<UnifiedWorkspaceProps> = ({
  initialFile = null,
}) => {
  return (
    <div className="w-full max-w-full overflow-hidden">
      <DocWorkspace initialFile={initialFile} />
    </div>
  );
};
