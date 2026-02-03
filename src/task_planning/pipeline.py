from typing import Any, Dict, List

from .llm import call_llm_json
from .validate import validate_tasks  # ★ここが変更点（validate_result じゃない）


PLAN_PROMPT = """You are a senior software engineer.
Read ONE acceptance criterion (AC) and design small work units that each finish in 1–4 hours.

Rules:
- Output JSON only.
- Create 2–6 work_units.
- Each work_unit must be actionable and specific (file/area/API/db/test).
- Each work_unit must include a short "surface" tag: one of
  ["util","api","db","integration","test","config","doc","security","perf","fe"].

JSON schema:
{
  "work_units": [
    {
      "title": "...",
      "surface": "util|api|db|integration|test|config|doc|security|perf|fe",
      "description": "...",
      "estimate_hours": 1-4,
      "dependencies": ["<other work_unit title>", ...]
    }
  ]
}
"""

GEN_PROMPT = """You are generating company-ready tasks from work units.
Output JSON only.

Task constraints:
- Each task must be doable in 1-4 hours.
- The task must include concrete changes (where/what) and acceptance checks.
- related_task_titles should reference dependencies by title.

JSON schema:
{
  "tasks": [
    {
      "title": "...",
      "category": "Task",
      "subcategory": "[Code][BE]|[Code][FE]|[Code][DB]|[Test]|[Doc]",
      "status": "Todo",
      "priority": "Low|Medium|High",
      "estimate_hours": 1-4,
      "assignee": "",
      "related_task_titles": ["...", ...],
      "period": "",
      "description": "Goal...\\nChanges...\\nAcceptance checks..."
    }
  ]
}
"""

REPAIR_PROMPT = """You will fix the tasks based on issues.
Output JSON only with the same schema as tasks.
Make tasks smaller and more specific if needed.
"""


def plan_one_ac(model: str, ac_text: str) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": PLAN_PROMPT},
        {"role": "user", "content": f"AC: {ac_text}"},
    ]
    return call_llm_json(model=model, messages=messages, temperature=0.0, max_tokens=1200)


def _normalize_tasks(tasks: Any, max_tasks_per_ac: int) -> Dict[str, Any]:
    if not isinstance(tasks, list):
        tasks = []

    fixed: List[Dict[str, Any]] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue

        t.setdefault("category", "Task")
        t.setdefault("status", "Todo")
        t.setdefault("priority", "Medium")
        t.setdefault("assignee", "")
        t.setdefault("related_task_titles", [])
        t.setdefault("period", "")
        t.setdefault("subcategory", "[Code][BE]")

        # estimate_hours 最終防衛（1-4に丸める）
        try:
            h = int(t.get("estimate_hours", 2))
        except Exception:
            h = 2
        t["estimate_hours"] = min(4, max(1, h))

        fixed.append(t)

    return {"tasks": fixed[:max_tasks_per_ac]}


def generate_from_plan(
    model: str,
    ac_text: str,
    plan: Dict[str, Any],
    max_tasks_per_ac: int,
) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": GEN_PROMPT},
        {
            "role": "user",
            "content": f"AC: {ac_text}\nPlan JSON:\n{plan}\nMax tasks: {max_tasks_per_ac}",
        },
    ]
    out = call_llm_json(model=model, messages=messages, temperature=0.1, max_tokens=1800)
    return _normalize_tasks(out.get("tasks"), max_tasks_per_ac)


def repair_tasks(
    model: str,
    ac_text: str,
    tasks_obj: Dict[str, Any],
    issues: List[str],
    max_tasks_per_ac: int,
) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": REPAIR_PROMPT},
        {
            "role": "user",
            "content": (
                f"AC: {ac_text}\n"
                f"Issues:\n- " + "\n- ".join([str(x) for x in issues]) + "\n\n"
                f"Current tasks JSON:\n{tasks_obj}\n"
                f"Max tasks: {max_tasks_per_ac}"
            ),
        },
    ]
    out = call_llm_json(model=model, messages=messages, temperature=0.1, max_tokens=1800)
    return _normalize_tasks(out.get("tasks"), max_tasks_per_ac)


def run_pipeline(
    *,
    model: str,
    acceptance_criteria: List[str],
    max_tasks_per_ac: int = 6,
    max_repairs: int = 1,
) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []

    for idx, ac in enumerate(acceptance_criteria, start=1):
        try:
            plan = plan_one_ac(model, ac)
            gen = generate_from_plan(model, ac, plan, max_tasks_per_ac=max_tasks_per_ac)

            # ★ここが変更点：validate_result ではなく validate_tasks
            ok, issues = validate_tasks(gen, max_tasks_per_ac=max_tasks_per_ac)

            repairs = 0
            while (not ok) and repairs < max_repairs:
                gen = repair_tasks(model, ac, gen, issues, max_tasks_per_ac=max_tasks_per_ac)
                ok, issues = validate_tasks(gen, max_tasks_per_ac=max_tasks_per_ac)
                repairs += 1

            items.append(
                {
                    "ac_index": idx,
                    "ac_text": ac,
                    "plan": plan,
                    "validate": {"pass": bool(ok), "issues": issues},
                    "tasks": gen.get("tasks", [])[:max_tasks_per_ac],
                }
            )

        except Exception as e:
            items.append(
                {
                    "ac_index": idx,
                    "ac_text": ac,
                    "error": f"{type(e).__name__}: {e}",
                    "tasks": [],
                }
            )

    return {"items": items}