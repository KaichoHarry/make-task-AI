# src/task_planning/db.py
from __future__ import annotations
import json
import sqlite3
from typing import Any, Dict, List, Optional


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ac_task_runs (
          us_id TEXT NOT NULL,
          ac_index INTEGER NOT NULL,
          ac_text TEXT NOT NULL,
          score INTEGER NOT NULL,
          max_tasks_per_ac INTEGER NOT NULL,
          status TEXT NOT NULL,              -- "ok" | "error"
          result_json TEXT NOT NULL,         -- items[1件] を丸ごとJSON
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now')),
          PRIMARY KEY (us_id, ac_index)
        );
        """
    )
    conn.commit()
    conn.close()


def upsert_run(
    db_path: str,
    *,
    us_id: str,
    ac_index: int,
    ac_text: str,
    score: int,
    max_tasks_per_ac: int,
    status: str,
    result_obj: Dict[str, Any],
) -> None:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ac_task_runs
          (us_id, ac_index, ac_text, score, max_tasks_per_ac, status, result_json, updated_at)
        VALUES
          (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(us_id, ac_index) DO UPDATE SET
          ac_text=excluded.ac_text,
          score=excluded.score,
          max_tasks_per_ac=excluded.max_tasks_per_ac,
          status=excluded.status,
          result_json=excluded.result_json,
          updated_at=datetime('now');
        """,
        (
            us_id,
            int(ac_index),
            str(ac_text),
            int(score),
            int(max_tasks_per_ac),
            str(status),
            json.dumps(result_obj, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def fetch_all(db_path: str, *, us_id: str) -> List[Dict[str, Any]]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT ac_index, result_json FROM ac_task_runs WHERE us_id=? ORDER BY ac_index ASC",
        (us_id,),
    )
    rows = cur.fetchall()
    conn.close()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(json.loads(r["result_json"]))
    return out