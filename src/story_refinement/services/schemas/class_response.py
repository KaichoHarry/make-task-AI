"""
ClassifierAI が返却するスコアのスキーマ

- 0   : 非常に抽象的
- 100 : 非常に具体的
"""

from pydantic import BaseModel, Field, field_validator


class ClassifierResponse(BaseModel):
    score: int = Field(
        ...,
        description="USとACの具体度スコア（0〜100）"
    )

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("score must be between 0 and 100")
        return v


if __name__ == "__main__":
    sample = ClassifierResponse(score=85)
    print(sample.model_dump())
