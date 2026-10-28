"""Pydantic schemas aligned with frontend domain types in src/data/constants.js."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    UNCLAIMED = "unclaimed"
    IN_PROGRESS = "in-progress"
    REVIEW = "review"
    READY = "ready"
    CLOSED = "closed"


class StrStatus(str, Enum):
    NONE = "none"
    DRAFTING = "drafting"
    REVIEW = "review"
    FILED = "filed"


class GraphHighlight(BaseModel):
    type: Literal["node", "edge"]
    id: str | None = None
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None

    model_config = {"populate_by_name": True}


class CaseSummary(BaseModel):
    id: str
    account: str
    type: str
    score: int
    flag: str
    status: CaseStatus
    claimed_by: str | None = Field(default=None, alias="claimedBy")
    opened_min: int = Field(alias="openedMin")
    str_deadline_hrs: float | None = Field(default=None, alias="strDeadlineHrs")
    urgent: bool | None = None
    closed_reason: str | None = Field(default=None, alias="closedReason")

    model_config = {"populate_by_name": True}


class CaseDetail(CaseSummary):
    str_status: StrStatus = StrStatus.NONE


class ClaimCaseRequest(BaseModel):
    analyst_name: str = "Priya Venkatesh"


class HandoffRequest(BaseModel):
    recipient_handle: str
    note: str


class CloseCaseRequest(BaseModel):
    reason: str


class EscalateRequest(BaseModel):
    officer_id: str
    note: str
    priority: Literal["normal", "urgent", "critical"] = "normal"


class ConfidenceUpdate(BaseModel):
    confidence: int = Field(ge=0, le=100)


class NoteCreate(BaseModel):
    body: str
    mentions: list[str] = Field(default_factory=list)


class Note(BaseModel):
    id: int
    kind: Literal["user", "system"]
    author: str
    role: str
    time: str
    body: str
    mentions: list[str] = Field(default_factory=list)


class AccountProfile(BaseModel):
    account: str
    type: str
    opened: str
    dormant: str
    branch: str
    kyc: str
    mobile: str
    pan: str
    balance_before: str = Field(alias="balanceBefore")
    balance_peak: str = Field(alias="balancePeak")
    balance_current: str = Field(alias="balanceCurrent")

    model_config = {"populate_by_name": True}


class TimelineEvent(BaseModel):
    t: str
    dir: Literal["credit", "debit"]
    amt: int
    party: str
    channel: str
    flag: str


class GraphNode(BaseModel):
    id: str
    label: str
    role: str
    color: str
    size: int
    balance: str
    type: str
    note: str


class GraphLink(BaseModel):
    source: str
    target: str
    amt: int
    t: str
    channel: str


class GraphPayload(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class EvidenceRow(BaseModel):
    k: str
    v: str
    emp: bool | None = None
    link: str | None = None


class ModelMetadata(BaseModel):
    weight: str
    precision: str
    trained: str


class RiskSignal(BaseModel):
    id: str
    title: str
    pts: int
    desc: str
    highlight: GraphHighlight
    rule: str
    formula: str
    evidence: list[EvidenceRow]
    model: ModelMetadata
    trace: str


class BilingualSummary(BaseModel):
    en: str
    ta: str


class AuditEntry(BaseModel):
    ts: str
    actor: str
    action: str
    hash: str


class NotificationItem(BaseModel):
    id: int
    type: str
    color: str
    icon: str
    title: str
    time: str
    msg: str
    action: str
    case_id: str | None = Field(default=None, alias="caseId")
    read: bool = False

    model_config = {"populate_by_name": True}


class StrEvidenceChip(BaseModel):
    id: str
    label: str
    cls: str
    checked: bool = True


class StrCiteSegment(BaseModel):
    text: str
    highlight: GraphHighlight
    chip_id: str = Field(alias="chipId")

    model_config = {"populate_by_name": True}


class StrEntity(BaseModel):
    account: str
    type: str
    role: str
    amount: str
    note: str


class ComplianceItem(BaseModel):
    label: str
    status: Literal["ok", "warn", "fail"]
    icon: str
    note: str | None = None


class StrDraft(BaseModel):
    case_id: str
    status: StrStatus
    narrative: str
    cite_segments: list[StrCiteSegment] = Field(default_factory=list, alias="citeSegments")
    evidence_chips: list[StrEvidenceChip] = Field(default_factory=list, alias="evidenceChips")
    entities: list[StrEntity] = Field(default_factory=list)
    compliance_items: list[ComplianceItem] = Field(default_factory=list, alias="complianceItems")
    analyst_confidence: int | None = Field(default=None, alias="analystConfidence")
    fiu_reference: str | None = Field(default=None, alias="fiuReference")
    updated_at: datetime | None = None

    model_config = {"populate_by_name": True}


class StrGenerateRequest(BaseModel):
    analyst_confidence: int = Field(default=87, ge=0, le=100, alias="analystConfidence")
    linked_case_ids: list[str] = Field(default_factory=list, alias="linkedCaseIds")

    model_config = {"populate_by_name": True}


class StrGenerationStep(BaseModel):
    index: int
    label: str
    status: Literal["pending", "running", "done"]


class StrGenerationJob(BaseModel):
    job_id: str
    case_id: str
    status: Literal["queued", "running", "completed", "failed"]
    steps: list[StrGenerationStep]
    draft: StrDraft | None = None
    error: str | None = None


class StrUpdateRequest(BaseModel):
    narrative: str | None = None
    evidence_chips: list[StrEvidenceChip] | None = Field(default=None, alias="evidenceChips")
    entities: list[StrEntity] | None = None

    model_config = {"populate_by_name": True}


class StrFileResponse(BaseModel):
    status: StrStatus
    fiu_reference: str = Field(alias="fiuReference")

    model_config = {"populate_by_name": True}


# --- ML (generic) ---


class TransactionFeatures(BaseModel):
    account_id: str
    amount: float
    channel: str
    direction: Literal["credit", "debit"]
    counterparty_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SignalContribution(BaseModel):
    rule: str
    points: int
    weight: float
    description: str


class RiskScoreResult(BaseModel):
    score: int = Field(ge=0, le=100)
    model_version: str
    model_type: str = "generic_stub"
    signals: list[SignalContribution]
    explanation: str
    is_placeholder: bool = True


class CaseScoreResult(RiskScoreResult):
    case_id: str
    flag: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    openai_configured: bool
    ml_model: str
