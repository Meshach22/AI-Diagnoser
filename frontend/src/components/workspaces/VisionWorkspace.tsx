// frontend/src/components/workspaces/VisionWorkspace.tsx
'use client';

import React, { useState } from 'react';
import { api, VisionMetadataResult } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  Image as ImageIcon,
  Upload,
  Eye,
  ScanText,
  LineChart,
  Sparkles,
  FileSearch,
} from 'lucide-react';

interface VisionWorkspaceProps {
  initialFile?: File | null;
}

export const VisionWorkspace: React.FC<VisionWorkspaceProps> = ({ initialFile = null }) => {
  const { user, openAuthModal } = useAuth();
  const [file, setFile] = useState<File | null>(initialFile);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [base64, setBase64] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<VisionMetadataResult | null>(null);
  const [taskType, setTaskType] = useState<string>('describe');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (selectedFile: File) => {
    if (!user) {
      openAuthModal();
      return;
    }
    setFile(selectedFile);
    setLoading(true);
    setError(null);
    setMetadata(null);
    setResult(null);

    // Read preview & base64
    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = reader.result as string;
      setPreviewUrl(b64);
      setBase64(b64.split(',')[1] || b64);

      try {
        const meta = await api.getImageMetadata(selectedFile);
        setMetadata(meta);
      } catch (err: any) {
        setError(err.message || 'Failed to inspect image metadata.');
      } finally {
        setLoading(false);
      }
    };
    reader.readAsDataURL(selectedFile);
  };

  const handleAnalyze = async () => {
    if (!base64 || !user) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.analyzeVision(
        base64,
        taskType,
        customPrompt.trim() || undefined
      );
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze image telemetry.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Upload Header */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div className="brand-icon-box" style={{ width: 40, height: 40 }}>
              <ImageIcon size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {file ? file.name : 'Vision & Infographics Diagnostics'}
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                {file ? `${(file.size / 1024).toFixed(1)} KB • Multimodal visual inspection` : 'Upload dashboard screenshots, architectural diagrams, or infographic charts'}
              </p>
            </div>
          </div>

          <label className="btn btn-outline" style={{ cursor: 'pointer' }}>
            <Upload size={15} />
            <span>{file ? 'Replace Image' : 'Upload Image'}</span>
            <input
              type="file"
              style={{ display: 'none' }}
              accept=".png,.jpg,.jpeg,.webp"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
            />
          </label>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.12)', color: 'var(--accent-red)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239, 68, 68, 0.25)', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {previewUrl && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
          {/* Image Canvas View */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
              Image Telemetry Preview
            </div>
            <div
              style={{
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                maxHeight: 380,
              }}
            >
              <img
                src={previewUrl}
                alt="Uploaded diagnostic image"
                style={{ maxWidth: '100%', maxHeight: 380, objectFit: 'contain' }}
              />
            </div>

            {metadata && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, textAlign: 'center' }}>
                <div style={{ padding: '8px 4px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Dimensions</div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600 }}>{metadata.width} × {metadata.height}</div>
                </div>
                <div style={{ padding: '8px 4px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Format</div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600 }}>{metadata.format}</div>
                </div>
                <div style={{ padding: '8px 4px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Aspect Ratio</div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 600 }}>{metadata.aspect_ratio}</div>
                </div>
              </div>
            )}
          </div>

          {/* Diagnostic Controls & Output */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
              Multimodal Analysis Objective
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              <button
                className={`btn ${taskType === 'describe' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => setTaskType('describe')}
              >
                <Eye size={14} />
                <span>General Inspection</span>
              </button>
              <button
                className={`btn ${taskType === 'ocr' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => setTaskType('ocr')}
              >
                <ScanText size={14} />
                <span>OCR Text Extract</span>
              </button>
              <button
                className={`btn ${taskType === 'chart_reasoning' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => setTaskType('chart_reasoning')}
              >
                <LineChart size={14} />
                <span>Quantitative Chart Logic</span>
              </button>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                Specific Prompt / Question (Optional)
              </label>
              <textarea
                className="textarea"
                placeholder="e.g. Which metric peaked highest in Q3, and what was the percentage change?"
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                style={{ minHeight: 70 }}
              />
            </div>

            <button
              className="btn btn-primary"
              onClick={handleAnalyze}
              disabled={loading}
              style={{ width: '100%' }}
            >
              <Sparkles size={16} />
              <span>{loading ? 'Evaluating Multimodal Pixels...' : 'Run Vision Diagnosis'}</span>
            </button>

            {result && (
              <div
                style={{
                  marginTop: 10,
                  padding: 14,
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-soft)',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}
              >
                <div style={{ fontWeight: 700, color: 'var(--accent-red)', marginBottom: 6 }}>
                  Diagnostic Finding:
                </div>
                {result}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
