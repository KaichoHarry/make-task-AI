"""
ユーザーストーリー(US)のスキーマ定義

USは以下の4要素で構成される：
- domain   : USのタイトル・対象領域
- persona  : 誰が
- action   : 何をしたいのか
- reason   : なぜそれをしたいのか
"""

from pydantic import BaseModel, Field


class UserStory(BaseModel):
    domain: str = Field(
        ...,
        description="User Storyの対象ドメインやタイトル"
    )
    persona: str = Field(
        ...,
        description="ユーザーストーリーの主体（Who）"
    )
    action: str = Field(
        ...,
        description="ユーザーがしたい行動（What）"
    )
    reason: str = Field(
        ...,
        description="行動によって得たい価値・理由（Why）"
    )


if __name__ == "__main__":
    # 動作確認用
    sample = UserStory(
        domain="Authentication",
        persona="User",
        action="login to the system",
        reason="access protected resources"
    )
    print(sample.model_dump())
