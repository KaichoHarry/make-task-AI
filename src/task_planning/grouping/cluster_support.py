# src/task_planning/grouping/cluster_support.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


# =========================
# Prompts
# =========================
CLUSTER_SYSTEM = """You are a senior software engineer and requirements analyst.
You cluster Acceptance Criteria (ACs) into stable implementation groups.

You MUST follow priority tiers and relaxation rules when constraints conflict.
Return JSON only. No markdown. No extra text.
"""

CLUSTER_USER = """Cluster ACs into implementation groups for task generation.

You MUST follow this decision policy exactly.

====================
Priority Tiers
====================
Tier 0 (ABSOLUTE, never violate):
- Output JSON only with schema: {{"groups":[...], "meta": {{...}}}}.
- Assign EVERY AC ID exactly once (no missing, no duplicates).
- Do NOT invent AC IDs; use only IDs provided in ac_map.
- groups[*].ac_ids must be non-empty list[str].
- group_id must be unique.

Tier 1 (VERY IMPORTANT, violate only if impossible):
- Max ACs per group <= {max_ac_per_group}.
- Logging separation:
  - Security logs must be in their own group(s) (tag: "log_security")
  - Audit/tamper-evident logs must be in their own group(s) (tag: "log_audit")
  - Do NOT mix security + audit in the same group.

Tier 2 (IMPORTANT, relax if it conflicts with feasibility):
- Orphan groups (size 1-2) are NOT allowed. Absorb them into closest groups.

Tier 3 (SOFT GOAL, relax freely):
- Total groups should be within target range {target_min}..{target_max}.
  If impossible, choose a feasible group count that minimizes risk of messy mixing.

====================
Relaxation / If-Then Rules
====================
You MUST proactively avoid fallback-worthy states by relaxing lower tiers.

Definitions:
- N = number of ACs (len(ac_map))
- min_group_size = {min_group_size}

Feasibility checks you must perform BEFORE finalizing:
1) max_feasible_groups = floor(N / min_group_size) (at least 1)

2) If max_feasible_groups < {target_min}:
   - Relax Tier 3 first: set target range to [1 .. max_feasible_groups]
   - Keep Tier 2 (no orphans) if still feasible.

3) If Tier 2 (no orphans) causes conflict:
   - You may relax Tier 2 ONLY as a last resort by allowing size=2 groups,
     but still try to absorb them if possible without violating Tier 1.

4) If you cannot satisfy both Tier 1 max_ac_per_group and Tier 2 no-orphans,
   prioritize Tier 1 and absorb orphans by merging while staying <= max_ac_per_group.

====================
Grouping Principle (STRICT)
====================
Group by same implementation touchpoint, NOT vague topic.

====================
Output Schema
====================
Return JSON:
{{
  "groups": [
    {{
      "group_id": "G01",
      "label": "short name",
      "tags": ["optional", "..."],
      "rationale": "1-2 sentences why these ACs belong together",
      "ac_ids": ["AC-001-01", "AC-001-02"]
    }}
  ],
  "meta": {{
    "self_check": {{
      "n_acs": 0,
      "groups_count": 0,
      "group_sizes": [0,0],
      "max_ac_per_group": {max_ac_per_group},
      "min_group_size": {min_group_size},
      "missing_ids": [],
      "duplicate_ids": [],
      "unknown_ids": [],
      "orphan_groups": [],
      "log_split_ok": true,
      "relaxations_applied": ["..."]
    }}
  }}
}}

Input:
story: {story_json}
ac_map: {ac_map_json}
"""

REPAIR_SYSTEM = """You repair grouping JSON based on validation issues.
Use the same priority tiers + relaxation rules as in the clustering step.
Return JSON only. No extra text.
"""

REPAIR_USER = """Fix the grouping JSON to resolve validation issues.

Issues to fix (hard issues only):
{issues_text}

Current grouping JSON:
{grouping_json}

MANDATORY:
- Return the full JSON with {{"groups":[...], "meta":{{"self_check":{{...}}}}}}
"""


# =========================
# Issue split
# =========================
def split_issues(issues: List[str]) -> Tuple[List[str], List[str]]:
    hard: List[str] = []
    warn: List[str] = []
    for x in issues or []:
        if isinstance(x, str) and x.strip().lower().startswith("warning:"):
            warn.append(x.strip())
        else:
            hard.append(str(x).strip())
    return hard, warn


# =========================
# Policy meta + feasibility
# =========================
def policy_meta(
    *,
    max_ac_per_group: int,
    target_groups_min: int,
    target_groups_max: int,
    max_groups: int,
    min_group_size: int,
) -> Dict[str, Any]:
    return {
        "max_ac_per_group": int(max_ac_per_group),
        "target_groups": [int(target_groups_min), int(target_groups_max)],
        "max_groups": int(max_groups),
        "min_group_size": int(min_group_size),
        "log_split": True,
    }


@dataclass(frozen=True)
class EffectivePolicy:
    target_min: int
    target_max: int
    max_groups: int
    min_group_size: int
    relaxations: List[str]


def derive_effective_policy(
    *,
    n_acs: int,
    target_groups_min: int,
    target_groups_max: int,
    max_groups: int,
    min_group_size: int,
) -> EffectivePolicy:
    min_group_size_i = max(1, int(min_group_size))
    max_feasible_groups = max(1, int(n_acs) // min_group_size_i)

    tmin = int(target_groups_min)
    tmax = int(target_groups_max)
    relax: List[str] = []

    # cap by feasibility
    if tmin > max_feasible_groups:
        tmin = max_feasible_groups
        relax.append("tier3_target_min_capped_by_feasibility")
    if tmax > max_feasible_groups:
        tmax = max_feasible_groups
        relax.append("tier3_target_max_capped_by_feasibility")

    if tmax < tmin:
        tmax = tmin
        relax.append("tier3_target_range_collapsed")

    # if requested min is impossible, relax to [1..max_feasible]
    if int(target_groups_min) > max_feasible_groups:
        tmin = 1
        tmax = max_feasible_groups
        relax.append("tier3_target_range_adjusted")

    eff_max_groups = min(int(max_groups), max_feasible_groups)
    if eff_max_groups < int(max_groups):
        relax.append("max_groups_capped_by_feasibility")

    return EffectivePolicy(
        target_min=tmin,
        target_max=tmax,
        max_groups=eff_max_groups,
        min_group_size=min_group_size_i,
        relaxations=relax,
    )


# =========================
# Prompt builders
# =========================
def build_cluster_prompt(
    *,
    story: Dict[str, Any],
    ac_map: Dict[str, str],
    max_ac_per_group: int,
    effective_target_min: int,
    effective_target_max: int,
    effective_max_groups: int,
    min_group_size: int,
) -> str:
    story_json = json.dumps(story, ensure_ascii=False)
    ac_map_json = json.dumps(ac_map, ensure_ascii=False, indent=2)
    return CLUSTER_USER.format(
        max_ac_per_group=int(max_ac_per_group),
        target_min=int(effective_target_min),
        target_max=int(effective_target_max),
        max_groups=int(effective_max_groups),
        min_group_size=int(min_group_size),
        story_json=story_json,
        ac_map_json=ac_map_json,
    )


def build_repair_prompt(*, issues_text: str, grouping_obj: Dict[str, Any]) -> str:
    grouping_json = json.dumps(grouping_obj, ensure_ascii=False, indent=2)
    return REPAIR_USER.format(
        issues_text=issues_text,
        grouping_json=grouping_json,
    )


# =========================
# Self-check (Python authoritative)
# =========================
def build_self_check_py(
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

    def _kind(ac_text: str) -> str:
        t = (ac_text or "").lower()
        if "audit" in t or "tamper" in t or "改ざん" in t or "耐改ざん" in t:
            return "audit"
        if "security log" in t or "セキュリティログ" in t or "brute" in t or "ブルート" in t:
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