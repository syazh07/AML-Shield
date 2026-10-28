from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request

from app.core.exceptions import NotFoundError
from app.core.state import AppState
from app.models.schemas import (
    StrDraft,
    StrFileResponse,
    StrGenerateRequest,
    StrGenerationJob,
    StrStatus,
    StrUpdateRequest,
)

router = APIRouter(prefix="/cases/{case_id}/str", tags=["str"])


def get_state(request: Request) -> AppState:
    return request.app.state.container


@router.get("", response_model=Optional[StrDraft])
def get_str_draft(case_id: str, state: AppState = Depends(get_state)) -> StrDraft | None:
    return state.str_service.get_draft(case_id)


@router.post("/generate", response_model=StrGenerationJob)
async def generate_str(
    case_id: str,
    body: StrGenerateRequest,
    state: AppState = Depends(get_state),
) -> StrGenerationJob:
    try:
        state.cases.get_case(case_id)
    except KeyError as exc:
        raise NotFoundError(f"Case {case_id} not found") from exc

    return await state.str_service.start_generation(
        case_id,
        analyst_confidence=body.analyst_confidence,
        linked_case_ids=body.linked_case_ids,
    )


@router.get("/generate/{job_id}", response_model=StrGenerationJob)
def get_generation_job(job_id: str, state: AppState = Depends(get_state)) -> StrGenerationJob:
    job = state.str_service.get_job(job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found")
    return job


@router.put("", response_model=StrDraft)
def update_str_draft(
    case_id: str,
    body: StrUpdateRequest,
    state: AppState = Depends(get_state),
) -> StrDraft:
    try:
        return state.str_service.update_draft(
            case_id,
            narrative=body.narrative,
            evidence_chips=body.evidence_chips,
            entities=body.entities,
        )
    except KeyError as exc:
        raise NotFoundError(str(exc)) from exc


@router.post("/submit-review", response_model=StrDraft)
def submit_for_review(case_id: str, state: AppState = Depends(get_state)) -> StrDraft:
    try:
        return state.str_service.submit_review(case_id)
    except KeyError as exc:
        raise NotFoundError(str(exc)) from exc


@router.post("/file", response_model=StrFileResponse)
def file_str(case_id: str, state: AppState = Depends(get_state)) -> StrFileResponse:
    try:
        draft = state.str_service.file_str(case_id)
        return StrFileResponse(status=draft.status, fiuReference=draft.fiu_reference or "")
    except KeyError as exc:
        raise NotFoundError(str(exc)) from exc
