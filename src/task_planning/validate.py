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

def validate_tasks_obj(tasks_obj: Dict[str, Any], *, max_tasks: int) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    tasks = tasks_obj.get("tasks")
    if not isinstance(tasks, list) or len(tasks) == 0:
        return False, ["tasks must be a non-empty list"]

    if max_tasks > 0 and len(tasks) > max_tasks:
        errors.append(f"tasks exceeds max_tasks ({len(tasks)} > {max_tasks})")

    for i, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"tasks[{i}] must be an object")
            continue

        for k in REQUIRED_TASK_KEYS:
            if k not in task:
                errors.append(f"tasks[{i}].{k} is missing")

        if not str(task.get("title", "")).strip():
            errors.append(f"tasks[{i}].title is empty")
        if not str(task.get("description", "")).strip():
            errors.append(f"tasks[{i}].description is empty")

        eh = task.get("estimate_hours")
        if not isinstance(eh, (int, float)):
            errors.append(f"tasks[{i}].estimate_hours must be number")
        else:
            if not (1 <= float(eh) <= 4):
                errors.append(f"tasks[{i}].estimate_hours must be 1-4 (got {eh})")

        rtt = task.get("related_task_titles")
        if not isinstance(rtt, list):
            errors.append(f"tasks[{i}].related_task_titles must be list")

        desc = str(task.get("description", ""))
        for kw in ["Goal:", "Changes:", "Acceptance checks:"]:
            if kw not in desc:
                errors.append(f"tasks[{i}].description should include '{kw}'")

    return (len(errors) == 0), errors
