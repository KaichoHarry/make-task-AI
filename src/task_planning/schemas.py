from typing import Any, Dict, List, Optional
from dataclasses import dataclass


ALLOWED_SUBCATEGORIES = {
    "[Code][BE]",
    "[Code][FE]",
    "[Code][DB]",
    "[Test]",
    "[Doc]",
    "[Ops]",
}

@dataclass
class Task:
    title: str
    category: str
    subcategory: str
    status: str
    priority: str
    estimate_hours: int
    assignee: str
    related_task_titles: List[str]
    period: str
    description: str
    canonical_key: str = ""
    depends_on_keys: List[str] = None
    flags: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "category": self.category,
            "subcategory": self.subcategory,
            "status": self.status,
            "priority": self.priority,
            "estimate_hours": int(self.estimate_hours),
            "assignee": self.assignee or "",
            "related_task_titles": self.related_task_titles or [],
            "period": self.period or "",
            "description": self.description,
            "canonical_key": self.canonical_key or "",
            "depends_on_keys": self.depends_on_keys or [],
            "flags": self.flags or [],
        }


def clamp_hours(h: int) -> int:
    if h < 1:
        return 1
    if h > 4:
        return 4
    return h