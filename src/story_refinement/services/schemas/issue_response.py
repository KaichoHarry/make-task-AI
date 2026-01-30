"""
IssueDetectionAI が返却する内容のスキーマ

- US / AC の「曖昧さ」「不足点」「具体化できる点」を文章で返す
"""

from pydantic import BaseModel, Field


class IssueResponse(BaseModel):
    issues: str = Field(
        ...,
        description="USおよびACに対する不明点・改善点の指摘"
    )


if __name__ == "__main__":
    sample = IssueResponse(
        issues="The authentication method is unclear. Specify email/password or SSO."
    )
    print(sample.model_dump())
