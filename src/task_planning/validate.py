# src/task_planning/validate.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple

REQUIRED_TASK_KEYS = [
    "title",
    "category",
    "subcategory",
    "status",
    "priority",
    "estimate_hours",
    "related_task_titles",
    "description",
]


def validate_tasks(tasks_obj: Dict[str, Any], *, max_tasks_per_ac: int) -> Tuple[bool, List[str]]:
    """
    1ACぶんの生成物を検証する:
      {"tasks": [ ...task... ]}
    """
    errors: List[str] = []

    tasks = tasks_obj.get("tasks")
    if not isinstance(tasks, list) or len(tasks) == 0:
        return False, ["tasks must be a non-empty list"]

    if max_tasks_per_ac > 0 and len(tasks) > max_tasks_per_ac:
        errors.append(f"tasks exceeds max_tasks_per_ac ({len(tasks)} > {max_tasks_per_ac})")

    for t, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"tasks[{t}] must be an object")
            continue

        for k in REQUIRED_TASK_KEYS:
            if k not in task:
                errors.append(f"tasks[{t}].{k} is missing")

        if not str(task.get("title", "")).strip():
            errors.append(f"tasks[{t}].title is empty")
        if not str(task.get("description", "")).strip():
            errors.append(f"tasks[{t}].description is empty")

        eh = task.get("estimate_hours")
        if not isinstance(eh, (int, float)):
            errors.append(f"tasks[{t}].estimate_hours must be number")
        else:
            if not (1 <= float(eh) <= 4):
                errors.append(f"tasks[{t}].estimate_hours must be 1-4 (got {eh})")

        rtt = task.get("related_task_titles")
        if not isinstance(rtt, list):
            errors.append(f"tasks[{t}].related_task_titles must be list")

    return (len(errors) == 0), errors


def validate_result(result: Dict[str, Any], *, max_tasks_per_ac: int) -> Tuple[bool, List[str]]:
    """
    pipeline全体の出力を検証する:
      {"items":[{"ac_index":..,"ac_text":..,"tasks":[...]}]}
    """
    errors: List[str] = []

    items = result.get("items")
    if not isinstance(items, list):
        return False, ["result.items must be a list"]

    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"items[{i}] must be an object")
            continue

        if "ac_index" not in item:
            errors.append(f"items[{i}].ac_index is missing")
        if not str(item.get("ac_text", "")).strip():
            errors.append(f"items[{i}].ac_text is empty")

        tasks_obj = {"tasks": item.get("tasks")}
        ok, errs = validate_tasks(tasks_obj, max_tasks_per_ac=max_tasks_per_ac)
        if not ok:
            errors.extend([f"items[{i}]." + e for e in errs])

    return (len(errors) == 0), errors