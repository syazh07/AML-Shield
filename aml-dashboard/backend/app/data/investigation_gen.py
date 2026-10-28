"""Generate a per-case investigation bundle (profile, timeline, graph, risk
signals, summary) so EVERY case is fully explorable from the API — not just the
one hand-authored demo case.

To keep the d3 timeline/graph robust, generated cases reuse the same 5 event
timestamps and 6-node topology as the showcase case; only the amounts, parties,
flags, and narrative differ per case. Generation is deterministic (seeded by
case id) so a case looks identical across restarts.
"""
from __future__ import annotations

import hashlib
import random

# fixed event clock + graph roles (shared time domain keeps the viz stable)
_TIMES = ["14:31:02", "14:32:44", "14:33:11", "14:33:58", "14:34:22"]

_FLAG_STORY = {
    "Jan Dhan Spike": ("Large credit to dormant Jan Dhan", "Jan Dhan account misused as pass-through relay"),
    "Gulf Remittance Layering": ("Inward SWIFT remittance from Gulf", "NRI remittance split immediately via UPI"),
    "Fan-Out Structure": ("Single credit fanned out", "1 source, multiple receivers in minutes"),
    "Dormancy Break": ("Credit to long-dormant account", "Account dormant for months before this event"),
    "Velocity Spike": ("Abnormal transaction velocity", "Sudden burst far above account baseline"),
    "DBT Subsidy Diversion": ("DBT subsidy credit diverted", "PM-KISAN/scholarship credit routed onward"),
    "Pass-Through": ("Pass-through credit", "~Full inflow forwarded within minutes"),
    "Structuring / Smurfing": ("Structured just under CTR line", "Repeated amounts below ₹50,000"),
    "Impossible Travel": ("Geo-impossible session", "Logins from distant cities minutes apart"),
}


def _acc(seed: str, i: int) -> str:
    h = int(hashlib.md5(f"{seed}:{i}".encode()).hexdigest(), 16)
    return "AC" + str(1000000 + h % 9000000)


def _rupees(n: int) -> str:
    return "₹" + f"{n:,}"


def _signal(sid, title, pts, desc, rule, formula, evidence, weight, precision, trained, trace, highlight):
    return {
        "id": sid, "title": title, "pts": pts, "desc": desc, "highlight": highlight,
        "rule": rule, "formula": formula, "evidence": evidence,
        "model": {"weight": weight, "precision": precision, "trained": trained},
        "trace": trace,
    }


def generate_bundle(case: dict) -> dict:
    rng = random.Random(case["id"])
    acct = case["account"]
    typ = case["type"]
    flag = case["flag"]
    score = int(case["score"])

    amount_in = rng.choice([490000, 360000, 280000, 210000, 155000, 120000])
    # vary how much is forwarded per case so the model produces a realistic spread
    # of scores (near-total pass-through = high risk; partial = medium/low)
    ratio_target = rng.choice([0.99, 0.97, 0.93, 0.82, 0.66, 0.54])
    outs = [round(amount_in * ratio_target * f) for f in (0.50, 0.42, 0.06, 0.02)]
    parties = [_acc(case["id"], i) for i in range(5)]
    primary_hl = {"type": "node", "id": acct}
    lead, pattern_extra = _FLAG_STORY.get(flag, ("Suspicious credit", "Behaviour inconsistent with account profile"))

    timeline = [
        {"t": _TIMES[0], "dir": "credit", "amt": amount_in, "party": parties[0], "channel": "IMPS", "flag": lead},
        {"t": _TIMES[1], "dir": "debit", "amt": outs[0], "party": parties[1], "channel": "UPI", "flag": "Rapid onward transfer"},
        {"t": _TIMES[2], "dir": "debit", "amt": outs[1], "party": parties[2], "channel": "UPI", "flag": "Recipient recently opened"},
        {"t": _TIMES[3], "dir": "debit", "amt": outs[2], "party": parties[3], "channel": "ATM", "flag": "ATM cash-out node"},
        {"t": _TIMES[4], "dir": "debit", "amt": outs[3], "party": parties[4], "channel": "UPI", "flag": "Possible test ping pattern"},
    ]

    nodes = [
        {"id": parties[0], "label": "SOURCE", "role": "victim", "color": "#ef4444", "size": 26, "balance": _rupees(amount_in * 3), "type": "Savings", "note": "Funds origin — likely victim"},
        {"id": acct, "label": "PRIMARY", "role": "primary", "color": "#f59e0b", "size": 38, "balance": _rupees(rng.randint(500, 9000)), "type": typ, "note": "Primary mule under investigation"},
        {"id": parties[1], "label": "RELAY-1", "role": "relay", "color": "#f59e0b", "size": 28, "balance": _rupees(rng.randint(1000, 12000)), "type": "Savings", "note": "Onward relay node"},
        {"id": parties[2], "label": "RELAY-2", "role": "relay", "color": "#f59e0b", "size": 28, "balance": _rupees(rng.randint(500, 4000)), "type": "Savings", "note": "Recently opened account"},
        {"id": parties[3], "label": "CASH-OUT", "role": "cashout", "color": "#8b5cf6", "size": 32, "balance": "—", "type": "ATM", "note": "ATM withdrawal endpoint"},
        {"id": parties[4], "label": "LINKED", "role": "linked", "color": "#94a3b8", "size": 20, "balance": _rupees(rng.randint(100, 1500)), "type": "Savings", "note": "Possible test-ping account"},
    ]
    links = [
        {"source": parties[0], "target": acct, "amt": amount_in, "t": _TIMES[0], "channel": "IMPS"},
        {"source": acct, "target": parties[1], "amt": outs[0], "t": _TIMES[1], "channel": "UPI"},
        {"source": acct, "target": parties[2], "amt": outs[1], "t": _TIMES[2], "channel": "UPI"},
        {"source": acct, "target": parties[3], "amt": outs[2], "t": _TIMES[3], "channel": "ATM"},
        {"source": acct, "target": parties[4], "amt": outs[3], "t": _TIMES[4], "channel": "UPI"},
    ]

    forwarded = sum(outs)
    ratio = forwarded / amount_in
    signals = [
        _signal("pass", "Pass-Through Pattern", min(30, round(score * 0.31)),
                f"{ratio*100:.0f}% outward ratio within minutes", "RULE_PASS_THROUGH_90S",
                "Σ(outflow within 90s) ÷ inflow_amount ≥ 0.85",
                [{"k": "Inflow", "v": f"{_rupees(amount_in)} from {parties[0]}"},
                 {"k": "Forwarded", "v": _rupees(forwarded), "emp": True},
                 {"k": "Ratio", "v": f"{ratio*100:.1f}% (threshold 85%)", "emp": True}],
                "0.30", "0.87", "12,400", "Feature vector v3.2.1 · calibrated 2024-Q3", primary_hl),
        _signal("fanout", "Fan-Out Structure", min(30, round(score * 0.18)),
                "1 credit source, 4 debit destinations in minutes", "RULE_FANOUT_STRUCTURE",
                "distinct_recipients(window=300s) ≥ 3",
                [{"k": "Recipients", "v": ", ".join(parties[1:])},
                 {"k": "Distinct", "v": "4 of 4 unique", "emp": True}],
                "0.16", "0.74", "9,800", "Structural graph match · mule topology M-12", primary_hl),
        _signal("new", "New Account Link", min(30, round(score * 0.10)),
                f"{parties[2]} opened recently", "RULE_NEW_ACCOUNT_LINK",
                "exists(neighbor n WHERE age_days(n) < 30)",
                [{"k": "Counterparty", "v": parties[2]},
                 {"k": "Opened", "v": f"{rng.randint(3, 21)} days ago", "emp": True}],
                "0.08", "0.63", "15,200", "Account-age check on N+1 neighbour set",
                {"type": "node", "id": parties[2]}),
    ]

    profile = {
        "account": acct, "type": typ,
        "opened": f"{rng.randint(6, 26)} months ago",
        "dormant": f"{rng.randint(3, 14)} months before this event",
        "branch": rng.choice(["Madurai South", "Chennai Egmore", "Coimbatore RS Puram", "Salem Fort"]),
        "kyc": rng.choice(["Basic eKYC", "Full KYC", "Basic eKYC, mobile-only"]),
        "mobile": "9" + "X" * 7 + str(rng.randint(0, 9)),
        "pan": "X" * 4 + str(rng.randint(1000, 9999)) + "X",
        "balanceBefore": _rupees(rng.randint(100, 900)),
        "balancePeak": _rupees(amount_in + rng.randint(100, 900)),
        "balanceCurrent": _rupees(rng.randint(500, 9000)),
    }

    summary_en = (
        f"This {typ} account ({acct}) received {_rupees(amount_in)} and forwarded "
        f"{ratio*100:.0f}% of it within minutes across four accounts. The pattern is "
        f"consistent with a {flag.lower()} mule operation."
    )
    summary_ta = (
        f"இந்த {typ} கணக்கு ({acct}) {_rupees(amount_in)} பெற்று சில நிமிடங்களில் "
        f"நான்கு கணக்குகளுக்கு {ratio*100:.0f}% அனுப்பியது. இது ஒரு மியூல் செயல்பாட்டுக்கு ஒத்துப்போகிறது."
    )

    return {
        "account_profile": profile,
        "timeline": timeline,
        "graph": {"nodes": nodes, "links": links},
        "risk_signals": signals,
        "total_score": score,
        "iob_pattern": {
            "title": flag,
            "detail": f"{_rupees(amount_in)} received and rapidly forwarded — flagged as {flag}.",
            "extra": pattern_extra,
        },
        "summary": {"en": summary_en, "ta": summary_ta},
    }
