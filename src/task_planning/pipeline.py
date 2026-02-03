# src/task_planning/pipeline.py
from __future__ import annotations

import json
from typing import Any, Dict, List

from .llm import call_llm_json
from .validate import validate_tasks_obj
from .prompts import (
    PLAN_SYSTEM, PLAN_USER,
    GEN_SYSTEM, GEN_USER,
    REPAIR_SYSTEM, REPAIR_USER,
)

# ✅ subcategory 許可リスト（ここ以外はBEへ落とす）
ALLOWED_SUBCATS = {"[Code][BE]", "[Code][FE]", "[Code][DB]", "[Test]", "[Doc]", "[Ops]"}


def plan_one_ac(model: str, ac_text: str, max_tasks: int) -> Dict[str, Any]:
    return call_llm_json(
        model=model,
        messages=[
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": PLAN_USER.format(ac_text=ac_text, max_tasks=max_tasks)},
        ],
        temperature=0.0,
        max_tokens=1400,
    )


def _normalize_tasks(tasks: Any, max_tasks: int) -> Dict[str, Any]:
    # ✅ 事故防止：max_tasks を必ず int 化
    try:
        max_tasks_i = int(max_tasks)
    except Exception:
        max_tasks_i = 1
    if max_tasks_i <= 0:
        max_tasks_i = 1

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

        # ✅ subcategory：文字列化 → "|"除去 → 許可リスト以外はBEへ矯正
        sub = t.get("subcategory") or "[Code][BE]"
        sub = str(sub).strip()

        # 例: "[Code][BE]|[Doc]" → "[Code][BE]"
        if "|" in sub:
            sub = sub.split("|", 1)[0].strip()

        if not sub:
            sub = "[Code][BE]"

        # 例: "[Code][Validation]" などはBEへ落とす
        if sub not in ALLOWED_SUBCATS:
            sub = "[Code][BE]"

        t["subcategory"] = sub

        # estimate_hours 最終防衛（1-4に丸める）
        try:
            h = int(t.get("estimate_hours", 2))
        except Exception:
            h = 2
        t["estimate_hours"] = min(4, max(1, h))

        fixed.append(t)

    return {"tasks": fixed[:max_tasks_i]}


def generate_tasks(model: str, ac_text: str, plan: Dict[str, Any], max_tasks: int) -> Dict[str, Any]:
    plan_json = json.dumps(plan, ensure_ascii=False, indent=2)
    out = call_llm_json(
        model=model,
        messages=[
            {"role": "system", "content": GEN_SYSTEM},
            {"role": "user", "content": GEN_USER.format(ac_text=ac_text, plan_json=plan_json, max_tasks=max_tasks)},
        ],
        temperature=0.1,
        max_tokens=1800,
    )
    return _normalize_tasks(out.get("tasks", []), max_tasks=max_tasks)


def repair_tasks(model: str, issues: List[str], tasks_obj: Dict[str, Any], max_tasks: int) -> Dict[str, Any]:
    issues_text = "\n".join([f"- {x}" for x in issues])
    tasks_json = json.dumps(tasks_obj, ensure_ascii=False, indent=2)
    out = call_llm_json(
        model=model,
        messages=[
            {"role": "system", "content": REPAIR_SYSTEM},
            {"role": "user", "content": REPAIR_USER.format(
                issues_text=issues_text,
                tasks_json=tasks_json,
                max_tasks=max_tasks
            )},
        ],
        temperature=0.1,
        max_tokens=1800,
    )
    return _normalize_tasks(out.get("tasks", []), max_tasks=max_tasks)


def run_pipeline(
    *,
    model: str,
    acceptance_criteria: List[str],
    max_tasks_per_ac: int,
    max_repairs: int = 1,
    start_ac_index: int = 1,  # ✅ part実行でAC番号ズレない
) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []

    for offset, ac in enumerate(acceptance_criteria, start=0):
        ac_index = start_ac_index + offset  # ✅ 元のAC番号で出す
        try:
            plan = plan_one_ac(model, ac, max_tasks=max_tasks_per_ac)
            gen = generate_tasks(model, ac, plan, max_tasks=max_tasks_per_ac)

            ok, issues = validate_tasks_obj(gen, max_tasks=max_tasks_per_ac)
            repairs = 0
            while (not ok) and repairs < max_repairs:
                gen = repair_tasks(model, issues, gen, max_tasks=max_tasks_per_ac)
                ok, issues = validate_tasks_obj(gen, max_tasks=max_tasks_per_ac)
                repairs += 1

            items.append(
                {
                    "ac_index": ac_index,
                    "ac_text": ac,
                    "max_tasks": int(max_tasks_per_ac),
                    "plan": plan,
                    "validate": {"pass": bool(ok), "issues": issues},
                    "tasks": gen.get("tasks", [])[: int(max_tasks_per_ac)],
                }
            )
        except Exception as e:
            items.append(
                {
                    "ac_index": ac_index,
                    "ac_text": ac,
                    "error": f"{type(e).__name__}: {e}",
                    "tasks": [],
                }
            )

    return {"items": items}