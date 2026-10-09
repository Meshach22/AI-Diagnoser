"""backend/schemas/n8n.py

Schemas for n8n Automation Engine endpoints:
- Inbound Webhooks
- Outbound Reports
- Email Dispatch
- Slack Alerts
- Scheduled Jobs
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# 1. Inbound Webhooks
class N8nWebhookPayload(BaseModel):
    """Payload received from an n8n webhook node."""
    event: str = Field(..., description="Event type: 'document.diagnose', 'vision.diagnose', 'data.diagnose', or 'batch.audit'")
    source: Optional[str] = Field(default="n8n-workflow", description="Originating workflow or system")
    content: Optional[str] = Field(default=None, description="Raw text, CSV string, or document content")
    image_base64: Optional[str] = Field(default=None, description="Base64 image data if vision event")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata / headers")
    callback_url: Optional[str] = Field(default=None, description="Optional n8n webhook URL to post results back to")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider: Google Gemini, OpenAI, Groq")


class DocumentWebhookPayload(BaseModel):
    """Direct inbound document diagnosis webhook payload."""
    content: str = Field(..., description="Document content text")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider")
    callback_url: Optional[str] = Field(default=None, description="Optional callback URL")


class VisionWebhookPayload(BaseModel):
    """Direct inbound vision diagnosis webhook payload with base64 in POST body."""
    image_base64: str = Field(..., description="Base64-encoded image payload in POST JSON body")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider")
    callback_url: Optional[str] = Field(default=None, description="Optional callback URL")


class DataWebhookPayload(BaseModel):
    """Direct inbound tabular data diagnosis webhook payload."""
    csv_content: str = Field(..., description="Raw CSV text content")
    provider: Optional[str] = Field(default="Google Gemini", description="LLM provider")
    callback_url: Optional[str] = Field(default=None, description="Optional callback URL")


class N8nWebhookResponse(BaseModel):
    """Response returned to n8n webhook caller."""
    status: str = "success"
    event: str
    diagnosis: str
    summary: Optional[str] = None
    telemetry: Optional[Dict[str, Any]] = None
    dispatched_to_callback: bool = False


# 2. Reports
class ReportGenerationRequest(BaseModel):
    """Request to synthesize and format a diagnostic report."""
    title: str = Field(..., description="Report title")
    content: str = Field(..., description="Diagnostic markdown or structured findings")
    report_type: str = Field(default="markdown", description="'markdown', 'pdf', 'docx', or 'json'")
    recipient_email: Optional[str] = Field(default=None, description="Optional recipient to auto-dispatch")
    slack_channel: Optional[str] = Field(default=None, description="Optional Slack channel to alert")


class ReportGenerationResponse(BaseModel):
    """Response containing formatted report metadata."""
    report_id: str
    title: str
    report_type: str
    content: str
    created_at: str
    status: str


# 3. Email Dispatch
class EmailDispatchRequest(BaseModel):
    """Request to dispatch a diagnostic summary or report via Email."""
    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Subject line")
    body: str = Field(..., description="Email body (text or markdown)")
    report_id: Optional[str] = Field(default=None, description="Optional attached report ID")
    n8n_webhook_url: Optional[str] = Field(default=None, description="Optional custom n8n Email Webhook URL override")


class EmailDispatchResponse(BaseModel):
    """Response for email dispatch."""
    status: str
    recipient: str
    subject: str
    delivered_via: str  # e.g., 'n8n_email_node' or 'direct_smtp_mock'
    message: str


# 4. Slack Dispatch
class SlackDispatchRequest(BaseModel):
    """Request to dispatch a diagnostic card or alert to Slack."""
    channel: Optional[str] = Field(default="#general", description="Slack channel name")
    title: str = Field(..., description="Card / Alert Title")
    message: str = Field(..., description="Alert details or findings")
    severity: str = Field(default="info", description="'info', 'warning', 'critical', or 'success'")
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Key/value metrics to show in Slack block kit")
    webhook_url: Optional[str] = Field(default=None, description="Custom Slack or n8n webhook URL override")


class SlackDispatchResponse(BaseModel):
    """Response for Slack dispatch."""
    status: str
    channel: str
    delivered_via: str
    message: str


# 5. Scheduled Jobs
class ScheduledJobInfo(BaseModel):
    """Information about a scheduled diagnostic job."""
    job_id: str
    name: str
    cron: str
    description: str
    target_service: str  # 'documents', 'vision', 'data'
    status: str  # 'active', 'paused', 'idle'
    last_run: Optional[str] = None
    next_run: Optional[str] = None


class ScheduledJobTriggerRequest(BaseModel):
    """Trigger an on-demand run of a scheduled job."""
    job_id: str
    provider: Optional[str] = Field(default="Google Gemini")


# 6. Workflow Blueprints
class WorkflowBlueprintInfo(BaseModel):
    """Metadata for an exportable n8n workflow JSON file."""
    id: str
    name: str
    filename: str
    description: str
    nodes_count: int
    trigger_type: str
    target_endpoints: List[str]
