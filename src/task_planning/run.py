# src/task_planning/run.py
from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from .grouping.cluster_agent import cluster_acs
from .grouped_taskgen.taskgen_agent import generate_tasks_for_group

# ✅ new: failsafe
from .failsafe_taskgen import ac_map_to_min_tasks

# ✅ new: traceability
from .traceability import enforce_ac_traceability


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return obj[0]
    if isinstance(obj, dict):
        return obj
    raise RuntimeError("Input JSON must be object or [object].")


def extract_story_and_acs(input_obj: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    story = {
        "domain": input_obj.get("domain", ""),
        "persona": input_obj.get("persona", ""),
        "action": input_obj.get("action", ""),
        "reason": input_obj.get("reason", ""),
    }

    acs: List[str] = []
    if isinstance(input_obj.get("acceptance_criteria"), list):
        for s in input_obj["acceptance_criteria"]:
            t = str(s).strip()
            if t:
                acs.append(t)

    if not acs and isinstance(input_obj.get("items"), list):
        for it in input_obj["items"]:
            if isinstance(it, dict) and it.get("ac_text"):
                t = str(it["ac_text"]).strip()
                if t:
                    acs.append(t)

    return story, acs


def build_ac_map(acs: List[str], *, ac_prefix: str = "AC") -> Dict[str, str]:
    out: Dict[str, str] = {}
    for i, text in enumerate(acs, start=1):
        out[f"{ac_prefix}-{i:03d}"] = text
    return out


def max_tasks_from_score(score: int) -> int:
    if score <= 40:
        return 5
    if score <= 70:
        return 3
    return 2


def _select_range(all_acs: List[str], *, start: int, limit: int) -> List[str]:
    total = len(all_acs)
    start = max(1, int(start))
    start0 = start - 1
    if start0 >= total:
        raise RuntimeError(f"--start is out of range. start={start} but total_acs={total}")

    if limit and int(limit) > 0:
        end0 = min(total, start0 + int(limit))
    else:
        end0 = total

    selected = all_acs[start0:end0]
    if not selected:
        raise RuntimeError("No ACs selected. Check --start/--limit range.")
    return selected


def _auto_tune_grouping_policy(
    n_acs: int,
    *,
    max_ac_per_group: int,
    target_groups_min: int,
    target_groups_max: int,
    max_groups: int,
    min_group_size: int,
) -> Dict[str, int]:
    max_ac_per_group = max(1, int(max_ac_per_group))
    min_group_size = max(2, int(min_group_size))

    feasible_max_groups = max(1, n_acs // min_group_size)
    max_groups = min(int(max_groups), feasible_max_groups)

    tmin = int(target_groups_min)
    tmax = int(target_groups_max)
    if tmin > max_groups:
        tmin = max(1, max_groups - 2)
    if tmax > max_groups:
        tmax = max_groups
    if tmin > tmax:
        tmin = max(1, tmax)

    return {
        "max_ac_per_group": max_ac_per_group,
        "target_groups_min": tmin,
        "target_groups_max": tmax,
        "max_groups": max_groups,
        "min_group_size": min_group_size,
    }


def _make_failsafe_output(
    *,
    story: Dict[str, Any],
    ac_map: Dict[str, str],
    tuned_policy: Dict[str, int],
    output_path: str,
    model: str,
) -> Dict[str, Any]:
    tasks = ac_map_to_min_tasks(ac_map)

    groups = [
        {
            "group_id": "G00",
            "label": "Failsafe: AC-to-Task",
            "tags": ["failsafe"],
            "rationale": "Fallback mode: convert each AC into one task without LLM task generation.",
            "ac_ids": list(ac_map.keys()),
        }
    ]

    grouping = {
        "groups": groups,
        "meta": {
            "fallback": True,
            "reason": "failsafe_taskgen_used",
            "policy_used": tuned_policy,
        },
    }

    group_results = [
        {
            "group_id": "G00",
            "tasks": tasks,
            "meta": {"mode": "failsafe"},
        }
    ]

    # ✅ traceability (failsafe too)
    trace = enforce_ac_traceability(
        ac_map=ac_map,
        grouping=grouping,
        group_results=group_results,
        mode="attach",
    )

    out = {
        "story": story,
        "ac_map": ac_map,
        "grouping": grouping,
        "group_results": group_results,
        "trace": trace,
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": model,
            "ac_count_selected": len(ac_map),
            "group_count": 1,
            "total_tasks": len(tasks),
            "fallback": True,
            "fallback_reason": "failsafe_taskgen_used",
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[OK] wrote: {output_path} acs={len(ac_map)} groups=1 total_tasks={len(tasks)} fallback=True")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", default="tests/fixtures/login_us001.json")
    p.add_argument("-o", "--output", default="out_grouped.json")

    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--score", type=int, default=50)

    p.add_argument("--start", type=int, default=1)
    p.add_argument("--limit", type=int, default=0)

    p.add_argument("--max-ac-per-group", type=int, default=10)
    p.add_argument("--target-groups-min", type=int, default=8)
    p.add_argument("--target-groups-max", type=int, default=12)
    p.add_argument("--max-groups", type=int, default=15)
    p.add_argument("--min-group-size", type=int, default=3)

    p.add_argument("--max-ac-per-task", type=int, default=2)
    p.add_argument("--max-repairs", type=int, default=2)

    # ✅ new: 並列数
    p.add_argument("--workers", type=int, default=4)

    args = p.parse_args()

    input_obj = _load_json(args.input)
    story, all_acs = extract_story_and_acs(input_obj)
    if not all_acs:
        raise RuntimeError("No acceptance_criteria found in input.")

    selected_acs = _select_range(all_acs, start=args.start, limit=args.limit)
    ac_map = build_ac_map(selected_acs, ac_prefix="AC")

    tuned = _auto_tune_grouping_policy(
        n_acs=len(ac_map),
        max_ac_per_group=args.max_ac_per_group,
        target_groups_min=args.target_groups_min,
        target_groups_max=args.target_groups_max,
        max_groups=args.max_groups,
        min_group_size=args.min_group_size,
    )

    # -------------------------
    # 1) grouping
    # -------------------------
    try:
        grouping = cluster_acs(
            model=args.model,
            story=story,
            ac_map=ac_map,
            max_ac_per_group=tuned["max_ac_per_group"],
            target_groups_min=tuned["target_groups_min"],
            target_groups_max=tuned["target_groups_max"],
            max_groups=tuned["max_groups"],
            min_group_size=tuned["min_group_size"],
            max_repairs=int(args.max_repairs),
        )
    except Exception:
        return _make_failsafe_output(
            story=story,
            ac_map=ac_map,
            tuned_policy=tuned,
            output_path=args.output,
            model=args.model,
        )

    if not isinstance(grouping, dict):
        return _make_failsafe_output(
            story=story,
            ac_map=ac_map,
            tuned_policy=tuned,
            output_path=args.output,
            model=args.model,
        )

    grouping.setdefault("meta", {})
    grouping["meta"].setdefault("policy_used", tuned)
    groups = grouping.get("groups", [])
    if not isinstance(groups, list) or not groups:
        return _make_failsafe_output(
            story=story,
            ac_map=ac_map,
            tuned_policy=tuned,
            output_path=args.output,
            model=args.model,
        )

    if bool((grouping.get("meta") or {}).get("fallback")):
        return _make_failsafe_output(
            story=story,
            ac_map=ac_map,
            tuned_policy=tuned,
            output_path=args.output,
            model=args.model,
        )

    # -------------------------
    # 2) taskgen per group (PARALLEL)
    # -------------------------
    import concurrent.futures

    max_tasks_per_ac = max_tasks_from_score(int(args.score))
    workers = max(1, int(args.workers))

    def _taskgen_one_group(g: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return generate_tasks_for_group(
                model=args.model,
                story=story,
                group=g,
                ac_map=ac_map,
                max_ac_per_task=int(args.max_ac_per_task),
                max_tasks_per_ac=int(max_tasks_per_ac),
                max_repairs=int(args.max_repairs),
            )
        except Exception as e:
            g_ac_ids = g.get("ac_ids") or []
            if not isinstance(g_ac_ids, list):
                g_ac_ids = []
            sub_ac_map = {aid: ac_map[aid] for aid in g_ac_ids if aid in ac_map}
            tasks = ac_map_to_min_tasks(sub_ac_map)

            return {
                "group_id": g.get("group_id", "G??"),
                "tasks": tasks,
                "meta": {
                    "mode": "failsafe_group",
                    "error": f"{type(e).__name__}: {e}",
                },
            }

    indexed_groups = [(i, g) for i, g in enumerate(groups) if isinstance(g, dict)]
    results_by_index: Dict[int, Dict[str, Any]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        future_map = {ex.submit(_taskgen_one_group, g): i for i, g in indexed_groups}
        for fut in concurrent.futures.as_completed(future_map):
            i = future_map[fut]
            results_by_index[i] = fut.result()

    group_results: List[Dict[str, Any]] = []
    total_tasks = 0
    for i, _g in indexed_groups:
        gr = results_by_index.get(i) or {"group_id": "G??", "tasks": [], "meta": {"mode": "empty"}}
        group_results.append(gr)
        tasks = gr.get("tasks", [])
        if isinstance(tasks, list):
            total_tasks += len(tasks)

    # ✅ traceability (NEW)
    trace = enforce_ac_traceability(
        ac_map=ac_map,
        grouping=grouping,
        group_results=group_results,
        mode="attach",
    )

    # -------------------------
    # 3) output
    # -------------------------
    out: Dict[str, Any] = {
        "story": story,
        "ac_map": ac_map,
        "grouping": grouping,
        "group_results": group_results,
        "trace": trace,  # ✅ NEW
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": args.model,
            "score": int(args.score),
            "max_tasks_per_ac": int(max_tasks_per_ac),
            "max_ac_per_group": int(tuned["max_ac_per_group"]),
            "target_groups": [int(tuned["target_groups_min"]), int(tuned["target_groups_max"])],
            "max_groups": int(tuned["max_groups"]),
            "min_group_size": int(tuned["min_group_size"]),
            "max_ac_per_task": int(args.max_ac_per_task),
            "max_repairs": int(args.max_repairs),
            "workers": int(workers),
            "ac_count_selected": len(selected_acs),
            "group_count": len(groups),
            "total_tasks": int(total_tasks),
            "fallback": False,
            "fallback_reason": "",
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(
        f"[OK] wrote: {args.output} "
        f"acs={len(selected_acs)} groups={len(groups)} total_tasks={total_tasks} "
        f"fallback={out['meta']['fallback']} workers={workers}"
    )


if __name__ == "__main__":
    main()