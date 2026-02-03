# src/task_planning/batch_run.py
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List

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

    # 予備：{"items":[{"ac_text":"..."}]}
    if isinstance(x.get("items"), list):
        out = []
        for it in x["items"]:
            if isinstance(it, dict) and it.get("ac_text"):
                out.append(str(it["ac_text"]).strip())
        return out

    return []


def max_tasks_from_global_score(score: int) -> int:
    # 0–40 -> 5, 41–70 -> 3, 71–90 -> 2（それ以外は安全側で3）
    if 0 <= score <= 40:
        return 5
    if 41 <= score <= 70:
        return 3
    if 71 <= score <= 90:
        return 2
    return 3


def _part_name(out_dir: str, start_idx: int, end_idx: int) -> str:
    return os.path.join(out_dir, f"out_part_{start_idx:03d}_{end_idx:03d}.json")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", default="tests/fixtures/login_us001.json")
    p.add_argument("--out-dir", default="out_parts")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--score", type=int, default=50)
    p.add_argument("--batch", type=int, default=5)  # 5件ずつ
    p.add_argument("--max-repairs", type=int, default=1)
    p.add_argument("--limit", type=int, default=0)  # 0 => 全部
    p.add_argument("--resume", action="store_true")  # 既存partがあればスキップ
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    input_json = _load_json(args.input)
    acs = extract_acs(input_json)
    if args.limit and args.limit > 0:
        acs = acs[: args.limit]

    if not acs:
        raise RuntimeError("No acceptance_criteria found.")

    max_tasks_per_ac = max_tasks_from_global_score(int(args.score))

    total = len(acs)
    batch = max(1, int(args.batch))

    # 1-based indexで扱う（わかりやすい）
    start = 1
    while start <= total:
        end = min(total, start + batch - 1)
        out_path = _part_name(args.out_dir, start, end)

        if args.resume and os.path.exists(out_path):
            print(f"[SKIP] exists: {out_path}")
            start = end + 1
            continue

        subset = acs[start - 1 : end]

        result = run_pipeline(
            model=args.model,
            acceptance_criteria=subset,
            max_tasks_per_ac=max_tasks_per_ac,
            max_repairs=args.max_repairs,
        )

        # AC index を「全体の番号」に補正（重要）
        for i, it in enumerate(result.get("items", []), start=start):
            if isinstance(it, dict):
                it["ac_index"] = i

        payload: Dict[str, Any] = {
            "meta": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "model": args.model,
                "score": int(args.score),
                "max_tasks_per_ac": int(max_tasks_per_ac),
                "max_repairs": int(args.max_repairs),
                "range": {"start": start, "end": end, "total": total},
                "input": args.input,
            },
            "items": result.get("items", []),
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"[OK] wrote: {out_path} items={len(payload['items'])}")
        start = end + 1


if __name__ == "__main__":
    main()