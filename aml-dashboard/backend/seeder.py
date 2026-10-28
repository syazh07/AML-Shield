#!/usr/bin/env python3
"""
AML Shield — live demo seeder.

A *triggerable* script (not an always-on service) that simulates the Transaction
Monitoring Engine and a working analyst team by calling the running backend API
over HTTP. Run it during a demo and the dashboard visibly comes alive: new cases
flow into the pool, notifications fire, and teammates claim / close cases.

The frontend polls the API, so whatever this script pushes shows up within a few
seconds — no frontend changes, clean frontend/backend separation.

Usage:
    # stream a new event every ~4s until Ctrl+C
    python seeder.py

    # inject a quick burst of 8 cases and exit
    python seeder.py --mode burst --count 8

    # slower stream against a remote host
    python seeder.py --interval 8 --url http://localhost:8000/api/v1
"""
from __future__ import annotations

import argparse
import random
import sys
import time

import httpx

FLAGS = [
    "Jan Dhan Spike", "Gulf Remittance Layering", "Fan-Out Structure",
    "Dormancy Break", "Velocity Spike", "DBT Subsidy Diversion",
    "Pass-Through", "Structuring / Smurfing", "Impossible Travel",
]
ACCT_TYPES = ["Jan Dhan", "Savings", "Current", "NRI"]
TEAMMATES = ["Arjun Krishnan", "Ravi Kumar"]
CLOSE_REASONS = ["False Positive", "Confirmed Mule", "Insufficient Evidence", "Legitimate Business"]


def next_case_number(client: httpx.Client) -> int:
    """Continue the IOB-2024-MU-#### sequence after the highest existing case."""
    try:
        cases = client.get("/cases").json()
        nums = [int(c["id"].split("-")[-1]) for c in cases if c["id"].startswith("IOB-2024-MU-")]
        return (max(nums) + 1) if nums else 4472
    except Exception:
        return 4472


def make_case(number: int) -> dict:
    score = random.choices(
        [random.randint(35, 59), random.randint(60, 84), random.randint(85, 97)],
        weights=[2, 4, 3],
    )[0]
    deadline = random.choice([167, 166, 143, 96, 71, 47, 23.5, 11.2])
    return {
        "id": f"IOB-2024-MU-{number}",
        "account": f"AC{random.randint(1000000, 9999999)}",
        "type": random.choice(ACCT_TYPES),
        "score": score,
        "flag": random.choice(FLAGS),
        "status": "unclaimed",
        "claimedBy": None,
        "openedMin": 0,
        "strDeadlineHrs": deadline,
        "urgent": score >= 85 or deadline < 48,
    }


def emit_case(client: httpx.Client, number: int) -> None:
    case = make_case(number)
    r = client.post("/cases", json=case)
    r.raise_for_status()
    tag = "🔴 CRITICAL" if case["score"] >= 85 else "🟡 alert  "
    print(f"  {tag}  {case['id']}  {case['account']}  score {case['score']:>2}  {case['flag']}")


def teammate_action(client: httpx.Client) -> None:
    """Occasionally have a teammate claim an unclaimed case or close an active one."""
    cases = client.get("/cases").json()
    if random.random() < 0.5:
        pool = [c for c in cases if c["status"] == "unclaimed"]
        if pool:
            c = random.choice(pool)
            who = random.choice(TEAMMATES)
            client.post(f"/cases/{c['id']}/claim", json={"analyst_name": who})
            print(f"  👤 {who} claimed {c['id']}")
    else:
        pool = [c for c in cases if c["status"] == "in-progress" and c["claimedBy"] in TEAMMATES]
        if pool:
            c = random.choice(pool)
            reason = random.choice(CLOSE_REASONS)
            client.post(f"/cases/{c['id']}/close", params={"actor": c["claimedBy"]}, json={"reason": reason})
            print(f"  ✅ {c['claimedBy']} closed {c['id']} · {reason}")


def main() -> int:
    ap = argparse.ArgumentParser(description="AML Shield live demo seeder")
    ap.add_argument("--url", default="http://localhost:8000/api/v1", help="API base URL")
    ap.add_argument("--mode", choices=["stream", "burst"], default="stream")
    ap.add_argument("--count", type=int, default=0, help="events to emit (0 = infinite in stream mode)")
    ap.add_argument("--interval", type=float, default=4.0, help="seconds between events (stream mode)")
    args = ap.parse_args()

    client = httpx.Client(base_url=args.url, timeout=5.0)
    try:
        client.get("/health")
    except Exception:
        print(f"✗ Cannot reach backend at {args.url}. Start it first:\n"
              f"    uvicorn app.main:app --reload --port 8000", file=sys.stderr)
        return 1

    number = next_case_number(client)
    interval = 0.4 if args.mode == "burst" else args.interval
    limit = args.count if args.count > 0 else (8 if args.mode == "burst" else None)

    print(f"● Seeding {args.url}  (mode={args.mode}, interval={interval}s, "
          f"limit={limit or '∞'})  — Ctrl+C to stop\n")
    emitted = 0
    try:
        while limit is None or emitted < limit:
            emit_case(client, number)
            number += 1
            emitted += 1
            # in stream mode, sprinkle in teammate activity
            if args.mode == "stream" and random.random() < 0.4:
                teammate_action(client)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n● Stopped.")
    finally:
        client.close()
    print(f"\n● Emitted {emitted} case(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
