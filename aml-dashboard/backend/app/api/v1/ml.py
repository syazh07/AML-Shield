from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.state import AppState
from app.models.schemas import CaseScoreResult, RiskScoreResult, TransactionFeatures

router = APIRouter(prefix="/ml", tags=["ml"])


def get_state(request: Request) -> AppState:
    return request.app.state.container


@router.get("/info")
def model_info(state: AppState = Depends(get_state)) -> dict:
    return {
        "model_version": state.ml.MODEL_VERSION,
        "model_type": state.ml.MODEL_TYPE,
        "description": "Plugged-in ml_pipeline hybrid: IOB noisy-OR rules + Isolation Forest, "
                       "fitted on the project's own sample transactions.",
        "is_placeholder": getattr(state.ml, "IS_PLACEHOLDER", True),
    }


@router.post("/score/transaction", response_model=RiskScoreResult)
async def score_transaction(
    features: TransactionFeatures,
    state: AppState = Depends(get_state),
) -> RiskScoreResult:
    return await state.ml.score_transaction(features)


@router.post("/score/case/{case_id}", response_model=CaseScoreResult)
async def score_case(case_id: str, state: AppState = Depends(get_state)) -> CaseScoreResult:
    try:
        return await state.cases.rescore_case(case_id)
    except KeyError as exc:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(f"Case {case_id} not found") from exc
