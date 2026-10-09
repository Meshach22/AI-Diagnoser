# AI-Diagnoser: Post-Refactor Architecture Audit Report

**Audit Date**: October 8, 2026  
**Auditor**: Antigravity Assistant  
**Repository**: `shalom1109/AI-Diagnoser` (`D:\ai data diagoniser\AI-Diagnoser`)  
**Commit/State**: Post initial FastAPI, Core Services, LLM Router, and n8n integration  

---

## Executive Summary

An architectural audit was performed on the current codebase following the initial implementation of the FastAPI backend, n8n integrations, and multi-tier routing. While basic API endpoints exist and local integration tests pass, **the repository currently operates in a hybrid state rather than a clean decoupled architecture**. 

Crucially:
1. **Security Alert**: Live, plaintext API keys for multiple providers are committed and actively tracked in Git (`.streamlit/secrets.toml`).
2. **Architecture Decoupling**: Streamlit still directly imports and executes the document, vision, and data pipelines in-process, bypassing the FastAPI backend for ingestion, profiling, and artifacts workspace execution.
3. **Missing Service Layer**: FastAPI routers communicate directly with pipelines and contain route-level business and numerical calculations.
4. **n8n Automation Boundary**: The n8n integration is currently **simulated** via in-memory dictionaries and mock fallbacks; no actual n8n daemon or external webhooks are verified in runtime, and workflow JSON blueprints contain circular callbacks and hardcoded `localhost` endpoints that fail in Docker networks.
5. **Docker Execution Blocker**: The `Dockerfile` hardcodes `ENTRYPOINT ["streamlit", ...]`, causing the `backend` container defined in `docker-compose.yml` to fail on boot due to argument collision with `uvicorn`.

---

## A. Current Directory Tree

```
AI-Diagnoser/
├── .gitignore                                 # Added during refactor (untracked in git)
├── .streamlit/
│   ├── config.toml                            # Streamlit server and theme configuration
│   └── secrets.toml                           # CRITICAL: Plaintext API keys tracked in Git
├── Dockerfile                                 # Single-stage Streamlit image (ENTRYPOINT conflict)
├── README.md                                  # Architectural documentation (contains overstated claims)
├── requirements.txt                           # Dependencies catalog
├── docker-compose.yml                         # 4-service compose (Nginx, Backend, Frontend, n8n)
├── main.py                                    # Streamlit frontend application (retains pipeline bypasses)
├── backend/
│   ├── __init__.py
│   ├── config.py                              # Backend settings & secrets resolution
│   ├── main.py                                # FastAPI application entrypoint
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── data.py                            # /api/v1/data (contains route-level business logic)
│   │   ├── documents.py                       # /api/v1/documents (bypasses service layer)
│   │   ├── n8n.py                             # /api/v1/n8n (webhook, dispatch, schedules)
│   │   ├── router.py                          # /api/v1/router (LLM HTTP adapter)
│   │   └── vision.py                          # /api/v1/vision (bypasses service layer)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── data.py                            # Data request/response Pydantic schemas
│   │   ├── documents.py                       # Document Pydantic schemas
│   │   ├── n8n.py                             # n8n payloads, dispatch, and job schemas
│   │   ├── router.py                          # LLM query and provider schemas
│   │   └── vision.py                          # Vision request/response schemas
│   └── services/
│       ├── __init__.py
│       └── n8n_service.py                     # n8n service (contains in-memory mock storage)
├── core/
│   ├── __init__.py
│   ├── backend_client.py                      # HTTP client bridge from Streamlit to FastAPI
│   ├── config.py                              # Model catalogs, color tokens, font presets
│   ├── llm_router.py                          # Monolithic 1440-line router (coupled to Streamlit)
│   ├── styles.py                              # CSS theme injector (SF Pro, dark/light porcelain)
│   ├── telemetry.py                           # Event logger to logs/telemetry.jsonl
│   └── ui_components.py                       # Claude Artifacts, 3D Monolith, diagnostics UI
├── n8n/
│   ├── README.md                              # n8n deployment guide
│   └── workflows/
│       ├── ai_diagnoser_multimodal_router.json # Multi-branch triage workflow
│       ├── ai_diagnoser_scheduled_batch_job.json# Scheduled audit workflow
│       └── ai_diagnoser_webhook_pipeline.json # Webhook to Slack & Email workflow
├── nginx/
│   └── default.conf                           # Reverse proxy routing /api -> backend, / -> frontend
├── pipelines/
│   ├── __init__.py
│   ├── data_pipeline.py                       # Tabular loading, health card, Plotly figures
│   ├── document_pipeline.py                   # PDF, DOCX, TXT extraction and Q&A
│   └── image_pipeline.py                      # Pillow normalization, EXIF, color quantization
├── sample_data/
│   ├── sample_business_metrics.csv
│   ├── sample_financial_report.txt
│   └── sample_performance_chart.png
├── scratch/
│   └── ai_test_matrix_results.json            # Tracked test artifact
├── tests/
│   ├── locustfile.py                          # Load testing script
│   ├── run_uat.py                             # User acceptance test runner
│   ├── test_claude_artifacts.py               # Unit tests for artifact engine
│   ├── test_export_pipeline.py                # Unit tests for PDF/DOCX export
│   ├── test_fastapi_backend.py                # 11-step backend test suite (hybrid real/simulated)
│   └── test_llm_router.py                     # Direct LLM router unit tests
└── logs/
    └── telemetry.jsonl                        # Tracked runtime log file
```

---

## B. Dependency Flow Analysis

```mermaid
graph TD
    subgraph Frontend["Streamlit Frontend (main.py)"]
        UI[Streamlit UI]
        BC[BackendClient (backend_client.py)]
    end

    subgraph Backend["FastAPI Backend (backend/main.py)"]
        R_DOC[routers/documents.py]
        R_VIS[routers/vision.py]
        R_DAT[routers/data.py]
        R_ROU[routers/router.py]
        R_N8N[routers/n8n.py]
        S_N8N[services/n8n_service.py]
    end

    subgraph CoreServices["Core AI Pipelines (pipelines/)"]
        P_DOC[document_pipeline.py]
        P_VIS[image_pipeline.py]
        P_DAT[data_pipeline.py]
    end

    subgraph LLM["LLM Router (core/llm_router.py)"]
        ROUTER[LLMRouter Engine]
        GEMINI[Google Gemini]
        OPENAI[OpenAI]
        GROQ[Groq Cloud]
        OFFLINE[Offline Heuristics]
    end

    subgraph Automation["n8n Automation"]
        N8N_WF[Workflow Blueprints]
    end

    %% Actual flows
    UI -->|HTTP Calls| BC
    BC -->|REST API| Backend
    UI -.->|DIRECT BYPASS IMPORTS| CoreServices
    UI -.->|DIRECT BYPASS IMPORTS| ROUTER

    R_DOC -->|Direct Call| P_DOC
    R_VIS -->|Direct Call| P_VIS
    R_DAT -->|Direct Call| P_DAT
    R_ROU -->|Direct Call| ROUTER
    R_N8N -->|Service Call| S_N8N

    S_N8N -->|Direct Call| P_DAT
    S_N8N -->|Direct Call| ROUTER

    P_DOC --> ROUTER
    P_VIS --> ROUTER
    P_DAT --> ROUTER

    ROUTER --> GEMINI
    ROUTER --> OPENAI
    ROUTER --> GROQ
    ROUTER --> OFFLINE
```

### Dependency Findings:
1. **Frontend-to-Backend Coupling**: The frontend does not solely communicate through HTTP (`BackendClient`). It directly imports `document_pipeline`, `image_pipeline`, `data_pipeline`, and `LLMRouter`.
2. **Missing Backend Service Abstraction**: `routers/documents.py`, `routers/vision.py`, and `routers/data.py` directly call the pipeline layer without an intermediate `backend/services/` orchestration layer.
3. **Core-to-Streamlit Coupling**: `core/llm_router.py` contains `import streamlit as st` statements and inspects `st.session_state` and `st.secrets` for telemetry and API key resolution. When executed in FastAPI, this produces runtime context warnings (`missing ScriptRunContext`).

---

## C. Streamlit → Backend Flow & Bypass Audit

The desired architecture requires all user actions in Streamlit to traverse `backend_client.py` → `FastAPI`. 

### Bypass Inventory:

| Operation | Current Execution Path | Target Architecture Path | Severity |
| :--- | :--- | :--- | :--- |
| **Document Ingestion** | Direct `pipelines.document_pipeline.load_document()` in Streamlit | Streamlit → `POST /api/v1/documents/upload` | **CRITICAL** |
| **Document Summarization** | Conditional: Calls `backend_client.summarize_document()` IF in FastAPI mode, otherwise direct pipeline | Streamlit → `POST /api/v1/documents/summarize` (Mandatory) | **HIGH** |
| **Ask the Document** | Conditional: Calls `backend_client.ask_document()` IF in FastAPI mode | Streamlit → `POST /api/v1/documents/ask` | **HIGH** |
| **Claude Artifacts Workspace** | Directly executes `render_claude_artifact_workspace(router=router)` invoking in-process LLM | Streamlit → FastAPI Artifact/Chat endpoint | **CRITICAL** |
| **Image Ingestion & Exif** | Direct `pipelines.image_pipeline.load_image()` & `extract_image_metadata()` in Streamlit | Streamlit → `POST /api/v1/vision/metadata` | **CRITICAL** |
| **Dominant Colors Quantization** | Direct `pipelines.image_pipeline.extract_dominant_colors()` in Streamlit | Streamlit → `POST /api/v1/vision/metadata` | **HIGH** |
| **Vision OCR Analysis** | Conditional: Calls `backend_client.analyze_vision()` IF in FastAPI mode | Streamlit → `POST /api/v1/vision/analyze` | **HIGH** |
| **Tabular Data Loading** | Direct `pipelines.data_pipeline.load_structured_data()` in Streamlit | Streamlit → `POST /api/v1/data/profile` | **CRITICAL** |
| **Data Health Card Diagnostics** | Direct `pipelines.data_pipeline.generate_data_health_card()` in Streamlit | Streamlit → `POST /api/v1/data/profile` | **CRITICAL** |
| **Plotly Figures Generation** | Direct `pipelines.data_pipeline.create_*_plot()` in Streamlit | Streamlit requests chart specs or renders from API JSON contract | **MEDIUM** |
| **AI Dataset Intelligence (EDA)** | Conditional: Calls `backend_client.get_data_insights()` IF in FastAPI mode | Streamlit → `POST /api/v1/data/insights` | **HIGH** |
| **Execution Mode Radio Button** | Allows user to toggle "Direct Core Engine", entirely bypassing the backend | Remove mode switch; Streamlit must be a pure presentation client | **HIGH** |

---

## D. FastAPI → Service → Pipeline Flow

The current implementation in `backend/` lacks a consistent Service layer:

### 1. Document Routing (`backend/routers/documents.py`)
- **Route**: `POST /upload`  
  - Directly calls `load_document(content, filename)`.
  - **Verdict**: MISWIRED (skips service layer).
- **Route**: `POST /summarize`  
  - Directly calls `generate_document_summary(...)`.
  - **Verdict**: MISWIRED (skips service layer).
- **Route**: `POST /ask`  
  - Directly calls `ask_document_question(...)`.
  - **Verdict**: MISWIRED (skips service layer).

### 2. Vision Routing (`backend/routers/vision.py`)
- **Route**: `POST /metadata`  
  - Directly calls `load_image`, `extract_image_metadata`, and `extract_dominant_colors`.
  - Performs custom list comprehensions inside the router function.
  - **Verdict**: MISWIRED (business logic in router).
- **Route**: `POST /analyze`  
  - Directly calls `analyze_image_with_llm(...)`.
  - **Verdict**: MISWIRED (skips service layer).

### 3. Data Routing (`backend/routers/data.py`)
- **Route**: `POST /profile`  
  - Directly calls `load_structured_data` and `generate_data_health_card`.
  - Serializes DataFrames to dict inside the router function.
  - **Verdict**: MISWIRED (skips service layer).
- **Route**: `POST /insights`  
  - Directly parses CSV with pandas `pd.read_csv(io.StringIO(...))` inside route.
  - Calls `generate_data_insights`.
  - **Verdict**: MISWIRED (business logic & pandas manipulation in router).
- **Route**: `POST /correlation`  
  - Directly calls `num_df = df.select_dtypes(include=[np.number])` and `corr = num_df.corr().round(4)` inside route.
  - Returns an untyped dictionary.
  - **Verdict**: MISWIRED / UNTYPED.

### 4. Service Layer (`backend/services/`)
- Only `n8n_service.py` exists.
- `DocumentService`, `VisionService`, and `DataAnalyticsService` are **MISSING**.

---

## E. LLM Routing Flow & Duplication Check

The user specifically requested verification of:
`core/llm_router.py` vs `backend/routers/router.py`

### Findings:
1. **No Logic Duplication**: `backend/routers/router.py` does **NOT** reimplement LLM routing logic. It is a thin FastAPI router that imports `query_llm` and `get_last_telemetry` from `core/llm_router.py`.
2. **Naming Ambiguity**: Having `backend/routers/router.py` and `core/llm_router.py` creates semantic confusion. The backend router should be named `backend/routers/llm.py` to clarify that it is an HTTP route endpoint, not an LLM router.
3. **Monolithic Coupling in `core/llm_router.py`**:
   - Total lines: 1,440 lines.
   - Contains 6 distinct provider adapters in a single file (`_query_gemini`, `_query_openai`, `_query_deepseek`, `_query_groq`, `_query_ollama`, `_query_offline`).
   - Contains full image compression logic (`compress_and_downsample_image`).
   - Contains a pure-Python TF-IDF engine (`OfflineHeuristicsEngine`).
   - Contains string manipulation for Claude artifacts (`_clean_artifact_markdown`).
   - Tightly coupled to Streamlit:
     ```python
     # Line 75 in core/llm_router.py
     import streamlit as st
     if hasattr(st, "secrets") and key_name in st.secrets:
         ...
     ```
   - **Verdict**: WORKING, but ARCHITECTURALLY CONFLATED and COUPLED TO STREAMLIT.

---

## F. n8n Integration Flow & Boundary Audit

### 1. Separation of Concerns:
- **n8n Workflow Definitions**: Exists in `n8n/workflows/*.json` (VALID JSON structures).
- **FastAPI n8n Integration**: Exists in `backend/routers/n8n.py` (WORKING endpoints).
- **Simulated / Local Helper Functions**:
  - `dispatch_email`: Returns `"local_simulation"` if `N8N_EMAIL_WEBHOOK_URL` is empty.
  - `dispatch_slack`: Returns `"local_simulation"` if `N8N_SLACK_WEBHOOK_URL` is empty.
  - `SCHEDULED_JOBS`: In-memory Python dictionary; no persistent storage or cron scheduler.
  - `GENERATED_REPORTS`: In-memory Python dictionary; vanishes on backend restart.
- **Actual HTTP Communication with n8n**:
  - Only occurs if an active n8n instance is explicitly running and configured via environment variables. In test runs, this is **NOT TESTED** against a live n8n instance.
- **Actual n8n Execution**: **SIMULATED** in current test suite.

### 2. Architectural Boundary Violations:
- In `n8n/workflows/ai_diagnoser_webhook_pipeline.json`:
  - Node 4 ("Slack: Send Block Kit Alert") and Node 5 ("Email: Dispatch Diagnostic Dossier") are configured as HTTP Request nodes calling **BACK** into the FastAPI backend (`/api/v1/n8n/dispatch/slack` and `/api/v1/n8n/dispatch/email`).
  - And inside FastAPI, `N8nService.dispatch_slack` attempts to POST to `settings.N8N_SLACK_WEBHOOK_URL`!
  - **Verdict**: MISWIRED / CIRCULAR CALL. In a clean architecture, n8n handles Slack and Email dispatch natively via its official Slack and Send Email nodes, or FastAPI dispatches directly to Slack webhooks. Having n8n call FastAPI to call n8n creates a circular loop.
- Hardcoded URLs:
  - All 3 workflow JSONs hardcode `http://localhost:8000/api/v1/...`.
  - When n8n runs inside Docker via `docker-compose.yml`, `localhost:8000` refers to the n8n container, resulting in `ECONNREFUSED`. It must use `http://backend:8000` in Docker networks.
  - **Verdict**: MISWIRED FOR DOCKER.

---

## G. Docker & Container Flow Audit

### 1. `Dockerfile`
- The `Dockerfile` ends with:
  ```dockerfile
  ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
  ```
- In `docker-compose.yml`, the `backend` service specifies:
  ```yaml
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- **CRITICAL DOCKER DEFECT**: When an image defines an `ENTRYPOINT`, Docker appends the `command` arguments to the entrypoint. The resulting process execution is:
  `streamlit run main.py ... uvicorn backend.main:app ...`
  This causes the backend container to fail immediately on startup.
- **Verdict**: PRODUCTION-UNSAFE / BROKEN.

### 2. Environment Variables & `.env`
- Both `backend` and `streamlit-app` specify:
  ```yaml
  env_file:
    - .env
  ```
- There is currently **no `.env` file** on disk in the repository. Running `docker compose up` on a clean checkout will fail with `open .env: no such file or directory`.
- **Verdict**: PRODUCTION-UNSAFE.

---

## H. Test Coverage Audit: "11 Tests Passed"

The test file `tests/test_fastapi_backend.py` contains 11 tests. Below is the strict classification of each test:

| Test Name | Target Tested | Real / Mocked / Superficial | Rationale |
| :--- | :--- | :--- | :--- |
| `test_health_check` | `GET /health` | **REAL** | Verifies FastAPI application boots and health contract holds. |
| `test_root_architecture_index` | `GET /` | **REAL** | Verifies API root gateway documentation and links. |
| `test_router_providers_catalog` | `GET /api/v1/router/providers` | **REAL** | Verifies provider catalog response schema. |
| `test_document_summarization` | `POST /api/v1/documents/summarize` | **SUPERFICIAL** | Explicitly requests `"provider": "Offline Heuristics"`. Does NOT test real LLM API communication or provider adapters. |
| `test_data_profiling` | `POST /api/v1/data/profile` | **REAL** | Tests real multipart file upload, pandas processing, and health card serialization. |
| `test_n8n_webhook_ingestion` | `POST /api/v1/n8n/webhook` | **SUPERFICIAL / SIMULATED** | Tests in-process execution using Offline Heuristics; no actual n8n webhook communication occurs. |
| `test_n8n_report_generation` | `POST /api/v1/n8n/reports/generate` | **MOCKED / IN-MEMORY** | Writes to in-memory Python dictionary `GENERATED_REPORTS`. Does not test persistent storage. |
| `test_n8n_slack_dispatch` | `POST /api/v1/n8n/dispatch/slack` | **SIMULATED** | Without `SLACK_WEBHOOK_URL`, it returns `delivered_via="local_simulation"`. No real Slack API or delivery verification. |
| `test_n8n_email_dispatch` | `POST /api/v1/n8n/dispatch/email` | **SIMULATED** | Without `N8N_EMAIL_WEBHOOK_URL`, it returns `delivered_via="local_simulation"`. No SMTP or email node delivery verification. |
| `test_n8n_schedules_list` | `GET /schedules` & `POST /schedules/trigger` | **MOCKED / IN-MEMORY** | Operates on hardcoded in-memory dict `SCHEDULED_JOBS`. No cron daemon or real schedule trigger. |
| `test_n8n_workflows_catalog` | `GET /api/v1/n8n/workflows` | **REAL** | Reads filesystem JSON files and verifies presence and structure. |

**Summary**: Only 5 of 11 tests verify real end-to-end functionality. 6 of 11 tests test local simulations or offline fallbacks. Claiming full system readiness based on these tests is inaccurate.

---

## I. Security Audit

Search across the entire repository for credentials, tokens, and tracking status:

| File | Type | Status | Exposure Risk |
| :--- | :--- | :--- | :--- |
| `.streamlit/secrets.toml` | Plaintext API Keys (`gemini_api_key`, `groq_api_key`, `openai_api_key`, `deepseek_api_key`) | **COMPROMISED** | Tracked in Git history. Committed in initial clone from public/remote repository. |
| `logs/telemetry.jsonl` | Runtime audit logs (contains user prompt texts, session IDs) | **PRODUCTION-UNSAFE** | Tracked in Git history. |
| `scratch/ai_test_matrix_results.json` | Internal test execution artifacts | **DIRTY** | Tracked in Git history. |
| `__pycache__/*.pyc` | Compiled bytecode files | **DIRTY** | Multiple `.pyc` files tracked in Git repository root and subdirectories. |

---

## Component Status Classification Matrix

| Component | Status | Detailed Finding |
| :--- | :--- | :--- |
| `FastAPI Application Core` | **WORKING** | Mounts cleanly, passes CORS, provides interactive `/docs` and `/health`. |
| `Document Pipeline` | **PARTIALLY WORKING** | PDF, DOCX, TXT extraction works, but backend routes lack a service layer, and Streamlit bypasses backend upload. |
| `Vision Pipeline` | **PARTIALLY WORKING** | Pillow analysis and swatches work, but `clean_session_buffers()` depends on Streamlit, and Streamlit bypasses backend. |
| `Data Pipeline` | **PARTIALLY WORKING** | Tabular profiling and Plotly generation work, but correlation logic is duplicated in the router, and Streamlit bypasses backend. |
| `LLM Router` | **PARTIALLY WORKING** | Routing cascade and fallbacks function, but tightly coupled to Streamlit session state and giant monolithic file. |
| `Streamlit Frontend` | **MISWIRED / BYPASSING** | Displays UI properly, but directly imports and runs core pipelines rather than acting as a decoupled client. |
| `Backend Client` | **WORKING** | `core/backend_client.py` implements required HTTP methods, but is partially bypassed by `main.py`. |
| `Backend Service Layer` | **PLACEHOLDER / MISSING** | `DocumentService`, `VisionService`, `DataService` do not exist. Only `N8nService` is present. |
| `n8n Webhook Receivers` | **WORKING** | Inbound webhook endpoint accepts and processes payloads. |
| `n8n Email & Slack Dispatch` | **MOCKED / SIMULATED** | Falls back to `"local_simulation"` strings; no verified live delivery. |
| `n8n Scheduled Jobs` | **MOCKED / IN-MEMORY** | Static dictionary without persistent scheduler or cron worker. |
| `n8n Workflow Blueprints` | **MISWIRED FOR DOCKER** | Valid JSON, but hardcodes `localhost:8000` instead of `backend:8000` and creates circular loops for Slack/Email. |
| `Docker Compose & Dockerfile` | **PRODUCTION-UNSAFE / BROKEN** | `ENTRYPOINT` conflict prevents backend from running; missing `.env` breaks startup. |
| `Git Repository State` | **PRODUCTION-UNSAFE** | Live secrets committed; bytecode and logs tracked in repository. |
| `Documentation (README.md)` | **MISLEADING** | Overstates production readiness and live integration status. |

---

## Architectural Scorecard

| Dimension | Score | Primary Deficit |
| :--- | :---: | :--- |
| **Security** | **2 / 10** | Live API keys committed to Git in `.streamlit/secrets.toml`; logs tracked. |
| **Architecture** | **5 / 10** | Dual execution paths; no clean service layer; circular n8n dispatch. |
| **Backend Separation** | **4 / 10** | Streamlit retains direct imports of all pipeline and router modules. |
| **LLM Architecture** | **6 / 10** | Robust fallback cascade, but router is monolithic and imports Streamlit. |
| **Data Pipeline** | **7 / 10** | Comprehensive statistical profiling, but correlation duplicated in route. |
| **Vision Pipeline** | **6 / 10** | Solid color quantization and EXIF handling; route accepts unvalidated payloads. |
| **Document Pipeline** | **6 / 10** | Multi-format ingestion works; lacks service abstraction. |
| **n8n Integration** | **3 / 10** | Simulated in-memory storage, mock fallbacks, circular workflow node definitions. |
| **Testing** | **4 / 10** | 11 tests pass, but 6 are superficial/simulated checks on fallback mocks. |
| **Docker** | **4 / 10** | Compose configuration fails due to Dockerfile `ENTRYPOINT` collision. |
| **Documentation** | **5 / 10** | Detailed, but premature claims of "production-grade" and "one-click". |
| **OVERALL SYSTEM SCORE** | **4.7 / 10** | **Structural foundation exists, but requires strict architectural separation, security remediation, and service layer creation.** |

---

## Summary of Findings & Next Steps

### 1. What is Genuinely Implemented
- The FastAPI application structure, routing tables, and OpenAPI contracts.
- Core pipeline logic for parsing documents (`pypdf`, `python-docx`), images (`Pillow`), and tabular data (`pandas`).
- The zero-cost fallback cascade in `core/llm_router.py` (Gemini → Groq → Ollama → Offline Heuristics).
- The Streamlit presentation UI with Terracotta & Sage aesthetic.
- The `BackendClient` HTTP wrapper class.
- The 3 n8n JSON workflow blueprint files with valid syntax.

### 2. What is Simulated
- **Slack Dispatch**: Returns mock confirmation strings when no external webhook is configured.
- **Email Dispatch**: Returns mock confirmation strings when no email webhook is configured.
- **Scheduled Jobs**: Uses a static in-memory dictionary; no real cron runner or persistent task queue.
- **Report Catalog**: In-memory dictionary that does not persist across restarts.
- **n8n Testing**: The test suite only tests in-memory Python calls, not communication with an actual n8n engine.

### 3. What is Duplicated
- Correlation calculations exist in both `pipelines/data_pipeline.py` and `backend/routers/data.py`.
- LLM Provider catalog definitions exist in both `core/config.py` and `backend/routers/router.py`.
- Ingestion and parsing logic can be executed either via FastAPI or directly inside Streamlit.

### 4. What is Incorrectly Wired
- Streamlit's `main.py` directly imports pipeline functions (`load_document`, `load_image`, `load_structured_data`) and executes them on upload rather than posting multipart files to FastAPI.
- `render_claude_artifact_workspace` takes a direct Python `router` instance rather than routing edits through the backend.
- n8n workflow blueprints call back to FastAPI for Slack and Email rather than letting n8n dispatch them natively.
- n8n workflow blueprints target `http://localhost:8000` which fails inside Docker network bridges.

### 5. What is Production Unsafe
- **Committed Plaintext Secrets**: `.streamlit/secrets.toml` is tracked in Git with live API keys.
- **Dockerfile Entrypoint Conflict**: Prevents the backend container from starting in Docker Compose.
- **Missing `.env`**: Docker Compose references `.env` without an existing file on disk.
- **Unbounded In-Memory State**: `GENERATED_REPORTS` and `SCHEDULED_JOBS` grow indefinitely in memory with zero persistence.
- **Coupling to Streamlit Context**: `core/llm_router.py` imports `streamlit`, generating warnings when run inside FastAPI worker processes.

### 6. Recommended Next Steps (Pending Approval)
1. **Security Remediation**: Untrack `.streamlit/secrets.toml`, remove tracked `.pyc` and `logs/` files from Git index, create `.env.example`, and rotate exposed keys.
2. **True Backend Decoupling**: Refactor `main.py` so that Streamlit exclusively makes HTTP calls via `BackendClient` for file uploads, summaries, OCR, and profiling, removing direct pipeline imports from the UI.
3. **Establish Service Layer**: Introduce `backend/services/document_service.py`, `vision_service.py`, and `data_service.py` so routers strictly validate requests and delegate orchestration.
4. **Decouple LLM Router from Streamlit**: Remove `import streamlit` from `core/llm_router.py` and ensure secrets/telemetry pass cleanly through standard Python environment variables and backend context.
5. **Fix Docker Compose & Dockerfile**: Separate `Dockerfile.frontend` and `Dockerfile.backend` (or use `entrypoint: []` in compose) to resolve container boot crashes.
6. **Correct n8n Boundary & Workflow Blueprints**: Update workflow JSONs to use native n8n dispatch nodes and resolve container hostnames (`http://backend:8000`).
7. **Expand Real Integration Tests**: Add integration tests with mocked external APIs that test real HTTP request/response payloads rather than relying on offline fallback paths.

### 7. What Should NOT Be Changed
- The core analytical pipelines (`pipelines/data_pipeline.py`, `document_pipeline.py`, `image_pipeline.py`) — their parsing, statistical calculations, and image analysis functions are functionally solid.
- The UI styling and visual design system (`core/styles.py`) — the aesthetic and layout are well crafted.
- The fundamental LLM provider cascade logic (Gemini → OpenAI → Groq → Offline Heuristics) — the multi-tier failover mechanism works as intended.
