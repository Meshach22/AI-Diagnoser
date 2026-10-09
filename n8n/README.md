# n8n Automation Engine Integration Guide

This directory contains production n8n workflows and configurations for **AI-Diagnoser**, enabling end-to-end automated workflows across **Webhooks**, **Diagnostic Reports**, **Email Notifications**, **Slack Alerts**, and **Scheduled Cron Jobs**.

---

## 🏗️ Architecture & Interaction Flow

```
                         AI-Diagnoser
                              │
                    ┌─────────┴─────────┐
                    │                   │
                Frontend             Backend
               Streamlit            FastAPI
                    │                   │
                    └─────────┬─────────┘
                              │
                       Core AI Services
                              │
             ┌────────────────┼────────────────┐
             │                │                │
        Documents          Vision          Data Analytics
             │                │                │
             └────────────────┼────────────────┘
                              │
                         LLM Router
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          Gemini           OpenAI           Groq
             │                │                │
             └────────────────┼────────────────┘
                              │
                             n8n
                              │
       ┌──────────────┬───────┼────────┬─────────────┐
       │              │       │        │             │
    Webhooks       Reports   Email    Slack       Scheduled Jobs
```

---

## 📦 Ready-to-Import Workflow Blueprints

The `workflows/` directory contains standard n8n JSON definitions ready for one-click import into n8n:

1. **`ai_diagnoser_webhook_pipeline.json`**
   - **Trigger**: Inbound HTTP Webhook (`/webhook/ai-diagnoser`)
   - **Process**: Transmits document or image content to FastAPI Backend (`/api/v1/n8n/webhook`)
   - **Formatting**: Summarizes and formats findings into actionable alerts
   - **Dispatch**: Posts formatted Block Kit alert to **Slack** and sends executive dossier to **Email**
   - **Response**: Returns completed status and diagnostics payload to caller

2. **`ai_diagnoser_scheduled_batch_job.json`**
   - **Trigger**: Schedule Cron Trigger (Daily Mon–Fri at 09:00 AM)
   - **Process**: Triggers registered batch audit (`/api/v1/n8n/schedules/trigger`)
   - **Output**: Generates cataloged diagnostic report (`/api/v1/n8n/reports/generate`)
   - **Alert**: Pushes health summary to Slack `#audits-daily`

3. **`ai_diagnoser_multimodal_router.json`**
   - **Trigger**: Universal Inbound Webhook (`/webhook/triage`)
   - **Routing**: Inspects incoming payload modality (`document`, `vision`, `data`) and routes directly to the specialized FastAPI Core AI Service
   - **Response**: Returns unified JSON diagnosis with model latency and provider telemetry

---

## 🚀 Quickstart: Running n8n with AI-Diagnoser

### Option A: Running with Docker Compose (Recommended)
You can start n8n alongside AI-Diagnoser using Docker Compose:

```bash
# Start backend, frontend, and n8n
docker compose up -d n8n backend frontend
```

n8n will be accessible in your browser at:
`http://localhost:5678`

### Option B: Running n8n Standalone via Docker
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -e N8N_HOST=localhost \
  -e WEBHOOK_URL=http://localhost:5678/ \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n:latest
```

---

## 📥 How to Import Workflows into n8n

1. Open your n8n interface (`http://localhost:5678`).
2. Go to **Workflows** → Click **Add Workflow** (or `+`).
3. Click the top-right menu (`...`) → Select **Import from File**.
4. Choose any JSON file from `n8n/workflows/`:
   - `ai_diagnoser_webhook_pipeline.json`
   - `ai_diagnoser_scheduled_batch_job.json`
   - `ai_diagnoser_multimodal_router.json`
5. Activate the workflow!

---

## ⚙️ Environment Variables

Add these to your `.env` or Docker configuration:

```env
# n8n Automation Engine
N8N_BASE_URL=http://localhost:5678
N8N_WEBHOOK_URL=http://localhost:5678/webhook/ai-diagnoser
N8N_EMAIL_WEBHOOK_URL=http://localhost:5678/webhook/send-email
N8N_SLACK_WEBHOOK_URL=http://localhost:5678/webhook/slack-alert

# Direct Slack Incoming Webhook (Optional fallback)
SLACK_INCOMING_WEBHOOK=https://hooks.slack.com/services/T00/B00/XXXX
```
