"""backend/routers/n8n.py

n8n Automation Engine Router (/api/v1/n8n)
Exposes endpoints for the n8n automation ecosystem:
- Inbound Webhooks
- Report Generation & Cataloging
- Email Dispatch
- Slack Alerts
- Scheduled Jobs Registration & Triggering
- Downloadable n8n Workflow Blueprints
"""

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse

from backend.routers.auth import get_current_session, require_admin
from backend.schemas.n8n import (
    DataWebhookPayload,
    DocumentWebhookPayload,
    EmailDispatchRequest,
    EmailDispatchResponse,
    N8nWebhookPayload,
    N8nWebhookResponse,
    ReportGenerationRequest,
    ReportGenerationResponse,
    ScheduledJobInfo,
    ScheduledJobTriggerRequest,
    SlackDispatchRequest,
    SlackDispatchResponse,
    VisionWebhookPayload,
    WorkflowBlueprintInfo,
)
from backend.services.auth_service import AuthService, SessionInfo, get_auth_service
from backend.services.n8n_service import GENERATED_REPORTS, N8nService

router = APIRouter(prefix="/api/v1/n8n", tags=["n8n Automation Engine"])


# ---------------------------------------------------------------------------
# 1. Inbound Webhooks
# ---------------------------------------------------------------------------
@router.post("/webhook", response_model=N8nWebhookResponse, summary="Universal n8n webhook receiver")
async def receive_n8n_webhook(
    payload: N8nWebhookPayload,
    session: SessionInfo = Depends(get_current_session),
):
    """Universal webhook endpoint for n8n workflows.
    Accepts document, vision, or tabular events, invokes Core AI Services,
    and optionally responds to a callback URL. Requires authenticated session or webhook secret.
    """
    try:
        res = N8nService.process_incoming_webhook(
            event=payload.event,
            content=payload.content,
            image_base64=payload.image_base64,
            provider=payload.provider or "Google Gemini",
            callback_url=payload.callback_url,
            metadata=payload.metadata
        )
        return N8nWebhookResponse(**res)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook execution failure: {str(exc)}"
        )


@router.post("/webhook/document", response_model=N8nWebhookResponse, summary="Inbound Document diagnosis webhook")
async def receive_document_webhook(
    payload: DocumentWebhookPayload,
    session: SessionInfo = Depends(get_current_session),
):
    """Direct document webhook endpoint for n8n document triggers."""
    res = N8nService.process_incoming_webhook(
        event="document.diagnose",
        content=payload.content,
        provider=payload.provider or "Google Gemini",
        callback_url=payload.callback_url
    )
    return N8nWebhookResponse(**res)


@router.post("/webhook/vision", response_model=N8nWebhookResponse, summary="Inbound Vision diagnosis webhook")
async def receive_vision_webhook(
    payload: VisionWebhookPayload,
    session: SessionInfo = Depends(get_current_session),
):
    """Direct vision webhook endpoint for n8n image/OCR triggers with base64 in POST body."""
    res = N8nService.process_incoming_webhook(
        event="vision.diagnose",
        image_base64=payload.image_base64,
        provider=payload.provider or "Google Gemini",
        callback_url=payload.callback_url
    )
    return N8nWebhookResponse(**res)


@router.post("/webhook/data", response_model=N8nWebhookResponse, summary="Inbound Data diagnosis webhook")
async def receive_data_webhook(
    payload: DataWebhookPayload,
    session: SessionInfo = Depends(get_current_session),
):
    """Direct tabular data webhook endpoint for n8n CSV/Excel triggers."""
    res = N8nService.process_incoming_webhook(
        event="data.diagnose",
        content=payload.csv_content,
        provider=payload.provider or "Google Gemini",
        callback_url=payload.callback_url
    )
    return N8nWebhookResponse(**res)


# ---------------------------------------------------------------------------
# 2. Diagnostic Reports
# ---------------------------------------------------------------------------
@router.post("/reports/generate", response_model=ReportGenerationResponse, summary="Generate and catalog diagnostic report")
async def generate_diagnostic_report(
    req: ReportGenerationRequest,
    session: SessionInfo = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Synthesizes, catalogs, and associates a diagnostic report with the authenticated owner."""
    try:
        report = N8nService.generate_report(
            title=req.title,
            content=req.content,
            user_id=session.user_id,
            report_type=req.report_type,
            recipient_email=req.recipient_email,
            slack_channel=req.slack_channel,
            auth_service=auth_service,
        )
        return ReportGenerationResponse(**report)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation error: {str(exc)}"
        )


@router.get("/reports", summary="List cataloged reports for current user")
async def list_user_reports(
    session: SessionInfo = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Lists diagnostic reports belonging to the authenticated user."""
    return auth_service.list_reports(
        user_id=session.user_id,
        is_admin=session.is_admin or session.role == "admin",
    )


@router.get("/reports/{report_id}", summary="Retrieve a cataloged report")
async def get_report(
    report_id: str,
    session: SessionInfo = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Retrieves a previously generated diagnostic report by ID with strict ownership isolation."""
    report = auth_service.get_report(
        report_id=report_id,
        user_id=session.user_id,
        is_admin=session.is_admin or session.role == "admin",
    )
    if not report:
        # Non-disclosing 404 whether missing or belonging to another user
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/reports/{report_id}", summary="Delete a cataloged report")
async def delete_report(
    report_id: str,
    session: SessionInfo = Depends(get_current_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Deletes a report by ID with ownership enforcement."""
    deleted = auth_service.delete_report(
        report_id=report_id,
        user_id=session.user_id,
        is_admin=session.is_admin or session.role == "admin",
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "success", "message": "Report deleted successfully."}


# ---------------------------------------------------------------------------
# 3. Email Dispatch
# ---------------------------------------------------------------------------
@router.post("/dispatch/email", response_model=EmailDispatchResponse, summary="Dispatch diagnostic email")
async def dispatch_email(
    req: EmailDispatchRequest,
    session: SessionInfo = Depends(get_current_session),
):
    """Dispatches diagnostic notifications or reports via n8n Email Node or direct SMTP."""
    try:
        res = N8nService.dispatch_email(
            to_email=req.to_email,
            subject=req.subject,
            body=req.body,
            report_id=req.report_id,
            n8n_webhook_url=req.n8n_webhook_url
        )
        return EmailDispatchResponse(**res)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email dispatch error: {str(exc)}"
        )


# ---------------------------------------------------------------------------
# 4. Slack Alerts
# ---------------------------------------------------------------------------
@router.post("/dispatch/slack", response_model=SlackDispatchResponse, summary="Dispatch Slack Block Kit alert")
async def dispatch_slack(
    req: SlackDispatchRequest,
    session: SessionInfo = Depends(get_current_session),
):
    """Formats and dispatches Slack Block Kit message to n8n or Slack Incoming Webhook."""
    try:
        res = N8nService.dispatch_slack(
            channel=req.channel or "#general",
            title=req.title,
            message=req.message,
            severity=req.severity,
            metrics=req.metrics,
            webhook_url=req.webhook_url
        )
        return SlackDispatchResponse(**res)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack dispatch error: {str(exc)}"
        )


# ---------------------------------------------------------------------------
# 5. Scheduled Jobs
# ---------------------------------------------------------------------------
@router.get("/schedules", response_model=List[ScheduledJobInfo], summary="List scheduled diagnostic jobs")
async def list_scheduled_jobs(session: SessionInfo = Depends(get_current_session)):
    """Returns all registered scheduled cron jobs for data, document, and vision audits."""
    jobs = N8nService.list_scheduled_jobs()
    return [ScheduledJobInfo(**j) for j in jobs]


@router.post("/schedules/trigger", summary="Trigger a scheduled job on-demand")
async def trigger_scheduled_job(
    req: ScheduledJobTriggerRequest,
    session: SessionInfo = Depends(require_admin),
):
    """Triggers an immediate execution of a scheduled audit job (Admin role required)."""
    try:
        res = N8nService.trigger_scheduled_job(
            job_id=req.job_id,
            provider=req.provider or "Google Gemini"
        )
        return res
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scheduled job execution error: {str(exc)}"
        )


# ---------------------------------------------------------------------------
# 6. Workflow Blueprints
# ---------------------------------------------------------------------------
@router.get("/workflows", response_model=List[WorkflowBlueprintInfo], summary="List downloadable n8n workflow blueprints")
async def list_workflows(session: SessionInfo = Depends(get_current_session)):
    """Lists ready-to-import n8n workflow templates available in the project."""
    blueprints = N8nService.get_workflow_blueprints()
    return [WorkflowBlueprintInfo(**b) for b in blueprints]


@router.get("/workflows/{filename}", summary="Download n8n workflow JSON blueprint")
async def download_workflow_file(
    filename: str,
    session: SessionInfo = Depends(get_current_session),
):
    """Downloads the raw n8n workflow JSON file for direct import into an n8n instance."""
    safe_name = os.path.basename(filename)
    fpath = os.path.join(os.getcwd(), "n8n", "workflows", safe_name)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="Workflow template not found.")
    return FileResponse(
        path=fpath,
        media_type="application/json",
        filename=safe_name
    )
