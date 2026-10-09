# AI-Diagnoser — Next.js Enterprise Frontend

A high-performance Next.js 14 web application for the **AI-Diagnoser** platform, engineered for native Vercel deployment while connecting to the authoritative FastAPI backend.

---

## Architecture & Features

- **Design System**: SamsungOne typography, functional light/dark mode tokens, crisp red accents (`#C62828` / `#EF4444`), glassmorphism, responsive desktop & mobile viewports.
- **Authoritative Backend Authentication**:
  - Secure login & registration flows with Argon2id session hashing.
  - Automatic `Authorization: Bearer <token>` injection for all protected API calls.
  - User-scoped report isolation and session revocation on logout.
- **Multimodal Analytical Workspaces**:
  1. **Home Workspace**: Drag-and-drop ingestion, natural-language query input with quick-action prompt chips, and recent analysis catalogs.
  2. **Chat with Data**: Conversational AI router interface supporting Google Gemini, Groq, and OpenAI with latency and token telemetry.
  3. **Tabular Data Diagnostics**: Schema inspection, distribution stats, missing value metrics, correlation matrix heatmaps, and automated AI insight generation.
  4. **Document Intelligence**: Multi-page PDF/Word/Text parser with page/word counters, executive summarizers, and contextual document Q&A.
  5. **Vision & Infographics**: Image dimension inspection, OCR text extraction, and quantitative chart reasoning.
  6. **Reports & Artifacts**: Persistent report synthesis (Markdown, PDF, DOCX), catalog retrieval with ownership isolation, markdown viewer, and safe deletion.
  7. **System & Blueprints**: Real-time FastAPI core telemetry, database persistence monitor, and n8n batch execution orchestration.

---

## Local Development

```bash
cd frontend
npm install
npm run dev
```

The frontend will start on [http://localhost:3000](http://localhost:3000).

API calls to `/api/v1/*` are automatically proxied to the backend via `next.config.js` rewrites (defaulting to `http://127.0.0.1:8000`).

---

## Vercel Deployment

### 1. Vercel Project Configuration
- **Framework Preset**: `Next.js`
- **Root Directory**: `frontend`
- **Build Command**: `npm run build` (or `next build`)
- **Output Directory**: `.next`

### 2. Environment Variables in Vercel
Configure the following variable in your Vercel Project Settings:

| Variable Name | Description | Example |
| :--- | :--- | :--- |
| `BACKEND_URL` | Public HTTPS URL of the hosted FastAPI Backend | `https://api.yourcompany.com` |
| `NEXT_PUBLIC_API_URL` | Optional direct API base (if bypassing rewrites) | `https://api.yourcompany.com` |

---

## Backend Requirements
The backend must run with CORS allowing the Vercel production domain:
```bash
CORS_ORIGINS="https://your-vercel-app.vercel.app,http://localhost:3000"
```
