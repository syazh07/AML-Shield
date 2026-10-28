from __future__ import annotations

import asyncio
import json
import secrets
import uuid
from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import settings
from app.data import seed
from app.models.schemas import (
    ComplianceItem,
    StrCiteSegment,
    StrDraft,
    StrEntity,
    StrEvidenceChip,
    StrGenerationJob,
    StrGenerationStep,
    StrStatus,
)
from app.persistence import Store
from app.services.audit_service import AuditService
from app.services.case_service import CaseService


class STRGenerationService:
    def __init__(self, cases: CaseService, audit: AuditService, store: Store) -> None:
        self._cases = cases
        self._audit = audit
        self._store = store
        self._jobs: dict[str, StrGenerationJob] = {}
        # rehydrate any previously generated/edited drafts so they survive restarts
        self._drafts: dict[str, StrDraft] = {
            case_id: StrDraft(**data) for case_id, data in store.all_str_drafts().items()
        }
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def _persist(self, case_id: str) -> None:
        draft = self._drafts.get(case_id)
        if draft is not None:
            self._store.save_str_draft(case_id, draft.model_dump(mode="json"))

    def get_draft(self, case_id: str) -> StrDraft | None:
        return self._drafts.get(case_id)

    def get_job(self, job_id: str) -> StrGenerationJob | None:
        return self._jobs.get(job_id)

    async def start_generation(
        self,
        case_id: str,
        *,
        analyst_confidence: int,
        linked_case_ids: list[str],
    ) -> StrGenerationJob:
        job_id = str(uuid.uuid4())
        steps = [
            StrGenerationStep(index=i, label=label, status="pending")
            for i, label in enumerate(seed.GEN_STEPS)
        ]
        job = StrGenerationJob(
            job_id=job_id,
            case_id=case_id,
            status="queued",
            steps=steps,
        )
        self._jobs[job_id] = job
        self._cases.set_str_status(case_id, StrStatus.DRAFTING.value)
        asyncio.create_task(self._run_job(job_id, case_id, analyst_confidence, linked_case_ids))
        return job

    async def _run_job(
        self,
        job_id: str,
        case_id: str,
        analyst_confidence: int,
        linked_case_ids: list[str],
    ) -> None:
        job = self._jobs[job_id]
        job.status = "running"

        try:
            for i, step in enumerate(job.steps):
                step.status = "running"
                await asyncio.sleep(0.35)
                if i == len(job.steps) - 1:
                    draft = await self._compose_draft(case_id, analyst_confidence, linked_case_ids)
                    job.draft = draft
                    self._drafts[case_id] = draft
                    self._persist(case_id)
                    self._audit.append(case_id, "AML-SYS", "STR draft generated")
                step.status = "done"

            job.status = "completed"
        except Exception as exc:  # noqa: BLE001 — surface job failure to API consumer
            job.status = "failed"
            job.error = str(exc)

    async def _compose_draft(
        self,
        case_id: str,
        analyst_confidence: int,
        linked_case_ids: list[str],
    ) -> StrDraft:
        narrative = await self._generate_narrative(case_id, analyst_confidence, linked_case_ids)

        if case_id == seed.PRIMARY_CASE_ID:
            cite = [StrCiteSegment(**seg) for seg in seed.STR_CITE_SEGMENTS]
            chips = [StrEvidenceChip(**chip) for chip in seed.STR_EVIDENCE_CHIPS]
            entities = [StrEntity(**e) for e in seed.STR_ENTITIES]
            compliance = [ComplianceItem(**i) for i in seed.COMPLIANCE_ITEMS]
        else:
            bundle = self._cases.get_investigation(case_id)
            chips = [StrEvidenceChip(id=s["id"], label=s["rule"], cls="chip-pass", checked=True)
                     for s in bundle["risk_signals"]]
            cite = []
            entities = [StrEntity(account=n["id"], type=n["type"], role=n["label"],
                                  amount="—", note=n["note"]) for n in bundle["graph"]["nodes"]]
            compliance = [
                ComplianceItem(label="Pattern-based reporting criteria met", status="ok", icon="✓"),
                ComplianceItem(label="Cross-case linkage documented", status="ok", icon="✓"),
                ComplianceItem(label="Senior officer review required", status="warn", icon="!"),
            ]

        return StrDraft(
            case_id=case_id,
            status=StrStatus.DRAFTING,
            narrative=narrative,
            cite_segments=cite,
            evidence_chips=chips,
            entities=entities,
            compliance_items=compliance,
            analyst_confidence=analyst_confidence,
            updated_at=datetime.now(timezone.utc),
        )

    def _fallback_narrative(self, case_id: str) -> str:
        if case_id == seed.PRIMARY_CASE_ID:
            return seed.STR_DRAFT_NARRATIVE
        return self._cases.get_investigation(case_id)["summary"]["en"]

    async def _generate_narrative(
        self,
        case_id: str,
        analyst_confidence: int,
        linked_case_ids: list[str],
    ) -> str:
        if not self._client:
            return self._fallback_narrative(case_id)

        # A live OpenAI call can be slow or fail (network, rate limit, model access).
        # It must never block the whole draft — fall back to the seed narrative on
        # timeout/error so generation always completes and the editor renders.
        context = self._build_context(case_id, analyst_confidence, linked_case_ids)
        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=settings.openai_model,
                    temperature=0.2,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an AML compliance assistant drafting a Suspicious Transaction Report (STR) "
                                "narrative for FIU-IND filing. Use formal regulatory language. Reference specific accounts, "
                                "amounts, timestamps, and triggered rules from the evidence. Output plain text only — "
                                "no markdown headings."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Draft the STR narrative using this case evidence JSON:\n"
                                f"{json.dumps(context, indent=2)}"
                            ),
                        },
                    ],
                ),
                timeout=15,
            )
        except Exception:  # noqa: BLE001 — any OpenAI/timeout failure falls back to seed
            return self._fallback_narrative(case_id)

        content = response.choices[0].message.content
        return content.strip() if content else self._fallback_narrative(case_id)

    def _build_context(
        self,
        case_id: str,
        analyst_confidence: int,
        linked_case_ids: list[str],
    ) -> dict:
        bundle = self._cases.get_investigation(case_id)
        return {
            "case_id": case_id,
            "account_profile": bundle["account_profile"],
            "timeline": bundle["timeline"],
            "graph": bundle["graph"],
            "risk_signals": bundle["risk_signals"],
            "summary": bundle["summary"],
            "analyst_confidence": analyst_confidence,
            "linked_case_ids": linked_case_ids,
        }

    def update_draft(self, case_id: str, *, narrative: str | None, evidence_chips, entities) -> StrDraft:
        draft = self._drafts.get(case_id)
        if not draft:
            raise KeyError("No STR draft for case")

        updates = draft.model_dump()
        if narrative is not None:
            updates["narrative"] = narrative
        if evidence_chips is not None:
            updates["evidence_chips"] = evidence_chips
        if entities is not None:
            updates["entities"] = entities
        updates["updated_at"] = datetime.now(timezone.utc)

        draft = StrDraft(**updates)
        self._drafts[case_id] = draft
        self._persist(case_id)
        self._audit.append(case_id, "P.Venkatesh", "STR draft updated")
        return draft

    def submit_review(self, case_id: str) -> StrDraft:
        draft = self._require_draft(case_id)
        draft.status = StrStatus.REVIEW
        self._drafts[case_id] = draft
        self._persist(case_id)
        self._cases.set_str_status(case_id, StrStatus.REVIEW.value)
        self._audit.append(case_id, "P.Venkatesh", "STR submitted for senior review")
        return draft

    def file_str(self, case_id: str) -> StrDraft:
        draft = self._require_draft(case_id)
        ref = f"FIU-2024-IOB-{secrets.token_hex(3).upper()}"
        draft.status = StrStatus.FILED
        draft.fiu_reference = ref
        self._drafts[case_id] = draft
        self._persist(case_id)
        self._cases.set_str_status(case_id, StrStatus.FILED.value)
        self._audit.append(case_id, "AML-SYS", f"STR filed to FIU-IND · ref {ref}")
        return draft

    def _require_draft(self, case_id: str) -> StrDraft:
        draft = self._drafts.get(case_id)
        if not draft:
            raise KeyError("No STR draft for case")
        return draft
