# src/task_planning/grouped_taskgen/taskgen_agent.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from ..llm import call_llm_json
from ..validate import validate_tasks_obj


ALLOWED_SUBCATS = {"[Code][BE]", "[Code][FE]", "[Code][DB]", "[Test]", "[Doc]", "[Ops]"}


GROUP_TASKGEN_SYSTEM = """You are a senior software engineer.
You create implementation tasks from a GROUP of Acceptance Criteria (ACs).
Output JSON only. No markdown. No extra text.
"""

GROUP_TASKGEN_USER = """Create tasks for this AC group.

Hard constraints:
- Output JSON only with schema: {{"tasks":[...]}}.
- Task count must be between {min_tasks} and {max_tasks}.
- Each task must be 1-4 hours (integer).
- Each task MUST include "ac_ids": list of AC IDs that this task covers.
- Each task may cover 1..{max_ac_per_task} ACs (avoid messy mixing).
- Coverage rule: every AC ID in this group must appear in at least one task's ac_ids.
- Prefer stable grouping by implementation touchpoint (same module/endpoint/middleware/db/etc).
- Category must be "Task", status must be "Todo".
- Subcategory must be one of: [Code][BE], [Code][FE], [Code][DB], [Test], [Doc], [Ops].
- Titles must be concrete (avoid "refine/clarify/define").

Task schema:
{{
  "tasks":[
    {{
      "title":"...",
      "category":"Task",
      "subcategory":"[Code][BE]|[Code][FE]|[Code][DB]|[Test]|[Doc]|[Ops]",
      "status":"Todo",
      "priority":"Low|Medium|High",
      "estimate_hours":2,
      "ac_ids":["AC-001","AC-002"],
      "related_task_titles":[],
      "description":"Goal:...\\nChanges:...\\nAcceptance checks:..."
    }}
  ]
}}

Story (context):
{story_json}

AC group:
group_id: {group_id}
label: {group_label}
ac_ids: {ac_ids_json}

AC texts (ac_map subset):
{ac_subset_json}
"""

REPAIR_SYSTEM = """You fix tasks based on issues.
Output JSON only. No extra text.
"""

REPAIR_USER = """Fix the tasks.

Hard constraints:
- JSON only: {{"tasks":[...]}}.
- Task count must be between {min_tasks} and {max_tasks}.
- Each task must be 1-4 hours (integer).
- Each task MUST include ac_ids (1..{max_ac_per_task} ids).
- Coverage: every AC must appear at least once across tasks.
- category="Task", status="Todo"
- subcategory must be in allowed set.

Issues:
{issues_text}

Current tasks JSON:
{tasks_json}
"""


def _normalize_tasks(tasks: Any, *, max_tasks: int) -> Dict[str, Any]:
    if not isinstance(tasks, list):
        tasks = []

    fixed: List[Dict[str, Any]] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue

        t.setdefault("category", "Task")
        t.setdefault("status", "Todo")
        t.setdefault("priority", "Medium")
        t.setdefault("related_task_titles", [])
        t.setdefault("description", "Goal:...\nChanges:...\nAcceptance checks:...")

        # subcategory normalize
        sub = str(t.get("subcategory") or "[Code][BE]").strip()
        if "|" in sub:
            sub = sub.split("|", 1)[0].strip()
        if sub not in ALLOWED_SUBCATS:
            sub = "[Code][BE]"
        t["subcategory"] = sub

        # estimate_hours clamp
        try:
            h = int(t.get("estimate_hours", 2))
        except Exception:
            h = 2
        t["estimate_hours"] = min(4, max(1, h))

        # ac_ids normalize
        ac_ids = t.get("ac_ids", [])
        if not isinstance(ac_ids, list):
            ac_ids = []
        ac_ids = [str(x).strip() for x in ac_ids if str(x).strip()]
        t["ac_ids"] = ac_ids

        # title non-empty
        t["title"] = str(t.get("title", "")).strip()

        fixed.append(t)

    return {"tasks": fixed[:max_tasks]}


def _validate_group_coverage(
    tasks_obj: Dict[str, Any],
    *,
    group_ac_ids: List[str],
    max_ac_per_task: int,
) -> Tuple[bool, List[str]]:
    issues: List[str] = []

    tasks = tasks_obj.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return False, ["tasks must be a non-empty list"]

    group_set = set(group_ac_ids)
    seen: List[str] = []

    for i, t in enumerate(tasks, start=1):
        if not isinstance(t, dict):
            issues.append(f"tasks[{i}] must be object")
            continue

        ac_ids = t.get("ac_ids")
        if not isinstance(ac_ids, list) or not ac_ids:
            issues.append(f"tasks[{i}].ac_ids must be non-empty list")
            continue

        if len(ac_ids) > int(max_ac_per_task):
            issues.append(f"tasks[{i}].ac_ids exceeds max_ac_per_task ({len(ac_ids)} > {max_ac_per_task})")

        for a in ac_ids:
            if a not in group_set:
                issues.append(f"tasks[{i}].ac_ids contains unknown id: {a}")
            else:
                seen.append(a)

    missing = [a for a in group_ac_ids if a not in set(seen)]
    if missing:
        issues.append(f"coverage missing ACs: {missing}")

    return (len(issues) == 0), issues


def generate_tasks_for_group(
    *,
    model: str,
    story: Dict[str, Any],
    group: Dict[str, Any],
    ac_map: Dict[str, str],
    max_ac_per_task: int = 2,
    max_tasks_per_ac: int = 2,
    max_repairs: int = 1,
) -> Dict[str, Any]:
    """
    group (dict):
      - group_id
      - label
      - ac_ids: list[str]
    output:
      - group_id, label, ac_ids, tasks, validate/meta
    """
    group_id = str(group.get("group_id", "") or "").strip() or "G??"
    label = str(group.get("label", "") or "").strip()
    ac_ids = group.get("ac_ids", [])
    if not isinstance(ac_ids, list) or not ac_ids:
        return {
            "group_id": group_id,
            "label": label,
            "ac_ids": [],
            "error": "group.ac_ids is empty",
            "tasks": [],
        }

    group_ac_ids = [str(x).strip() for x in ac_ids if str(x).strip()]
    ac_subset = {a: ac_map.get(a, "") for a in group_ac_ids}

    # 目標: 1ACあたり最小1タスク、最大 max_tasks_per_ac タスク
    min_tasks = max(1, len(group_ac_ids))
    max_tasks = max(min_tasks, min(20, int(len(group_ac_ids) * float(max_tasks_per_ac))))

    story_json = json.dumps(story, ensure_ascii=False)
    ac_ids_json = json.dumps(group_ac_ids, ensure_ascii=False)
    ac_subset_json = json.dumps(ac_subset, ensure_ascii=False, indent=2)

    prompt = GROUP_TASKGEN_USER.format(
        min_tasks=int(min_tasks),
        max_tasks=int(max_tasks),
        max_ac_per_task=int(max_ac_per_task),
        story_json=story_json,
        group_id=group_id,
        group_label=label,
        ac_ids_json=ac_ids_json,
        ac_subset_json=ac_subset_json,
    )

    raw = call_llm_json(
        model=model,
        messages=[
            {"role": "system", "content": GROUP_TASKGEN_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1800,
    )
    tasks_obj = _normalize_tasks(raw.get("tasks", []), max_tasks=int(max_tasks))

    # validate (既存validate + group coverage)
    ok1, issues1 = validate_tasks_obj(tasks_obj, max_tasks=int(max_tasks))
    ok2, issues2 = _validate_group_coverage(tasks_obj, group_ac_ids=group_ac_ids, max_ac_per_task=int(max_ac_per_task))

    repairs = 0
    issues = issues1 + issues2
    ok = bool(ok1 and ok2)

    while (not ok) and repairs < int(max_repairs):
        issues_text = "\n".join([f"- {x}" for x in issues])
        tasks_json = json.dumps(tasks_obj, ensure_ascii=False, indent=2)

        rep_prompt = REPAIR_USER.format(
            min_tasks=int(min_tasks),
            max_tasks=int(max_tasks),
            max_ac_per_task=int(max_ac_per_task),
            issues_text=issues_text,
            tasks_json=tasks_json,
        )
        rep_raw = call_llm_json(
            model=model,
            messages=[
                {"role": "system", "content": REPAIR_SYSTEM},
                {"role": "user", "content": rep_prompt},
            ],
            temperature=0.0,
            max_tokens=1800,
        )
        tasks_obj = _normalize_tasks(rep_raw.get("tasks", []), max_tasks=int(max_tasks))

        ok1, issues1 = validate_tasks_obj(tasks_obj, max_tasks=int(max_tasks))
        ok2, issues2 = _validate_group_coverage(tasks_obj, group_ac_ids=group_ac_ids, max_ac_per_task=int(max_ac_per_task))
        issues = issues1 + issues2
        ok = bool(ok1 and ok2)
        repairs += 1

    return {
        "group_id": group_id,
        "label": label,
        "ac_ids": group_ac_ids,
        "validate": {"pass": ok, "issues": issues, "repairs_used": repairs},
        "tasks": tasks_obj.get("tasks", []),
    }