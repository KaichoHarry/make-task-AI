from pydantic import BaseModel, Field

class ClassificationResult(BaseModel):
    is_clear: bool = Field(description="US/ACが具体的で、エンジニアが迷わず作業できる状態ならTrue")
    reason: str = Field(description="なぜそう判断したかの短い理由")

class IssueResult(BaseModel):
    issues: list[str] = Field(description="US/ACに含まれる具体的な不備や、確認が必要な事項のリスト")