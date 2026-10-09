// frontend/src/lib/api.ts

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  is_admin: boolean;
}

export interface HealthStatus {
  status: string;
  environment: string;
  timestamp?: number;
  latencyMs?: number;
}

export interface ProviderInfo {
  name: string;
  configured: boolean;
  model: string;
  category?: string;
}

export interface ChatResponse {
  result: string;
  provider: string;
  model_name?: string;
  telemetry?: {
    latency_ms: number;
    tokens?: number;
    timestamp: number;
  };
}

export interface DocumentParseResult {
  filename: string;
  file_type: string;
  page_count: number;
  character_count: number;
  word_count: number;
  preview: string;
  structured_metadata?: Record<string, any>;
}

export interface DataProfileResult {
  filename: string;
  row_count: number;
  column_count: number;
  columns: string[];
  numeric_columns: string[];
  categorical_columns: string[];
  missing_values: Record<string, number>;
  summary_statistics: Record<string, Record<string, number>>;
  head: Record<string, any>[];
}

export interface CorrelationResult {
  filename: string;
  columns: string[];
  correlation_matrix: Record<string, Record<string, number>>;
}

export interface VisionMetadataResult {
  filename: string;
  format: string;
  mode: string;
  width: number;
  height: number;
  aspect_ratio: string;
  size_bytes: number;
}

export interface ReportItem {
  report_id: string;
  title: string;
  content: string;
  report_type: string;
  created_at: string;
  status: string;
  owner_user_id?: number;
}

export interface WorkflowBlueprint {
  filename: string;
  title: string;
  description: string;
  node_count: number;
  size_bytes: number;
}

export interface ScheduledJob {
  job_id: string;
  name: string;
  cron: string;
  last_run: string | null;
  status: string;
}

// Configurable Base URL (defaults to Next.js API rewrite or direct backend)
const API_BASE = process.env.NEXT_PUBLIC_API_URL 
  ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '')
  : '';

class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('ai_diagnoser_token');
    }
  }

  public setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('ai_diagnoser_token', token);
      } else {
        localStorage.removeItem('ai_diagnoser_token');
      }
    }
  }

  public getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('ai_diagnoser_token');
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // Fallback to text
        const text = await res.text().catch(() => '');
        if (text) errorMsg = text;
      }
      throw new Error(errorMsg);
    }

    return res.json();
  }

  // --- Health & System ---
  public async checkHealth(): Promise<{ ok: boolean; status?: HealthStatus; latencyMs: number }> {
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/health`, { method: 'GET', cache: 'no-store' });
      const latencyMs = Math.round(performance.now() - start);
      if (res.ok) {
        const data = await res.json();
        return { ok: true, status: { ...data, latencyMs }, latencyMs };
      }
      return { ok: false, latencyMs };
    } catch {
      return { ok: false, latencyMs: Math.round(performance.now() - start) };
    }
  }

  public async getAuthStatus(): Promise<{ signup_allowed: boolean; enforce_api: boolean }> {
    return this.request('/api/v1/auth/status');
  }

  // --- Auth Endpoints ---
  public async login(email: string, password: string): Promise<{ token: string; user: User }> {
    const data = await this.request<{ token: string; user: User }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.token);
    return data;
  }

  public async register(email: string, name: string, password: string): Promise<{ token: string; user: User }> {
    const data = await this.request<{ token: string; user: User }>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, name, password }),
    });
    this.setToken(data.token);
    return data;
  }

  public async getMe(): Promise<User> {
    const data = await this.request<{ user: User }>('/api/v1/auth/me');
    return data.user;
  }

  public async logout(): Promise<void> {
    try {
      await this.request('/api/v1/auth/logout', { method: 'POST' });
    } finally {
      this.setToken(null);
    }
  }

  // --- AI Router & Chat ---
  public async getProviders(): Promise<ProviderInfo[]> {
    const data = await this.request<{ providers: ProviderInfo[] }>('/api/v1/router/providers');
    return data.providers;
  }

  public async queryRouter(
    prompt: string,
    provider: string = 'Google Gemini',
    modelName?: string
  ): Promise<ChatResponse> {
    return this.request('/api/v1/router/query', {
      method: 'POST',
      body: JSON.stringify({ prompt, provider, model_name: modelName }),
    });
  }

  public async getTelemetry(): Promise<Record<string, any>> {
    return this.request('/api/v1/router/telemetry');
  }

  // --- Document Intelligence ---
  public async parseDocument(file: File): Promise<DocumentParseResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/api/v1/documents/parse', {
      method: 'POST',
      body: formData,
    });
  }

  public async summarizeDocument(
    text: string,
    summaryType: string = 'executive',
    provider: string = 'Google Gemini'
  ): Promise<string> {
    const data = await this.request<{ result: string }>('/api/v1/documents/summarize', {
      method: 'POST',
      body: JSON.stringify({ text, summary_type: summaryType, provider }),
    });
    return data.result;
  }

  public async askDocument(
    text: string,
    question: string,
    provider: string = 'Google Gemini'
  ): Promise<string> {
    const data = await this.request<{ result: string }>('/api/v1/documents/ask', {
      method: 'POST',
      body: JSON.stringify({ text, question, provider }),
    });
    return data.result;
  }

  // --- Data Analytics ---
  public async profileData(file: File): Promise<DataProfileResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/api/v1/data/profile', {
      method: 'POST',
      body: formData,
    });
  }

  public async computeCorrelation(file: File): Promise<CorrelationResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/api/v1/data/correlation', {
      method: 'POST',
      body: formData,
    });
  }

  public async getDataInsights(
    datasetCsv: string,
    userQuery?: string,
    provider: string = 'Google Gemini'
  ): Promise<string> {
    const data = await this.request<{ result: string }>('/api/v1/data/insights', {
      method: 'POST',
      body: JSON.stringify({ dataset_csv: datasetCsv, user_query: userQuery, provider }),
    });
    return data.result;
  }

  // --- Vision & Infographics ---
  public async getImageMetadata(file: File): Promise<VisionMetadataResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/api/v1/vision/metadata', {
      method: 'POST',
      body: formData,
    });
  }

  public async analyzeVision(
    imageBase64: string,
    taskType: string = 'describe',
    customPrompt?: string,
    provider: string = 'Google Gemini'
  ): Promise<string> {
    const data = await this.request<{ result: string }>('/api/v1/vision/analyze', {
      method: 'POST',
      body: JSON.stringify({
        image_base64: imageBase64,
        task_type: taskType,
        custom_prompt: customPrompt,
        provider,
      }),
    });
    return data.result;
  }

  // --- Reports & Automation ---
  public async generateReport(
    title: string,
    content: string,
    reportType: string = 'markdown',
    recipientEmail?: string,
    slackChannel?: string
  ): Promise<ReportItem> {
    return this.request('/api/v1/n8n/reports/generate', {
      method: 'POST',
      body: JSON.stringify({
        title,
        content,
        report_type: reportType,
        recipient_email: recipientEmail,
        slack_channel: slackChannel,
      }),
    });
  }

  public async listReports(): Promise<ReportItem[]> {
    return this.request('/api/v1/n8n/reports');
  }

  public async getReport(reportId: string): Promise<ReportItem> {
    return this.request(`/api/v1/n8n/reports/${reportId}`);
  }

  public async deleteReport(reportId: string): Promise<{ status: string }> {
    return this.request(`/api/v1/n8n/reports/${reportId}`, {
      method: 'DELETE',
    });
  }

  public async listWorkflows(): Promise<WorkflowBlueprint[]> {
    return this.request('/api/v1/n8n/workflows');
  }

  public async listSchedules(): Promise<ScheduledJob[]> {
    return this.request('/api/v1/n8n/schedules');
  }

  public async triggerSchedule(jobId: string, provider: string = 'Google Gemini'): Promise<any> {
    return this.request('/api/v1/n8n/schedules/trigger', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId, provider }),
    });
  }
}

export const api = new ApiClient();
