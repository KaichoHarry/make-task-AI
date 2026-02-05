# src/task_planning/grouping/policy.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroupingPolicy:
    max_ac_per_group: int = 10
    target_groups_min: int = 8
    target_groups_max: int = 12
    max_groups: int = 15
    min_group_size: int = 3
    log_groups_independent: bool = True


def derive_grouping_policy(n_acs: int) -> GroupingPolicy:
    # max_ac_per_group は基本 10
    max_ac_per_group = 10

    # orphan禁止(min_group_size) は AC数で可変
    if n_acs <= 8:
        min_group_size = 2
    elif n_acs <= 20:
        min_group_size = 3
    else:
        min_group_size = 4

    # 作り得る最大グループ数（上限）
    max_groups_cap = max(1, n_acs // min_group_size)

    # 目標レンジ（8-12）を「実現可能範囲」に丸める
    target_min = min(8, max_groups_cap)
    target_max = min(12, max_groups_cap)

    max_groups = min(15, max_groups_cap)

    return GroupingPolicy(
        max_ac_per_group=max_ac_per_group,
        target_groups_min=target_min,
        target_groups_max=target_max,
        max_groups=max_groups,
        min_group_size=min_group_size,
        log_groups_independent=True,
    )