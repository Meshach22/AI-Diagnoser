// frontend/src/lib/api.ts

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  is_admin: boolean;
  picture?: string;
  avatar_url?: string;
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
  response?: string;
  provider: string;
  active_provider?: string;
  primary_provider?: string;
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
  full_text?: string;
  char_count?: number;
  reading_time_min?: number;
  pages_or_chunks?: string[];
  structured_metadata?: Record<string, any>;
  has_extractable_text?: boolean;
}

export interface DocumentIngestApiResponse {
  filename: string;
  file_type: string;
  word_count?: number;
  char_count?: number;
  character_count?: number;
  page_count?: number;
  reading_time_min?: number;
  full_text?: string;
  preview?: string;
  pages_or_chunks?: string[];
  has_extractable_text?: boolean;
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
const getApiBase = (): string => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL;
  if (envUrl && typeof envUrl === 'string') {
    return envUrl.trim().replace(/\/$/, '');
  }
  return '';
};
const API_BASE = getApiBase();

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
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('ai_diagnoser_token');
      if (stored) {
        this.token = stored;
        return stored;
      }
    }
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = 90000
  ): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    const token = this.getToken() || (typeof window !== 'undefined' ? localStorage.getItem('ai_diagnoser_token') : null);
    if (token && token.trim()) {
      headers['Authorization'] = `Bearer ${token.trim()}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const controller = new AbortController();
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    if (timeoutMs > 0) {
      timeoutId = setTimeout(() => {
        controller.abort();
      }, timeoutMs);
    }

    if (options.signal) {
      options.signal.addEventListener('abort', () => controller.abort());
    }

    try {
      const res = await fetch(url, {
        credentials: options.credentials || 'include',
        ...options,
        headers,
        signal: controller.signal,
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

        if (res.status === 401) {
          if (typeof window !== 'undefined') {
            window.dispatchEvent(
              new CustomEvent('ai_diagnoser_auth_expired', {
                detail: { message: errorMsg, endpoint, status: 401 },
              })
            );
          }
        }

        throw new Error(errorMsg);
      }

      return await res.json();
    } catch (err: any) {
      if (err.name === 'AbortError' || controller.signal.aborted) {
        throw new Error(
          `Request timed out after ${Math.round(timeoutMs / 1000)}s. The backend server may be waking up from sleep or experiencing high load. Please try again in a few moments.`
        );
      }
      if (err.message === 'Failed to fetch' || (err instanceof TypeError && String(err.message).toLowerCase().includes('fetch'))) {
        throw new Error(
          'Unable to communicate with the AI-Diagnoser backend service (Failed to fetch). ' +
          'The server may be waking up from cold start (Render free tier), or network connectivity was interrupted. ' +
          'Please verify your connection and retry in a few moments.'
        );
      }
      throw err;
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    }
  }

  // --- Health & System ---
  public async checkHealth(): Promise<{
    ok: boolean;
    status?: HealthStatus;
    latencyMs: number;
    isWaking?: boolean;
    error?: string;
  }> {
    const start = performance.now();
    const healthUrl = API_BASE ? `${API_BASE}/api/v1/health` : '/api/v1/health';
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const res = await fetch(healthUrl, {
        method: 'GET',
        cache: 'no-store',
        credentials: 'include',
        signal: controller.signal,
      });
      const latencyMs = Math.round(performance.now() - start);
      if (res.ok) {
        const data = await res.json();
        return { ok: true, status: { ...data, latencyMs }, latencyMs, isWaking: false };
      }
      if (res.status === 404) {
        const altUrl = API_BASE ? `${API_BASE}/health` : '/health';
        const altRes = await fetch(altUrl, { method: 'GET', cache: 'no-store' });
        if (altRes.ok) {
          const altData = await altRes.json();
          return { ok: true, status: { ...altData, latencyMs }, latencyMs, isWaking: false };
        }
      }
      const isWaking = [502, 503, 504, 520, 521, 522, 523, 524].includes(res.status);
      return {
        ok: false,
        latencyMs,
        isWaking,
        error: isWaking ? 'Server waking up (cold start)...' : `HTTP ${res.status}`,
      };
    } catch (err: any) {
      try {
        const altUrl = API_BASE ? `${API_BASE}/health` : '/health';
        const altRes = await fetch(altUrl, { method: 'GET', cache: 'no-store' });
        if (altRes.ok) {
          const altData = await altRes.json();
          const latencyMs = Math.round(performance.now() - start);
          return { ok: true, status: { ...altData, latencyMs }, latencyMs, isWaking: false };
        }
      } catch {
        // proceed
      }
      const latencyMs = Math.round(performance.now() - start);
      const isTimeout = err.name === 'AbortError' || controller.signal.aborted;
      return {
        ok: false,
        latencyMs,
        isWaking: true,
        error: isTimeout ? 'Service waking up (Render cold start)...' : 'Connecting to backend...',
      };
    } finally {
      clearTimeout(timeoutId);
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

  public async loginWithGoogle(credential: string): Promise<{ token: string; user: User }> {
    // Only the signed Google ID token is sent; the backend verifies it and derives the identity.
    const data = await this.request<{ token: string; user: User }>('/api/v1/auth/google', {
      method: 'POST',
      body: JSON.stringify({ credential }),
    });
    this.setToken(data.token);
    return data;
  }

  public async getWorkspaceMemory(): Promise<any> {
    try {
      const res = await this.request<{ memory: any }>('/api/v1/auth/memory');
      return res?.memory || null;
    } catch {
      return null;
    }
  }

  public async saveWorkspaceMemory(memory: any): Promise<void> {
    try {
      await this.request('/api/v1/auth/memory', {
        method: 'POST',
        body: JSON.stringify(memory),
      });
    } catch {
      // background sync catch
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
    const raw = await this.request<any>(
      '/api/v1/router/query',
      {
        method: 'POST',
        body: JSON.stringify({ prompt, provider, model_name: modelName }),
      },
      60000
    );
    const text = raw.response || raw.result || '';
    return {
      result: text,
      response: text,
      provider: raw.active_provider || raw.primary_provider || provider,
      active_provider: raw.active_provider || raw.primary_provider || provider,
      primary_provider: raw.primary_provider || provider,
      model_name: modelName,
      telemetry: {
        latency_ms: raw.latency_ms || 0,
        tokens: raw.tokens || 0,
        timestamp: Date.now(),
      },
    };
  }

  /**
   * Stream a chat completion over Server-Sent Events (POST /api/v1/router/query/stream).
   * `onToken` is invoked for every text piece as it arrives so the UI can render in real time.
   * There is no total-duration timeout: the request is only aborted if NO bytes (tokens or
   * heartbeats) arrive for `idleTimeoutMs`, or if the caller aborts via `signal`.
   */
  public async streamRouter(
    prompt: string,
    provider: string = 'Google Gemini',
    modelName: string | undefined,
    onToken: (token: string) => void,
    options: { signal?: AbortSignal; idleTimeoutMs?: number } = {}
  ): Promise<{ provider: string; latencyMs: number }> {
    const idleTimeoutMs = options.idleTimeoutMs ?? 60000;
    const controller = new AbortController();
    if (options.signal) {
      if (options.signal.aborted) controller.abort();
      options.signal.addEventListener('abort', () => controller.abort());
    }

    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    let timedOut = false;
    const armIdleTimer = () => {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, idleTimeoutMs);
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    const token = this.getToken();
    if (token && token.trim()) headers['Authorization'] = `Bearer ${token.trim()}`;

    armIdleTimer();
    try {
      const res = await fetch(`${API_BASE}/api/v1/router/query/stream`, {
        method: 'POST',
        headers,
        credentials: 'include',
        cache: 'no-store',
        body: JSON.stringify({ prompt, provider, model_name: modelName }),
        signal: controller.signal,
      });

      if (!res.ok) {
        let errorMsg = `HTTP Error ${res.status}`;
        try {
          const errJson = await res.json();
          if (errJson.detail) {
            errorMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
          }
        } catch {
          // keep generic message
        }
        if (res.status === 401 && typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('ai_diagnoser_auth_expired', {
              detail: { message: errorMsg, endpoint: '/api/v1/router/query/stream', status: 401 },
            })
          );
        }
        throw new Error(errorMsg);
      }
      if (!res.body) {
        throw new Error('Streaming is not supported by this browser or proxy.');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finished = false;
      let meta = { provider, latencyMs: 0 };

      const handleFrame = (frame: string) => {
        let event = 'message';
        const dataLines: string[] = [];
        for (const line of frame.split('\n')) {
          if (!line || line.startsWith(':')) continue; // comment / keep-alive
          if (line.startsWith('event:')) event = line.slice(6).trim();
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
        }
        if (!dataLines.length) return;
        let payload: any;
        try {
          payload = JSON.parse(dataLines.join('\n'));
        } catch {
          return;
        }
        if (event === 'token' && typeof payload.token === 'string') {
          onToken(payload.token);
        } else if (event === 'done') {
          finished = true;
          meta = {
            provider: payload.provider || provider,
            latencyMs: Number(payload.latency_ms) || 0,
          };
        } else if (event === 'error') {
          throw new Error(payload.message || 'The model stream failed.');
        }
      };

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        armIdleTimer(); // any bytes (tokens or heartbeats) prove the connection is alive
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
        let sep: number;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          handleFrame(frame);
        }
      }
      if (buffer.trim()) handleFrame(buffer);

      if (!finished) {
        throw new Error('The response stream ended unexpectedly. Please try again.');
      }
      return meta;
    } catch (err: any) {
      if (timedOut) {
        throw new Error(
          `No response received for ${Math.round(idleTimeoutMs / 1000)}s. The backend may be waking up from sleep; please try again in a moment.`
        );
      }
      if (err?.name === 'AbortError') {
        throw new Error('Request cancelled.');
      }
      if (err instanceof TypeError && String(err.message).toLowerCase().includes('fetch')) {
        throw new Error(
          'Unable to communicate with the AI-Diagnoser backend service (Failed to fetch). ' +
          'The server may be waking up from cold start, or network connectivity was interrupted.'
        );
      }
      throw err;
    } finally {
      if (idleTimer) clearTimeout(idleTimer);
    }
  }

  public async getTelemetry(): Promise<Record<string, any>> {
    return this.request('/api/v1/router/telemetry');
  }

  // --- Document Intelligence ---
  public normalizeDocumentParseResult(raw: DocumentIngestApiResponse): DocumentParseResult {
    const fullText = raw.full_text ?? raw.preview ?? '';
    const charCount = typeof raw.character_count === 'number'
      ? raw.character_count
      : typeof raw.char_count === 'number'
        ? raw.char_count
        : fullText.length;
    const wordCount = typeof raw.word_count === 'number'
      ? raw.word_count
      : (fullText.trim() ? fullText.trim().split(/\s+/).length : 0);
    const pageCount = typeof raw.page_count === 'number' ? raw.page_count : 1;
    const readingTime = typeof raw.reading_time_min === 'number'
      ? raw.reading_time_min
      : Math.round(Math.max(0.5, wordCount / 220) * 10) / 10;
    const hasText = typeof raw.has_extractable_text === 'boolean'
      ? raw.has_extractable_text
      : fullText.trim().length > 0;

    return {
      filename: raw.filename || 'document',
      file_type: (raw.file_type || 'TXT').toUpperCase(),
      page_count: pageCount,
      character_count: charCount,
      char_count: charCount,
      word_count: wordCount,
      preview: fullText,
      full_text: fullText,
      reading_time_min: readingTime,
      pages_or_chunks: raw.pages_or_chunks ?? (fullText ? [fullText] : []),
      structured_metadata: raw.structured_metadata,
      has_extractable_text: hasText,
    };
  }

  public async parseDocument(file: File): Promise<DocumentParseResult> {
    const formData = new FormData();
    formData.append('file', file);
    const raw = await this.request<DocumentIngestApiResponse>(
      '/api/v1/documents/parse',
      {
        method: 'POST',
        body: formData,
      },
      60000 // 60s budget for document upload, extraction, and rendering
    );
    return this.normalizeDocumentParseResult(raw);
  }

  public async summarizeDocument(
    text: string,
    summaryType: string = 'executive',
    provider: string = 'Google Gemini',
    modelName: string = 'gemini-2.5-flash'
  ): Promise<string> {
    const payload: Record<string, any> = { text, summary_type: summaryType, provider, model_name: modelName };
    const data = await this.request<{ result: string }>(
      '/api/v1/documents/summarize',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      120000
    );
    return data.result;
  }

  public async askDocument(
    text: string,
    question: string,
    provider: string = 'Google Gemini',
    chatHistory: Array<{ role: string; content: string }> = [],
    modelName: string = 'gemini-2.5-flash'
  ): Promise<string> {
    const payload: Record<string, any> = {
      text,
      question,
      query: question,
      provider,
      chat_history: chatHistory,
      history: chatHistory,
      model_name: modelName,
    };
    const data = await this.request<{ result: string }>(
      '/api/v1/documents/ask',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      120000
    );
    return data.result;
  }

  /**
   * Stream Ask-the-Document Q&A completion token-by-token using Server-Sent Events.
   * Calls /api/v1/documents/ask/stream (with automatic fallback to /api/v1/router/query/stream).
   */
  public async streamDocumentQuestion(
    text: string,
    question: string,
    provider: string = 'Google Gemini',
    modelName: string = 'gemini-2.5-flash',
    chatHistory: Array<{ role: string; content: string }> = [],
    onToken: (token: string) => void,
    options: { signal?: AbortSignal; idleTimeoutMs?: number } = {}
  ): Promise<{ provider: string; latencyMs: number }> {
    const idleTimeoutMs = options.idleTimeoutMs ?? 90000;
    const controller = new AbortController();
    if (options.signal) {
      if (options.signal.aborted) controller.abort();
      options.signal.addEventListener('abort', () => controller.abort());
    }

    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    let timedOut = false;
    const armIdleTimer = () => {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, idleTimeoutMs);
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    const token = this.getToken();
    if (token && token.trim()) headers['Authorization'] = `Bearer ${token.trim()}`;

    armIdleTimer();
    const payload = {
      text,
      question,
      query: question,
      provider,
      model_name: modelName,
      chat_history: chatHistory,
      history: chatHistory,
    };

    try {
      const streamUrl = API_BASE ? `${API_BASE}/api/v1/documents/ask/stream` : '/api/v1/documents/ask/stream';
      const res = await fetch(streamUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        credentials: 'include',
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        // Fallback to router stream with structured context prompt
        const capped = text.slice(0, 30000);
        const routerPrompt = `System Context: The user has uploaded the following document context for analysis:\n---\n${capped}\n---\nUser Query: ${question}`;
        return await this.streamRouter(routerPrompt, provider, modelName, onToken, options);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let activeProvider = provider;
      let latencyMs = 0;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        armIdleTimer();
        buffer += decoder.decode(value, { stream: true });

        let boundaryIndex = buffer.indexOf('\n\n');
        while (boundaryIndex !== -1) {
          const rawEvent = buffer.slice(0, boundaryIndex).trim();
          buffer = buffer.slice(boundaryIndex + 2);

          if (rawEvent) {
            let eventType = 'message';
            let dataStr = '';
            for (const line of rawEvent.split('\n')) {
              if (line.startsWith(':')) continue;
              if (line.startsWith('event:')) eventType = line.slice(6).trim();
              else if (line.startsWith('data:')) dataStr = line.slice(5).trim();
            }

            if (dataStr) {
              try {
                const parsed = JSON.parse(dataStr);
                if (eventType === 'token' && typeof parsed.token === 'string') {
                  onToken(parsed.token);
                } else if (eventType === 'done') {
                  if (parsed.provider) activeProvider = parsed.provider;
                  if (typeof parsed.latency_ms === 'number') latencyMs = parsed.latency_ms;
                } else if (eventType === 'error') {
                  throw new Error(parsed.message || 'Stream processing error');
                }
              } catch (parseErr: any) {
                if (eventType === 'error') throw parseErr;
              }
            }
          }
          boundaryIndex = buffer.indexOf('\n\n');
        }
      }
      return { provider: activeProvider, latencyMs };
    } catch (err: any) {
      if (timedOut) {
        throw new Error('Document stream timed out waiting for backend response.');
      }
      throw err;
    } finally {
      if (idleTimer) clearTimeout(idleTimer);
    }
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

  // --- Automation Blueprints ---
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
