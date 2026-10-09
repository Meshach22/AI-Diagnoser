# AI-Diagnoser

An enterprise-grade multimodal diagnostic intelligence system engineered with a decoupled **Streamlit Frontend**, high-performance **FastAPI Backend**, modular **Core AI Services**, multi-provider **LLM Router** (Gemini, OpenAI, Groq), and automated **n8n Workflow Engine**.

---

## 🏛️ Target Architecture

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

## 🌟 System Capabilities & Modules

### 1. Frontend: Streamlit (`main.py`)
- Clean, responsive UI with **Terracotta & Sage** design system.
- Seamless Dark/Light theme switching with real-time architecture health indicators.
- 4 interactive operational studios:
  - 📄 **Document Intelligence**
  - 👁️ **Vision Intelligence**
  - 📊 **Structured Data Analytics**
  - ⚡ **n8n Automation Engine**
- Stateful **Claude Artifacts Workspace** supporting visual diffing, version rollback, and export to Markdown, PDF, and DOCX.
- Dual-mode execution toggle: **FastAPI REST API Mode** or **Direct Core Execution Mode**.

### 2. Backend: FastAPI (`backend/`)
- Production-grade asynchronous REST API with Swagger/OpenAPI docs at `http://localhost:8000/docs`.
- **Router Layer** (`backend/routers/`): Thin HTTP controllers for `documents`, `vision`, `data`, `router`, and `n8n`.
- **Service Layer** (`backend/services/`): Encapsulated business orchestration:
  - `DocumentService`: Ingestion, parsing, executive summarization, and interactive Q&A.
  - `VisionService`: Asset geometry profiling, dominant color swatches, and multimodal OCR/inspection.
  - `DataService`: Data Health Card calculation, authoritative Pearson correlation, and AI-driven EDA insights.
  - `ChatService`: Unified multi-provider chat orchestration via the LLM router.
  - `N8nService`: Inbound webhook execution, report generation, and multi-channel notification dispatch.
- **Strict Dependency Direction**:
  $$\text{Routers} \longrightarrow \text{Services} \longrightarrow \text{Pipelines} \longrightarrow \text{Core}$$

### 3. Core AI Services (`pipelines/`)
- **Documents Pipeline** (`pipelines/document_pipeline.py`): Ingests PDF (`pypdf`), Word DOCX (`python-docx`), and plain text/Markdown.
- **Vision Pipeline** (`pipelines/image_pipeline.py`): Ingests PNG, JPG, WEBP, BMP, TIFF with EXIF normalization, downsampling, and dominant color swatches.
- **Data Pipeline** (`pipelines/data_pipeline.py`): Ingests CSV and Excel (`openpyxl`), computes Data Health Cards, authoritative Pearson correlations, and interactive Plotly figures.

### 4. LLM Router (`core/llm_router.py`)
- Multi-provider zero-cost routing with sub-second failover cascades, **fully decoupled from Streamlit** (can be executed from FastAPI, CLI, tests, and background jobs):
  - **Google Gemini**: Multimodal text & vision via `gemini-2.5-flash` / `gemini-3.8-flash`.
  - **OpenAI**: Fast multimodal reasoning via `gpt-4o-mini`.
  - **Groq Cloud**: Ultra low-latency inference via `llama-3.3-70b-versatile` & `llama-3.2-11b-vision-preview`.
  - **Ollama**: 100% private local offline inference via `http://localhost:11434`.
  - **Offline Heuristics**: Pure Python TF-IDF and PIL spatial analysis for 100% zero-config execution.

### 5. n8n Automation Engine (`n8n/`)
- **Webhooks**: Universal inbound webhooks for external events (`/api/v1/n8n/webhook`), with base64 images handled securely in POST JSON bodies.
- **Reports**: Automated report generation and cataloging with unique IDs.
- **Email & Slack Dispatch**: Transparent channel dispatch with explicit classification:
  - `REAL INTEGRATION`: When webhooks or SMTP destinations are configured.
  - `SIMULATION`: Explicitly labeled when unconfigured so delivery is never falsely reported.
- **Scheduled Jobs**: Registered cron schedules for daily tabular health checks, weekly briefings, and periodic vision scans.
- **Ready-to-import Blueprints**: Validated JSON workflow templates located in `n8n/workflows/` configured for Docker networking (`http://backend:8000`).

---

## 🚀 Quickstart Guide

### 1. Environment Setup
Copy the template configuration and supply any optional API keys:
```bash
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the FastAPI Backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at `http://localhost:8000/docs`.

### 4. Launch the Streamlit Frontend
```bash
streamlit run main.py
```
The studio interface will launch at `http://localhost:8501`.

### 5. Run with Docker Compose
To run Frontend, Backend, Nginx Gateway, and n8n simultaneously:
```bash
docker compose up -d
```
- Gateway: `http://localhost`
- Streamlit UI: `http://localhost:8501`
- FastAPI API: `http://localhost:8000/docs`
- n8n Automation: `http://localhost:5678`

---

## 🧪 Automated Testing
Run the complete unit and integration test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
