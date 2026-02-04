# src/task_planning/grouping/feasibility.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EffectiveGrouping:
    target_min: int
    target_max: int
    max_groups: int
    min_group_size: int
    max_feasible_groups: int
    relaxations_applied: List[str]


def compute_effective_grouping(
    *,
    n_acs: int,
    requested_target_min: int,
    requested_target_max: int,
    requested_max_groups: int,
    min_group_size: int,
) -> EffectiveGrouping:
    # defensive
    n = max(0, int(n_acs))
    mgs = max(1, int(min_group_size))

    max_feasible_groups = max(1, n // mgs)  # floor(N/min_group_size)

    # cap to feasible
    eff_target_min = min(int(requested_target_min), max_feasible_groups)
    eff_target_max = min(int(requested_target_max), max_feasible_groups)

    # keep ordering
    if eff_target_max < eff_target_min:
        eff_target_max = eff_target_min

    eff_max_groups = min(int(requested_max_groups), max_feasible_groups)

    relax: List[str] = []
    if eff_target_min != int(requested_target_min):
        relax.append("tier3_target_min_capped_by_feasibility")
    if eff_target_max != int(requested_target_max):
        relax.append("tier3_target_max_capped_by_feasibility")
    if eff_max_groups != int(requested_max_groups):
        relax.append("max_groups_capped_by_feasibility")

    return EffectiveGrouping(
        target_min=eff_target_min,
        target_max=eff_target_max,
        max_groups=eff_max_groups,
        min_group_size=mgs,
        max_feasible_groups=max_feasible_groups,
        relaxations_applied=relax,
    )