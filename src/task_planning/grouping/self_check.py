# src/task_planning/grouping/self_check.py
from __future__ import annotations

from typing import Any, Dict, List


def build_self_check(
    *,
    groups: List[Dict[str, Any]],
    ac_map: Dict[str, str],
    max_ac_per_group: int,
    min_group_size: int,
    relaxations_applied: List[str],
) -> Dict[str, Any]:
    all_ids = list(ac_map.keys())
    all_set = set(all_ids)

    assigned: List[str] = []
    group_sizes: List[int] = []
    orphan_groups: List[List[Any]] = []

    for g in groups or []:
        if not isinstance(g, dict):
            continue
        ac_ids = g.get("ac_ids") or []
        if not isinstance(ac_ids, list):
            ac_ids = []
        ac_ids = [str(x) for x in ac_ids if isinstance(x, str)]
        assigned.extend(ac_ids)
        sz = len(ac_ids)
        group_sizes.append(sz)
        if sz < int(min_group_size):
            orphan_groups.append([g.get("group_id", "?"), sz])

    counts: Dict[str, int] = {}
    for a in assigned:
        counts[a] = counts.get(a, 0) + 1
    duplicate_ids = sorted([a for a, c in counts.items() if c >= 2])

    assigned_set = set(assigned)
    missing_ids = [a for a in all_ids if a not in assigned_set]
    unknown_ids = [a for a in assigned if a not in all_set]

    # cheap log split check (real check is validate_grouping)
    def _kind(ac_text: str) -> str:
        t = (ac_text or "").lower()
        if "audit" in t or "tamper" in t or "改ざん" in t or "耐改ざん" in t:
            return "audit"
        if "security log" in t or "セキュリティログ" in t or "brute" in t:
            return "security"
        if "log" in t or "ログ" in t:
            return "log"
        return "other"

    log_split_ok = True
    for g in groups or []:
        if not isinstance(g, dict):
            continue
        ac_ids = g.get("ac_ids") or []
        if not isinstance(ac_ids, list):
            continue
        kinds = set()
        for a in ac_ids:
            if a in ac_map:
                kinds.add(_kind(ac_map[a]))
        if "audit" in kinds and "security" in kinds:
            log_split_ok = False
            break

    return {
        "n_acs": len(all_ids),
        "groups_count": len([g for g in groups if isinstance(g, dict)]),
        "group_sizes": group_sizes,
        "max_ac_per_group": int(max_ac_per_group),
        "min_group_size": int(min_group_size),
        "missing_ids": missing_ids,
        "duplicate_ids": duplicate_ids,
        "unknown_ids": unknown_ids,
        "orphan_groups": orphan_groups,
        "log_split_ok": bool(log_split_ok),
        "relaxations_applied": list(relaxations_applied or []),
    }