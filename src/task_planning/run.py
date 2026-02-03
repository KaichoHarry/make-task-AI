import argparse
import json
from datetime import datetime

from .pipeline import run_pipeline


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_acs(input_obj) -> list[str]:
    """
    代表例: tests/fixtures/login_us001.json
      {
        "domain": "...",
        "persona": "...",
        "action": "...",
        "reason": "...",
        "acceptance_criteria": ["...", ...]
      }

    将来フォーマットの最低限にも対応:
      - {"acs":[...]} / {"ac":[...]}
      - {"items":[{"ac_text":"..."}]}
    """
    x = input_obj[0] if isinstance(input_obj, list) and input_obj else input_obj
    if not isinstance(x, dict):
        return []

    for k in ["acceptance_criteria", "acs", "ac"]:
        if isinstance(x.get(k), list):
            return [str(s).strip() for s in x[k] if str(s).strip()]

    # 予備：{"items":[{"ac_text":"..."}]}
    if isinstance(x.get("items"), list):
        out: list[str] = []
        for it in x["items"]:
            if isinstance(it, dict) and it.get("ac_text"):
                s = str(it["ac_text"]).strip()
                if s:
                    out.append(s)
        return out

    return []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", default="tests/fixtures/login_us001.json")
    p.add_argument("-o", "--output", default="out.json")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--max-tasks-per-ac", type=int, default=6)
    p.add_argument("--max-repairs", type=int, default=1)
    p.add_argument("--limit", type=int, default=0)  # 0 or negative => no limit
    args = p.parse_args()

    input_json = _load_json(args.input)
    acs = extract_acs(input_json)

    if args.limit and args.limit > 0:
        acs = acs[: args.limit]

    if not acs:
        raise RuntimeError(
            "No acceptance_criteria found. "
            "Input must contain key: acceptance_criteria/acs/ac (list[str]) "
            "or items[].ac_text."
        )

    result = run_pipeline(
        model=args.model,
        acceptance_criteria=acs,
        max_tasks_per_ac=args.max_tasks_per_ac,
        max_repairs=args.max_repairs,
    )

    # ✅ pipeline が壊れて items が 0 や型違いで返ってくるケースを即検知
    items = result.get("items", [])
    if not isinstance(items, list):
        raise RuntimeError(f"Pipeline returned invalid items type: {type(items)}")

    if len(items) == 0:
        raise RuntimeError(
            "Pipeline returned 0 items. "
            "This usually means ingest passed 0 ACs, or pipeline swallowed an error."
        )

    # ✅ meta は merge（上書きしない）
    result.setdefault("meta", {})
    result["meta"].update(
        {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": args.model,
            "max_tasks_per_ac": args.max_tasks_per_ac,
            "max_repairs": args.max_repairs,
            "limit": args.limit,
            "ac_count": len(acs),
        }
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] wrote: {args.output}")


if __name__ == "__main__":
    main()