"""
受入要件（Acceptance Criteria）のスキーマ定義
"""

from typing import List
from pydantic import BaseModel, Field


class AcceptanceCriteria(BaseModel):
    acceptance_criteria: List[str] = Field(
        ...,
        description="受入要件のリスト（すべて自然言語の文字列）",
        min_items=1
    )


if __name__ == "__main__":
    sample = AcceptanceCriteria(
        acceptance_criteria=[
            "Return HTTP 200 on success",
            "Return HTTP 401 on failure"
        ]
    )
    print(sample.model_dump())
