from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.config import settings
from app.services.case_service import CaseService

SYSTEM_PROMPT = (
    "You are AML Copilot, a case-grounded assistant for an anti-money-laundering "
    "investigator at Indian Overseas Bank. Answer the investigator's question using "
    "ONLY the case evidence JSON provided. Be concise and specific — cite exact "
    "accounts, amounts, timestamps, and rule names from the evidence. If the answer "
    "is not supported by the evidence, say so plainly. Plain text only, no markdown."
)


class CopilotService:
    """Case-grounded investigation copilot backed by OpenAI (no fallback).

    The key stays server-side (backend/.env → OPENAI_API_KEY). If it is missing the
    endpoint returns 503 rather than degrading to canned answers.
    """

    def __init__(self, cases: CaseService) -> None:
        self._cases = cases
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _context(self, case_id: str) -> dict:
        """Ground the copilot on THIS case's own investigation bundle (not the
        primary showcase). Mirrors how STRGenerationService builds its context."""
        case = self._cases.get_case(case_id)
        bundle = self._cases.get_investigation(case_id)
        return {
            "case": case.model_dump(mode="json"),
            "account_profile": bundle["account_profile"],
            "timeline": bundle["timeline"],
            "graph": bundle["graph"],
            "risk_signals": [
                {"id": s["id"], "title": s["title"], "points": s["pts"],
                 "rule": s["rule"], "detail": s["desc"]}
                for s in bundle["risk_signals"]
            ],
            "iob_pattern": bundle.get("iob_pattern"),
            "summary": bundle["summary"]["en"],
        }

    async def answer(self, case_id: str, question: str) -> str:
        context = self._context(case_id)
        resp = await self._client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Case evidence JSON:\n{json.dumps(context, ensure_ascii=False)}\n\n"
                    f"Investigator question: {question}"
                )},
            ],
        )
        content = resp.choices[0].message.content
        return content.strip() if content else "No answer produced."

    async def stream(self, case_id: str, question: str):
        """Yield the answer token-by-token (ChatGPT-style). The caller is
        responsible for persisting the accumulated text once the stream ends."""
        context = self._context(case_id)
        stream = await self._client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Case evidence JSON:\n{json.dumps(context, ensure_ascii=False)}\n\n"
                    f"Investigator question: {question}"
                )},
            ],
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
