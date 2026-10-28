from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.state import AppState

router = APIRouter(prefix="/cases/{case_id}/copilot", tags=["copilot"])


class CopilotQuery(BaseModel):
    question: str


class CopilotAnswer(BaseModel):
    answer: str


class ChatMessage(BaseModel):
    role: str
    body: str
    time: str


def get_state(request: Request) -> AppState:
    return request.app.state.container


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


@router.get("/history", response_model=list[ChatMessage])
def get_history(case_id: str, state: AppState = Depends(get_state)) -> list[ChatMessage]:
    return [ChatMessage(**m) for m in state.store.chat_for_case(case_id)]


@router.post("", response_model=CopilotAnswer)
async def ask_copilot(
    case_id: str,
    body: CopilotQuery,
    state: AppState = Depends(get_state),
) -> CopilotAnswer:
    if not state.copilot.available:
        raise HTTPException(
            status_code=503,
            detail="AML Copilot unavailable — set OPENAI_API_KEY in backend/.env",
        )
    # persist the investigator's turn first so a failed answer still records the question
    state.store.append_chat(case_id, {"role": "user", "body": body.question, "time": _now()})
    answer = await state.copilot.answer(case_id, body.question)
    state.store.append_chat(case_id, {"role": "assistant", "body": answer, "time": _now()})
    return CopilotAnswer(answer=answer)


@router.post("/stream")
async def stream_copilot(
    case_id: str,
    body: CopilotQuery,
    state: AppState = Depends(get_state),
) -> StreamingResponse:
    if not state.copilot.available:
        raise HTTPException(
            status_code=503,
            detail="AML Copilot unavailable — set OPENAI_API_KEY in backend/.env",
        )
    state.store.append_chat(case_id, {"role": "user", "body": body.question, "time": _now()})

    async def token_stream():
        parts: list[str] = []
        try:
            async for delta in state.copilot.stream(case_id, body.question):
                parts.append(delta)
                yield delta
        finally:
            # persist whatever was produced, even if the client disconnects mid-stream
            answer = "".join(parts).strip()
            if answer:
                state.store.append_chat(case_id, {"role": "assistant", "body": answer, "time": _now()})

    return StreamingResponse(
        token_stream(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
