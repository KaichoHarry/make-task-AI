# src/task_planning/fallback_ac_tasks.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


_SPACE_RE = re.compile(r"\s+")


def _normalize_space(s: str) -> str:
    return _SPACE_RE.sub(" ", (s or "").strip())


def _short_title(ac_text: str, max_len: int = 80) -> str:
    """
    AC文をそのままタイトルにすると長いので、先頭を短くして使う。
    """
    t = _normalize_space(ac_text)
    if not t:
        return "(empty acceptance criteria)"
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _guess_subcategory(ac_text: str) -> str:
    """
    最低限のキーワード分類（あとで辞書を増やすだけで強化できる）。
    ※ 判定順が重要：より「強い意味」を先に置く。
    """
    t = (ac_text or "").lower()

    # logging / audit（強い意味）
    if any(k in t for k in ["tamper", "immutable", "audit log", "audit", "監査", "耐改ざん", "改ざん"]):
        return "Logging/Audit"
    if any(k in t for k in ["security log", "セキュリティログ"]):
        return "Logging/Audit"
    if "log" in t or "logging" in t or "ログ" in t:
        return "Logging/Audit"

    # auth / permission
    if any(k in t for k in ["authenticated", "authentication", "auth", "login", "jwt", "session"]):
        return "Auth/Permission"
    if any(k in t for k in ["permission", "role", "rbac", "authorize", "authorization"]):
        return "Auth/Permission"

    # security / validation
    if any(k in t for k in ["sql injection", "sqli", "xss", "sanitize", "sanitise", "csrf", "validation"]):
        return "Security/Validation"
    if any(k in t for k in ["rate limit", "ratelimit", "throttle", "brute"]):
        return "Security/Validation"

    # performance / cache
    if any(k in t for k in ["cache", "caching", "latency", "performance", "throughput", "p95"]):
        return "Performance/Cache"
    if any(k in t for k in [" ms", "ms.", "milliseconds", " second", "seconds", "1 second"]):
        return "Performance/Cache"

    # api / integration
    if any(k in t for k in ["api", "rest", "endpoint", "http", "response"]):
        return "API"

    # ui / ux
    if any(k in t for k in ["responsive", "mobile", "layout", "widget", "screen", "ui", "ux"]):
        return "UI/UX"

    # export / report
    if any(k in t for k in ["export", "csv", "pdf", "report"]):
        return "Export/Report"

    return "General"


def _sort_ac_items(ac_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    安定順にする：
    - AC-001, AC-002 ... を数字でソートできるならそうする
    - できない場合はキーの辞書順
    """
    def key_fn(item: Tuple[str, str]) -> Tuple[int, str]:
        ac_id = item[0]
        m = re.search(r"(\d+)$", ac_id)
        if m:
            return (int(m.group(1)), ac_id)
        return (10**9, ac_id)

    return sorted(list(ac_map.items()), key=key_fn)


def ac_map_to_tasks(ac_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Fallback用：ACをそのまま最小タスクとして返す。
    タスク形式（あなたの仕様）:
    - ac_ids
    - category ("Task")
    - status ("Todo")
    - title
    - subcategory
    （task_id は運用上便利なので付ける）
    """
    tasks: List[Dict[str, Any]] = []

    for i, (ac_id, ac_text) in enumerate(_sort_ac_items(ac_map), start=1):
        text = "" if ac_text is None else str(ac_text)
        tasks.append(
            {
                "task_id": f"T-{i:03d}",
                "ac_ids": [str(ac_id)],
                "category": "Task",
                "status": "Todo",
                "title": _short_title(text),
                "subcategory": _guess_subcategory(text),
            }
        )

    return tasks