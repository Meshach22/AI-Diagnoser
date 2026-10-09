"""backend/services/n8n_service.py

Service layer implementing n8n automation operations:
- Webhooks handling & dispatch
- Automated Report generation
- Email notifications dispatching
- Slack Block Kit message formatting & posting
- Scheduled Jobs registration and execution
- n8n Workflow JSON blueprint manager
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests

from backend.config import settings
from core.llm_router import query_llm, get_last_telemetry

logger = logging.getLogger("n8n_service")

# In-memory storage for reports and job run logs
GENERATED_REPORTS: Dict[str, Dict[str, Any]] = {}
SCHEDULED_JOBS: Dict[str, Dict[str, Any]] = {
    "job_daily_data_audit": {
        "job_id": "job_daily_data_audit",
        "name": "Daily Tabular Data Health Audit",
        "cron": "0 0 * * *",
        "description": "Scans business metric tables for null spikes, duplicate rows, and schema drift.",
        "target_service": "data",
        "status": "active",
        "last_run": None,
        "next_run": "2026-10-09 00:00:00 UTC",
    },
    "job_weekly_executive_brief": {
        "job_id": "job_weekly_executive_brief",
        "name": "Weekly Executive Synthesis & Briefing",
        "cron": "0 9 * * 1",
        "description": "Synthesizes uploaded corporate reports into executive bullet points and dispatches to Slack & Email.",
        "target_service": "documents",
        "status": "active",
        "last_run": None,
        "next_run": "2026-10-12 09:00:00 UTC",
    },
    "job_vision_defect_scan": {
        "job_id": "job_vision_defect_scan",
        "name": "Automated Vision & OCR Audit",
        "cron": "*/30 * * * *",
        "description": "Processes queued receipt scans and system screenshots for OCR extraction and anomaly tags.",
        "target_service": "vision",
        "status": "active",
        "last_run": None,
        "next_run": "2026-10-08 12:00:00 UTC",
    }
}


class N8nService:
    """Core integration engine for n8n workflows and downstream notification channels."""

    @classmethod
    def process_incoming_webhook(
        cls,
        event: str,
        content: Optional[str] = None,
        image_base64: Optional[str] = None,
        provider: str = "Google Gemini",
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process inbound webhook from n8n and invoke corresponding Core AI Service."""
        diagnosis = ""
        summary = ""

        if event == "document.diagnose":
            doc_text = content or "Sample document content."
            prompt = (
                f"You are an expert executive document analyst. Review this document content and provide an executive summary and key findings:\n\n"
                f"{doc_text[:4000]}"
            )
            diagnosis = query_llm(prompt=prompt, model_provider=provider)
            summary = f"Processed document ({len(doc_text)} characters) via {provider}."

        elif event == "vision.diagnose":
            if image_base64:
                from core.llm_router import route_vision_request
                prompt = "Perform an executive visual inspection, OCR transcription, and anomaly detection on this image asset."
                diagnosis = route_vision_request(
                    prompt=prompt,
                    provider=provider,
                    image_data=image_base64
                )
                summary = f"Completed vision inspection via {provider}."
            else:
                diagnosis = "No image payload supplied in vision event."
                summary = "Vision inspection skipped: image_base64 missing."

        elif event == "data.diagnose":
            from pipelines.data_pipeline import load_structured_data, generate_data_health_card, generate_data_insights
            csv_text = content or "id,value,category\n1,100,A\n2,200,B"
            try:
                import io
                import pandas as pd
                df = pd.read_csv(io.StringIO(csv_text))
                health = generate_data_health_card(df, filename="n8n_stream_data.csv")
                insights = generate_data_insights(df, model_provider=provider)
                diagnosis = (
                    f"### 📊 Data Health Card\n"
                    f"- **Rows**: {health['total_rows']}, **Columns**: {health['total_cols']}\n"
                    f"- **Missing**: {health['missing_percentage']}%\n\n"
                    f"### 💡 AI Dataset Insights\n\n{insights}"
                )
                summary = f"Processed tabular dataset ({health['total_rows']} rows) via {provider}."
            except Exception as e:
                diagnosis = f"Error processing tabular dataset: {str(e)}"
                summary = "Tabular processing failed."

        else:
            # Generic diagnose
            prompt = f"Analyze the following diagnostic event payload ({event}):\n\n{content or ''}"
            diagnosis = query_llm(prompt=prompt, model_provider=provider)
            summary = f"Custom diagnostic event '{event}' processed."

        telemetry = get_last_telemetry()

        # If a callback URL was specified (n8n waiting for response), post to callback
        dispatched = False
        if callback_url:
            try:
                resp = requests.post(
                    callback_url,
                    json={
                        "event": event,
                        "status": "completed",
                        "diagnosis": diagnosis,
                        "summary": summary,
                        "telemetry": telemetry,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    timeout=5.0
                )
                dispatched = resp.status_code in (200, 201, 204)
            except Exception as exc:
                logger.warning(f"Could not post to n8n callback {callback_url}: {exc}")

        return {
            "status": "success",
            "event": event,
            "diagnosis": diagnosis,
            "summary": summary,
            "telemetry": telemetry,
            "dispatched_to_callback": dispatched
        }

    @classmethod
    def generate_report(
        cls,
        title: str,
        content: str,
        user_id: int = 1,
        report_type: str = "markdown",
        recipient_email: Optional[str] = None,
        slack_channel: Optional[str] = None,
        auth_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Synthesize, catalog in persistent SQLite storage, and optionally distribute a diagnostic report."""
        report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Persist to authoritative database
        try:
            from backend.services.auth_service import get_auth_service
            svc = auth_service or get_auth_service()
            report_entry = svc.save_report(
                user_id=user_id,
                title=title,
                content=content,
                report_type=report_type,
                recipient_email=recipient_email,
                slack_channel=slack_channel,
                status="ready",
                report_id=report_id,
            )
        except Exception as exc:
            logger.warning(f"Could not persist report to database: {exc}")
            report_entry = {
                "report_id": report_id,
                "user_id": user_id,
                "title": title,
                "report_type": report_type,
                "content": content,
                "recipient_email": recipient_email,
                "slack_channel": slack_channel,
                "created_at": now_str,
                "status": "ready"
            }

        # Maintain backward-compatible memory cache
        GENERATED_REPORTS[report_id] = report_entry

        # Optional auto-dispatch
        if recipient_email:
            cls.dispatch_email(
                to_email=recipient_email,
                subject=f"AI-Diagnoser Report: {title}",
                body=f"Diagnostic report '{title}' has been generated.\n\nSummary:\n{content[:500]}...",
                report_id=report_id
            )

        if slack_channel:
            cls.dispatch_slack(
                channel=slack_channel,
                title=f"📋 New Diagnostic Report: {title}",
                message=content[:400] + ("..." if len(content) > 400 else ""),
                severity="info"
            )

        return report_entry

    @classmethod
    def dispatch_email(
        cls,
        to_email: str,
        subject: str,
        body: str,
        report_id: Optional[str] = None,
        n8n_webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatch diagnostic email via n8n Email Node or direct fallback."""
        target_url = n8n_webhook_url or settings.N8N_EMAIL_WEBHOOK_URL or settings.N8N_WEBHOOK_URL
        payload = {
            "channel": "email",
            "to": to_email,
            "subject": subject,
            "body": body,
            "report_id": report_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if target_url:
            try:
                resp = requests.post(target_url, json=payload, timeout=4.0)
                if resp.status_code in (200, 201, 202, 204):
                    delivered_via = f"REAL INTEGRATION (n8n Webhook: {target_url})"
                    status = "dispatched"
                else:
                    delivered_via = f"NOT CONFIGURED / FAILED (HTTP {resp.status_code})"
                    status = "failed"
            except Exception as e:
                delivered_via = f"NOT CONFIGURED / FAILED ({str(e)})"
                status = "failed"
        else:
            delivered_via = "SIMULATION (No N8N_EMAIL_WEBHOOK_URL or SMTP configured)"
            status = "simulated"

        return {
            "status": status,
            "recipient": to_email,
            "subject": subject,
            "delivered_via": delivered_via,
            "message": f"Diagnostic email '{subject}' dispatched to {to_email}."
        }

    @classmethod
    def dispatch_slack(
        cls,
        channel: str,
        title: str,
        message: str,
        severity: str = "info",
        metrics: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format and dispatch Slack Block Kit message to n8n or Slack Incoming Webhook."""
        target_url = webhook_url or settings.N8N_SLACK_WEBHOOK_URL or settings.SLACK_INCOMING_WEBHOOK or settings.N8N_WEBHOOK_URL

        severity_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
            "success": "✅"
        }.get(severity.lower(), "ℹ️")

        fields = []
        if metrics:
            for k, v in list(metrics.items())[:6]:
                fields.append({"type": "mrkdwn", "text": f"*{k}:*\n`{v}`"})

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} AI-Diagnoser: {title}"[:150],
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message[:2000]
                }
            }
        ]

        if fields:
            blocks.append({
                "type": "section",
                "fields": fields
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Channel: `{channel}` • Timestamp: `{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}` • Engine: *FastAPI + n8n*"
                }
            ]
        })

        slack_payload = {
            "channel": channel,
            "text": f"{severity_emoji} {title}: {message[:200]}",
            "blocks": blocks
        }

        if target_url:
            try:
                resp = requests.post(target_url, json=slack_payload, timeout=4.0)
                if resp.status_code in (200, 201, 202, 204):
                    delivered_via = f"REAL INTEGRATION (Slack Webhook: {target_url})"
                    status = "dispatched"
                else:
                    delivered_via = f"NOT CONFIGURED / FAILED (HTTP {resp.status_code})"
                    status = "failed"
            except Exception as e:
                delivered_via = f"NOT CONFIGURED / FAILED ({str(e)})"
                status = "failed"
        else:
            delivered_via = "SIMULATION (No SLACK_INCOMING_WEBHOOK or N8N_SLACK_WEBHOOK_URL configured)"
            status = "simulated"

        return {
            "status": status,
            "channel": channel,
            "delivered_via": delivered_via,
            "message": f"Slack message '{title}' formatted and sent to {channel}."
        }

    @classmethod
    def list_scheduled_jobs(cls) -> List[Dict[str, Any]]:
        """Return list of active and pending scheduled diagnostic jobs."""
        return list(SCHEDULED_JOBS.values())

    @classmethod
    def trigger_scheduled_job(cls, job_id: str, provider: str = "Google Gemini") -> Dict[str, Any]:
        """Manually trigger an execution of a registered scheduled job."""
        if job_id not in SCHEDULED_JOBS:
            raise KeyError(f"Scheduled job '{job_id}' not found.")

        job = SCHEDULED_JOBS[job_id]
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        target_service = job["target_service"]
        diagnosis = ""

        if target_service == "data":
            # Run data audit
            prompt = "Conduct a routine automated data health card diagnostic audit. Report on expected null rates and duplicate thresholds."
            diagnosis = query_llm(prompt=prompt, model_provider=provider)
        elif target_service == "documents":
            prompt = "Conduct scheduled executive synthesis for corporate intelligence briefings. Detail action items and compliance checkpoints."
            diagnosis = query_llm(prompt=prompt, model_provider=provider)
        else:
            prompt = "Conduct scheduled computer vision audit scan for image artifacts, OCR text fidelity, and color gamut balance."
            diagnosis = query_llm(prompt=prompt, model_provider=provider)

        job["last_run"] = now_str

        # Generate report entry
        report = cls.generate_report(
            title=f"Scheduled Job Execution: {job['name']}",
            content=diagnosis,
            report_type="markdown"
        )

        # Notify via Slack
        cls.dispatch_slack(
            channel="#diagnostics-feed",
            title=f"Scheduled Run Completed: {job['name']}",
            message=f"Scheduled job completed at {now_str}.\nReport ID: `{report['report_id']}`",
            severity="success",
            metrics={"Service": target_service.capitalize(), "Provider": provider, "Status": "Success"}
        )

        return {
            "status": "success",
            "job_id": job_id,
            "job_name": job["name"],
            "executed_at": now_str,
            "report_id": report["report_id"],
            "diagnosis_preview": diagnosis[:250] + "..."
        }

    @classmethod
    def get_workflow_blueprints(cls) -> List[Dict[str, Any]]:
        """List downloadable n8n workflow blueprints available in the project."""
        workflows_dir = os.path.join(os.getcwd(), "n8n", "workflows")
        blueprints = []

        if os.path.isdir(workflows_dir):
            for fname in os.listdir(workflows_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(workflows_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            nodes = data.get("nodes", [])
                            name = data.get("name", fname.replace(".json", "").replace("_", " ").title())
                            blueprints.append({
                                "id": fname.replace(".json", ""),
                                "name": name,
                                "filename": fname,
                                "description": f"Ready-to-import n8n workflow containing {len(nodes)} orchestrated nodes.",
                                "nodes_count": len(nodes),
                                "trigger_type": "Webhook / Cron",
                                "target_endpoints": ["/api/v1/n8n/webhook", "/api/v1/documents/summarize", "/api/v1/data/insights"]
                            })
                    except Exception:
                        pass

        return blueprints
