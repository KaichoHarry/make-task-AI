from pydantic import BaseModel, Field
from typing import List, Optional

class UserStory(BaseModel):
    """ユーザーストーリーと受入要件を保持するクラス"""
    title: str = Field(description="ユーザーストーリーのタイトル")
    content: str = Field(description="ユーザーストーリーの本文（誰が、何を、なぜ）")
    acceptance_criteria: List[str] = Field(default_factory=list, description="受入要件（AC）のリスト")