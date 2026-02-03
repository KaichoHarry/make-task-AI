# src/task_planning/merge_parts.py
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime
from typing import Any, Dict, List


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in-dir", default="out_parts")
    p.add_argument("-o", "--output", default="out.json")
    args = p.parse_args()

    files = sorted(glob.glob(os.path.join(args.in_dir, "out_part_*.json")))
    if not files:
        raise RuntimeError(f"No part files found in: {args.in_dir}")

    all_items: List[Dict[str, Any]] = []
    metas: List[Dict[str, Any]] = []

    for fp in files:
        d = json.load(open(fp, "r", encoding="utf-8"))
        if isinstance(d.get("meta"), dict):
            metas.append(d["meta"])
        items = d.get("items", [])
        if isinstance(items, list):
            all_items.extend([x for x in items if isinstance(x, dict)])

    # ac_index順に並び替え
    all_items.sort(key=lambda x: int(x.get("ac_index", 10**9)))

    out = {
        "meta": {
            "merged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parts_dir": args.in_dir,
            "parts_count": len(files),
            "items_count": len(all_items),
        },
        "items": all_items,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[OK] merged -> {args.output} items={len(all_items)} parts={len(files)}")


if __name__ == "__main__":
    main()