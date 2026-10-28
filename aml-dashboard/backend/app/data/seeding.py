"""Populate the persistent Store with the base demo state (from seed.py).

Called by build_app_state() when the DB is empty, and on demo reset. This is the
single definition of "base state" — the 6 seeded cases, primary-case notes /
audit, and the initial notifications.
"""
from __future__ import annotations

from app.data import seed
from app.data.investigation_gen import generate_bundle
from app.persistence import Store
from app.services.scoring import ScoringModel


def _primary_bundle() -> dict:
    """The hand-authored showcase investigation, kept pixel-identical."""
    return {
        "account_profile": dict(seed.ACCOUNT_PROFILE),
        "timeline": [dict(t) for t in seed.TIMELINE],
        "graph": {"nodes": [dict(n) for n in seed.GRAPH_NODES],
                  "links": [dict(l) for l in seed.GRAPH_LINKS]},
        "risk_signals": [dict(s) for s in seed.RISK_SIGNALS],
        "total_score": 91,
        "iob_pattern": {
            "title": "Jan Dhan Spike",
            "detail": "₹4,90,000 received — 47x the average Jan Dhan transaction value "
                      "at Madurai South branch (branch average: ₹10,400).",
            "extra": "Account opened under PM Jan Dhan Yojana — financial inclusion "
                     "account misused as pass-through relay.",
        },
        "summary": {"en": seed.SUMMARY_EN, "ta": seed.SUMMARY_TA},
    }


def seed_base(store: Store, ml: ScoringModel) -> None:
    for c in seed.CASES:
        is_primary = c["id"] == seed.PRIMARY_CASE_ID
        if is_primary:
            # hand-authored showcase — keep its curated score + rich signals
            store.save_case(dict(c), 87, "none")
            store.save_investigation(c["id"], _primary_bundle())
        else:
            # every other case is scored by the real ml_pipeline model
            bundle = generate_bundle(c)
            result = ml.score_account(bundle)
            case = dict(c)
            case["score"] = result["score"]
            bundle["total_score"] = result["score"]
            bundle["risk_signals"] = result["signals"]
            store.save_case(case, None, "none")
            store.save_investigation(c["id"], bundle)

    for note in seed.INITIAL_NOTES:
        store.save_note(seed.PRIMARY_CASE_ID, dict(note))

    for notif in seed.INITIAL_NOTIFICATIONS:
        store.save_notification({**notif, "read": False})

    for entry in seed.AUDIT_LOG:
        store.append_audit(seed.PRIMARY_CASE_ID, dict(entry))
