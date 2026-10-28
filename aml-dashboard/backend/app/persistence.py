"""
Tiny SQLite persistence layer (stdlib sqlite3 — no extra dependency).

Each entity is stored as a JSON document in a typed table, which keeps the
existing dict-shaped service logic unchanged while giving real durability across
restarts. Services load their in-memory caches from here on startup and
write-through on every mutation.

The DB file lives at backend/aml_shield.db (gitignored). `wipe()` clears it for
the demo-reset flow.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aml_shield.db"
)


class Store:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA busy_timeout=3000")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notes (
                    pk INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit (
                    pk INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS investigation (
                    case_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS str_drafts (
                    case_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat (
                    pk INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    data TEXT NOT NULL
                );
                """
            )

    # --- cases (stored with their confidence + str_status) ------------------ #
    def is_empty(self) -> bool:
        cur = self._conn.execute("SELECT COUNT(*) AS n FROM cases")
        return cur.fetchone()["n"] == 0

    def save_case(self, case: dict, confidence: int | None, str_status: str) -> None:
        doc = json.dumps({"case": case, "confidence": confidence, "strStatus": str_status})
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO cases (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (case["id"], doc),
            )

    def all_cases(self) -> list[dict]:
        cur = self._conn.execute("SELECT data FROM cases")
        return [json.loads(r["data"]) for r in cur.fetchall()]

    # --- notifications ------------------------------------------------------ #
    def save_notification(self, notif: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO notifications (id, data) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (notif["id"], json.dumps(notif)),
            )

    def all_notifications(self) -> list[dict]:
        cur = self._conn.execute("SELECT data FROM notifications ORDER BY id")
        return [json.loads(r["data"]) for r in cur.fetchall()]

    def delete_notification(self, notif_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))

    # --- notes -------------------------------------------------------------- #
    def save_note(self, case_id: str, note: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO notes (case_id, data) VALUES (?, ?)",
                (case_id, json.dumps(note)),
            )

    def notes_by_case(self) -> dict[str, list[dict]]:
        cur = self._conn.execute("SELECT case_id, data FROM notes ORDER BY pk")
        out: dict[str, list[dict]] = {}
        for r in cur.fetchall():
            out.setdefault(r["case_id"], []).append(json.loads(r["data"]))
        return out

    # --- audit -------------------------------------------------------------- #
    def append_audit(self, case_id: str, entry: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO audit (case_id, data) VALUES (?, ?)",
                (case_id, json.dumps(entry)),
            )

    def audit_by_case(self) -> dict[str, list[dict]]:
        cur = self._conn.execute("SELECT case_id, data FROM audit ORDER BY pk")
        out: dict[str, list[dict]] = {}
        for r in cur.fetchall():
            out.setdefault(r["case_id"], []).append(json.loads(r["data"]))
        return out

    # --- investigation bundle (profile, timeline, graph, signals, summary) -- #
    def save_investigation(self, case_id: str, bundle: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO investigation (case_id, data) VALUES (?, ?) "
                "ON CONFLICT(case_id) DO UPDATE SET data = excluded.data",
                (case_id, json.dumps(bundle)),
            )

    def get_investigation(self, case_id: str) -> dict | None:
        cur = self._conn.execute("SELECT data FROM investigation WHERE case_id = ?", (case_id,))
        row = cur.fetchone()
        return json.loads(row["data"]) if row else None

    # --- STR drafts (persisted so a generated/edited draft survives restart) - #
    def save_str_draft(self, case_id: str, draft: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO str_drafts (case_id, data) VALUES (?, ?) "
                "ON CONFLICT(case_id) DO UPDATE SET data = excluded.data",
                (case_id, json.dumps(draft)),
            )

    def all_str_drafts(self) -> dict[str, dict]:
        cur = self._conn.execute("SELECT case_id, data FROM str_drafts")
        return {r["case_id"]: json.loads(r["data"]) for r in cur.fetchall()}

    # --- copilot chat history (per case) ------------------------------------ #
    def append_chat(self, case_id: str, message: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO chat (case_id, data) VALUES (?, ?)",
                (case_id, json.dumps(message)),
            )

    def chat_for_case(self, case_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT data FROM chat WHERE case_id = ? ORDER BY pk", (case_id,)
        )
        return [json.loads(r["data"]) for r in cur.fetchall()]

    # --- reset -------------------------------------------------------------- #
    def wipe(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                "DELETE FROM cases; DELETE FROM notifications; "
                "DELETE FROM notes; DELETE FROM audit; DELETE FROM investigation; "
                "DELETE FROM str_drafts; DELETE FROM chat;"
            )
