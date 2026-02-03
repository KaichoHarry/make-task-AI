# src/task_planning/run.py
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from .pipeline import run_pipeline


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_acs(input_obj) -> list[str]:
    x = input_obj[0] if isinstance(input_obj, list) and input_obj else input_obj
    if not isinstance(x, dict):
        return []

    if isinstance(x.get("acceptance_criteria"), list):
        return [str(s).strip() for s in x["acceptance_criteria"] if str(s).strip()]

    if isinstance(x.get("items"), list):
        out: list[str] = []
        for it in x["items"]:
            if isinstance(it, dict) and it.get("ac_text"):
                s = str(it["ac_text"]).strip()
                if s:
                    out.append(s)
        return out

    return []


def max_tasks_from_score(score: int) -> int:
    # 0–40 → 5, 41–70 → 3, 71–90 → 2
    if score <= 40:
        return 5
    if score <= 70:
        return 3
    return 2


# -------------------------
# SQLite helpers
# -------------------------
def _db_connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _db_init(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ac_results (
          ac_index INTEGER PRIMARY KEY,
          ac_text TEXT NOT NULL,
          ok INTEGER NOT NULL,
          error TEXT,
          item_json TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _db_has(conn: sqlite3.Connection, ac_index: int) -> bool:
    cur = conn.execute("SELECT 1 FROM ac_results WHERE ac_index=? LIMIT 1", (ac_index,))
    return cur.fetchone() is not None


def _db_upsert(conn: sqlite3.Connection, item: Dict[str, Any]) -> None:
    ac_index = int(item.get("ac_index", 0))
    ac_text = str(item.get("ac_text", ""))
    ok = 1 if (item.get("validate", {}) or {}).get("pass") else 0
    error = item.get("error")
    item_json = json.dumps(item, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        """
        INSERT INTO ac_results (ac_index, ac_text, ok, error, item_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ac_index) DO UPDATE SET
          ac_text=excluded.ac_text,
          ok=excluded.ok,
          error=excluded.error,
          item_json=excluded.item_json,
          updated_at=excluded.updated_at
        """,
        (ac_index, ac_text, ok, error, item_json, now),
    )


def _db_load_range(conn: sqlite3.Connection, start: int, end: int) -> List[Dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT item_json FROM ac_results
        WHERE ac_index BETWEEN ? AND ?
        ORDER BY ac_index ASC
        """,
        (start, end),
    )
    out: List[Dict[str, Any]] = []
    for (item_json,) in cur.fetchall():
        try:
            out.append(json.loads(item_json))
        except Exception:
            continue
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", default="tests/fixtures/login_us001.json")
    p.add_argument("-o", "--output", default="out.json")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--max-repairs", type=int, default=1)

    p.add_argument("--start", type=int, default=1, help="Start AC index (1-based)")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--score", type=int, default=50)

    # ✅ バッチサイズ（5件ずつ）
    p.add_argument("--batch-size", type=int, default=5)

    # ✅ DB保存先
    p.add_argument("--db", default="", help="Path to sqlite file. If set, save per-AC results here.")

    # ✅ 途中再開
    p.add_argument("--resume", action="store_true")

    args = p.parse_args()

    input_json = _load_json(args.input)
    all_acs = extract_acs(input_json)
    if not all_acs:
        raise RuntimeError("No acceptance_criteria found. Input must contain key: acceptance_criteria (list[str]).")

    total = len(all_acs)

    start = max(1, int(args.start))
    start0 = start - 1
    if start0 >= total:
        raise RuntimeError(f"--start is out of range. start={start} but total_acs={total}")

    if args.limit and int(args.limit) > 0:
        end0 = min(total, start0 + int(args.limit))
    else:
        end0 = total

    selected_acs = all_acs[start0:end0]
    if not selected_acs:
        raise RuntimeError("No ACs selected. Check --start/--limit range.")

    end_ac = start + len(selected_acs) - 1

    score = int(args.score)
    max_tasks_per_ac = max_tasks_from_score(score)
    batch_size = max(1, int(args.batch_size))

    conn: Optional[sqlite3.Connection] = None
    if args.db:
        conn = _db_connect(args.db)
        _db_init(conn)

    # -------------------------
    # Run in batches
    # -------------------------
    saved = 0
    skipped = 0

    for batch_offset in range(0, len(selected_acs), batch_size):
        batch_acs = selected_acs[batch_offset : batch_offset + batch_size]
        batch_start_ac_index = start + batch_offset
        original_batch_end = batch_start_ac_index + len(batch_acs) - 1

        # resume: 既存は飛ばす（AC単位）
        if conn and args.resume:
            filtered: List[str] = []
            filtered_indices: List[int] = []

            for i, ac_text in enumerate(batch_acs):
                ac_index = batch_start_ac_index + i
                if _db_has(conn, ac_index):
                    skipped += 1
                    continue
                filtered.append(ac_text)
                filtered_indices.append(ac_index)

            # 全部スキップなら次へ（ログ出す）
            if not filtered:
                print(f"[BATCH] range={batch_start_ac_index}-{original_batch_end} size={len(batch_acs)} -> skip(all in DB)")
                continue

            batch_acs = filtered
            batch_start_ac_index = filtered_indices[0]

        # 実行直前ログ（実際に回す範囲）
        actual_batch_end = batch_start_ac_index + len(batch_acs) - 1
        print(f"[BATCH] range={batch_start_ac_index}-{actual_batch_end} size={len(batch_acs)}")

        # 実行
        result = run_pipeline(
            model=args.model,
            acceptance_criteria=batch_acs,
            max_tasks_per_ac=max_tasks_per_ac,
            max_repairs=int(args.max_repairs),
            start_ac_index=batch_start_ac_index,
        )

        # DB保存
        if conn:
            for item in result.get("items", []):
                _db_upsert(conn, item)
                saved += 1
            conn.commit()

    # -------------------------
    # Final output
    # -------------------------
    if conn:
        items = _db_load_range(conn, start, end_ac)
        result_out = {"items": items}
        conn.close()
        db_path = args.db
    else:
        result_out = run_pipeline(
            model=args.model,
            acceptance_criteria=selected_acs,
            max_tasks_per_ac=max_tasks_per_ac,
            max_repairs=int(args.max_repairs),
            start_ac_index=start,
        )
        db_path = ""

    result_out["meta"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": args.model,
        "max_repairs": int(args.max_repairs),
        "start": start,
        "limit": int(args.limit),
        "score": score,
        "max_tasks_per_ac": int(max_tasks_per_ac),
        "batch_size": int(batch_size),
        "ac_count_selected": len(selected_acs),
        "ac_count_total": total,
        "range": f"{start}-{end_ac}",
        "db": db_path,
        "saved": saved,
        "skipped": skipped,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result_out, f, ensure_ascii=False, indent=2)

    print(
        f"[OK] wrote: {args.output} range={start}-{end_ac} "
        f"score={score} max_tasks_per_ac={max_tasks_per_ac} "
        f"batch_size={batch_size} db={db_path or '(none)'} saved={saved} skipped={skipped}"
    )


if __name__ == "__main__":
    main()