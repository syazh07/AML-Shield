from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.exceptions import NotFoundError
from app.core.state import AppState
from app.data import seed
from app.models.schemas import (
    AccountProfile,
    AuditEntry,
    BilingualSummary,
    CaseDetail,
    CaseSummary,
    ClaimCaseRequest,
    CloseCaseRequest,
    ConfidenceUpdate,
    EscalateRequest,
    GraphPayload,
    HandoffRequest,
    Note,
    NoteCreate,
    RiskSignal,
    TimelineEvent,
)

router = APIRouter(prefix="/cases", tags=["cases"])


def get_state(request: Request) -> AppState:
    return request.app.state.container


@router.get("", response_model=list[CaseSummary])
def list_cases(
    flag: str | None = None,
    status: str | None = None,
    score_min: int = 0,
    score_max: int = 100,
    search: str | None = None,
    state: AppState = Depends(get_state),
) -> list[CaseSummary]:
    return state.cases.list_cases(
        flag=flag,
        status=status,
        score_min=score_min,
        score_max=score_max,
        search=search,
    )


@router.post("", response_model=CaseDetail, status_code=201)
def create_case(body: CaseSummary, state: AppState = Depends(get_state)) -> CaseDetail:
    """Ingest a new case — the endpoint the Transaction Monitoring Engine (and the
    demo seeder) posts alerts to. Auto-emits a 'new case' notification."""
    try:
        return state.cases.add_case(body.model_dump(by_alias=True, mode="json"))
    except ValueError as exc:
        from app.core.exceptions import BadRequestError

        raise BadRequestError(str(exc)) from exc


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, state: AppState = Depends(get_state)) -> CaseDetail:
    try:
        return state.cases.get_case(case_id)
    except KeyError as exc:
        raise NotFoundError(f"Case {case_id} not found") from exc


@router.post("/{case_id}/claim", response_model=CaseDetail)
def claim_case(
    case_id: str,
    body: ClaimCaseRequest,
    state: AppState = Depends(get_state),
) -> CaseDetail:
    try:
        return state.cases.claim(case_id, body.analyst_name)
    except KeyError as exc:
        raise NotFoundError(f"Case {case_id} not found") from exc
    except ValueError as exc:
        from app.core.exceptions import BadRequestError

        raise BadRequestError(str(exc)) from exc


@router.post("/{case_id}/close", response_model=CaseDetail)
def close_case(
    case_id: str,
    body: CloseCaseRequest,
    actor: str = "Priya Venkatesh",
    state: AppState = Depends(get_state),
) -> CaseDetail:
    try:
        return state.cases.close(case_id, body.reason, actor)
    except KeyError as exc:
        raise NotFoundError(f"Case {case_id} not found") from exc


@router.post("/{case_id}/handoff", response_model=CaseDetail)
def handoff_case(
    case_id: str,
    body: HandoffRequest,
    actor: str = "Priya Venkatesh",
    state: AppState = Depends(get_state),
) -> CaseDetail:
    try:
        return state.cases.handoff(case_id, body.recipient_handle, body.note, actor)
    except KeyError as exc:
        raise NotFoundError(f"Case {case_id} not found") from exc


@router.post("/{case_id}/escalate", response_model=CaseDetail)
def escalate_case(
    case_id: str,
    body: EscalateRequest,
    actor: str = "Priya Venkatesh",
    state: AppState = Depends(get_state),
) -> CaseDetail:
    try:
        return state.cases.escalate(case_id, body.officer_id, body.note, body.priority, actor)
    except KeyError as exc:
        raise NotFoundError(f"Case {case_id} not found") from exc


@router.patch("/{case_id}/confidence")
def update_confidence(
    case_id: str,
    body: ConfidenceUpdate,
    state: AppState = Depends(get_state),
) -> dict:
    state.cases.update_confidence(case_id, body.confidence)
    return {"confidence": body.confidence}


def _bundle(case_id: str, state: AppState) -> dict:
    try:
        return state.cases.get_investigation(case_id)
    except KeyError as exc:
        raise NotFoundError(f"Case {case_id} not found") from exc


@router.get("/{case_id}/investigation")
def get_investigation(case_id: str, state: AppState = Depends(get_state)) -> dict:
    """Full per-case investigation bundle in one call — profile, timeline, graph,
    risk signals, IOB pattern, bilingual summary, notes, audit, confidence,
    STR status. This is what the workstation loads when a case is opened."""
    bundle = _bundle(case_id, state)
    return {
        **bundle,
        "notes": state.cases.list_notes(case_id),
        "audit": [e.model_dump() for e in state.audit.list_for_case(case_id)],
        "confidence": state.cases.get_confidence(case_id),
        "str_status": state.cases.get_str_status(case_id),
    }


@router.get("/{case_id}/account-profile", response_model=AccountProfile)
def get_account_profile(case_id: str, state: AppState = Depends(get_state)) -> AccountProfile:
    return AccountProfile(**_bundle(case_id, state)["account_profile"])


@router.get("/{case_id}/timeline", response_model=list[TimelineEvent])
def get_timeline(case_id: str, state: AppState = Depends(get_state)) -> list[TimelineEvent]:
    return [TimelineEvent(**e) for e in _bundle(case_id, state)["timeline"]]


@router.get("/{case_id}/graph", response_model=GraphPayload)
def get_graph(case_id: str, state: AppState = Depends(get_state)) -> GraphPayload:
    return GraphPayload(**_bundle(case_id, state)["graph"])


@router.get("/{case_id}/risk-signals", response_model=list[RiskSignal])
def get_risk_signals(case_id: str, state: AppState = Depends(get_state)) -> list[RiskSignal]:
    return [RiskSignal(**s) for s in _bundle(case_id, state)["risk_signals"]]


@router.get("/{case_id}/summary", response_model=BilingualSummary)
def get_summary(case_id: str, state: AppState = Depends(get_state)) -> BilingualSummary:
    return BilingualSummary(**_bundle(case_id, state)["summary"])


@router.get("/{case_id}/notes", response_model=list[Note])
def list_notes(case_id: str, state: AppState = Depends(get_state)) -> list[Note]:
    return [Note(**note) for note in state.cases.list_notes(case_id)]


@router.post("/{case_id}/notes", response_model=Note)
def add_note(case_id: str, body: NoteCreate, state: AppState = Depends(get_state)) -> Note:
    note = state.cases.add_note(case_id, body.body, body.mentions)
    return Note(**note)


@router.get("/{case_id}/audit", response_model=list[AuditEntry])
def get_audit(case_id: str, state: AppState = Depends(get_state)) -> list[AuditEntry]:
    return state.audit.list_for_case(case_id)
