# src/task_planning/grouping/cluster_agent.py
from __future__ import annotations

from typing import Any, Dict, List

from .schema import (
    normalize_grouping_obj,
    validate_grouping,
    simple_fallback_grouping,
    DEFAULT_MAX_AC_PER_GROUP,
    DEFAULT_TARGET_GROUPS_MIN,
    DEFAULT_TARGET_GROUPS_MAX,
    DEFAULT_MAX_GROUPS,
    DEFAULT_MIN_GROUP_SIZE,
)
from ..llm import call_llm_json

from .cluster_support import (
    CLUSTER_SYSTEM,
    REPAIR_SYSTEM,
    build_cluster_prompt,
    build_repair_prompt,
    split_issues,
    policy_meta,
    derive_effective_policy,
    build_self_check_py,
)


def cluster_acs(
    *,
    model: str,
    story: Dict[str, Any],
    ac_map: Dict[str, str],
    max_ac_per_group: int = DEFAULT_MAX_AC_PER_GROUP,
    target_groups_min: int = DEFAULT_TARGET_GROUPS_MIN,
    target_groups_max: int = DEFAULT_TARGET_GROUPS_MAX,
    max_groups: int = DEFAULT_MAX_GROUPS,
    min_group_size: int = DEFAULT_MIN_GROUP_SIZE,
    max_repairs: int = 1,
) -> Dict[str, Any]:

    eff = derive_effective_policy(
        n_acs=len(ac_map),
        target_groups_min=target_groups_min,
        target_groups_max=target_groups_max,
        max_groups=max_groups,
        min_group_size=min_group_size,
    )

    prompt = build_cluster_prompt(
        story=story,
        ac_map=ac_map,
        max_ac_per_group=max_ac_per_group,
        effective_target_min=eff.target_min,
        effective_target_max=eff.target_max,
        effective_max_groups=eff.max_groups,
        min_group_size=eff.min_group_size,
    )

    last_err = ""
    warnings: List[str] = []
    grouping_obj: Dict[str, Any] = {}

    # initial
    try:
        raw = call_llm_json(
            model=model,
            messages=[
                {"role": "system", "content": CLUSTER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=1800,
        )
        grouping_obj = normalize_grouping_obj(raw)
    except Exception as e:
        last_err = f"initial_call_failed: {type(e).__name__}: {e}"
        grouping_obj = {}

    # validate + repair
    for attempt in range(0, int(max_repairs) + 1):
        if not grouping_obj:
            break

        ok, issues = validate_grouping(
            grouping_obj,
            ac_map=ac_map,
            max_ac_per_group=max_ac_per_group,
            target_groups_min=eff.target_min,
            target_groups_max=eff.target_max,
            max_groups=eff.max_groups,
            min_group_size=eff.min_group_size,
            require_log_split=True,
        )

        hard, warn = split_issues(issues)
        warnings = warn

        if ok and not hard:
            groups = grouping_obj.get("groups") or []
            if not isinstance(groups, list):
                groups = []

            grouping_obj.setdefault("meta", {})
            grouping_obj["meta"].update(
                {
                    "fallback": False,
                    "repairs_used": attempt,
                    "warnings": warnings,
                    "policy": policy_meta(
                        max_ac_per_group=max_ac_per_group,
                        target_groups_min=eff.target_min,
                        target_groups_max=eff.target_max,
                        max_groups=eff.max_groups,
                        min_group_size=eff.min_group_size,
                    ),
                    "self_check": build_self_check_py(
                        groups=groups,
                        ac_map=ac_map,
                        max_ac_per_group=max_ac_per_group,
                        min_group_size=eff.min_group_size,
                        relaxations_applied=eff.relaxations,
                    ),
                }
            )
            return grouping_obj

        last_err = "; ".join(hard) if hard else "; ".join(issues)
        if attempt >= int(max_repairs):
            break

        try:
            issues_text = "\n".join([f"- {x}" for x in hard]) if hard else "- (none)"
            repair_prompt = build_repair_prompt(issues_text=issues_text, grouping_obj=grouping_obj)

            raw2 = call_llm_json(
                model=model,
                messages=[
                    {"role": "system", "content": REPAIR_SYSTEM},
                    {"role": "user", "content": repair_prompt},
                ],
                temperature=0.0,
                max_tokens=1800,
            )
            grouping_obj = normalize_grouping_obj(raw2)
        except Exception as e:
            last_err = f"repair_call_failed: {type(e).__name__}: {e}"
            break

    # fallback
    fb = simple_fallback_grouping(
        ac_map,
        max_ac_per_group=max_ac_per_group,
        min_group_size=eff.min_group_size,
    )

    groups = fb.get("groups") or []
    if not isinstance(groups, list):
        groups = []

    fb.setdefault("meta", {})
    fb["meta"].update(
        {
            "fallback": True,
            "reason": f"cluster_failed: {last_err}",
            "warnings": warnings,
            "policy": policy_meta(
                max_ac_per_group=max_ac_per_group,
                target_groups_min=eff.target_min,
                target_groups_max=eff.target_max,
                max_groups=eff.max_groups,
                min_group_size=eff.min_group_size,
            ),
            "self_check": build_self_check_py(
                groups=groups,
                ac_map=ac_map,
                max_ac_per_group=max_ac_per_group,
                min_group_size=eff.min_group_size,
                relaxations_applied=eff.relaxations + ["fallback_used"],
            ),
        }
    )
    return fb