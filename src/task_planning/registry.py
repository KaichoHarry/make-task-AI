from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TaskRegistry:
    """
    canonical_key で重複生成を抑える台帳
    """
    key_to_title: Dict[str, str] = field(default_factory=dict)

    def has(self, key: str) -> bool:
        return key in self.key_to_title

    def get_title(self, key: str) -> Optional[str]:
        return self.key_to_title.get(key)

    def register(self, key: str, title: str) -> None:
        if key and title and key not in self.key_to_title:
            self.key_to_title[key] = title