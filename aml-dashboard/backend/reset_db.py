#!/usr/bin/env python3
"""
Reset the AML Shield demo to its clean base state.

Run this between demo runs (after the seeder has added cases / teammate activity)
to get back to the seeded 6 cases and base notifications.

- If the backend is running, it calls POST /admin/reset (live reset, no restart).
- If the backend is down, it deletes the SQLite file so the next start reseeds.

Usage:  python reset_db.py
"""
from __future__ import annotations

import os
import sys

import httpx

from app.persistence import DB_PATH

RESET_URL = "http://localhost:8000/api/v1/admin/reset"


def main() -> int:
    try:
        r = httpx.post(RESET_URL, timeout=5.0)
        r.raise_for_status()
        print(f"✓ Reset via API — base restored ({r.json().get('cases')} cases).")
        return 0
    except Exception:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"✓ Backend not running — deleted {DB_PATH}. Next start reseeds base.")
        else:
            print("✓ No DB file found — already at base state.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
