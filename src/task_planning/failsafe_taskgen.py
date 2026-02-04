# src/task_planning/failsafe_taskgen.py
from __future__ import annotations

from typing import Any, Dict, List


def _guess_subcategory(ac_text: str) -> str:
    t = (ac_text or "").lower()
    if any(k in t for k in ["sql injection", "sqli", "xss", "sanitize", "csrf", "security"]):
        return "Security"
    if any(k in t for k in ["audit", "tamper", "監査", "改ざん", "耐改ざん"]):
        return "Audit"
    if any(k in t for k in ["log", "ログ", "history"]):
        return "Logging"
    if any(k in t for k in ["db", "schema", "migration", "index", "table"]):
        return "DB"
    if any(k in t for k in ["ui", "screen", "responsive", "layout", "widget"]):
        return "UI"
    if any(k in t for k in ["api", "rest", "endpoint", "rate limit", "caching", "cache", "performance", "ms", "sec"]):
        return "API"
    if any(k in t for k in ["validation", "invalid", "format", "error when", "must reject"]):
        return "Validation"
    return "General"


def ac_map_to_min_tasks(ac_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    FAILSAFE:
    - 何が壊れても最低限のタスク配列を返す
    - 各ACをそのまま1タスクにする（最低限フォーマット固定）
    """
    tasks: List[Dict[str, Any]] = []
    for ac_id, text in (ac_map or {}).items():
        ac_text = str(text or "").strip()
        title = ac_text
        if len(title) > 90:
            title = title[:90].rstrip() + "…"

        tasks.append(
            {
                "ac_ids": [str(ac_id)],
                "category": "Task",
                "status": "Todo",
                "title": title,
                "subcategory": _guess_subcategory(ac_text),
            }
        )
    return tasks