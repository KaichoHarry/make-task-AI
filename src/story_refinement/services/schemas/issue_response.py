"""
IssueDetectionAI が返却する内容のスキーマ
"""
from pydantic import BaseModel, Field
from typing import List

class IssueResponse(BaseModel):
    # description を新しい役割（専門家フィードバックの集約）に合わせて最適化
    issues: List[str] = Field(
        ...,
        description="各専門家（PM, Backend, Security, QA, UX）の視点を踏まえ、US/ACで修正・具体化が必要なポイントを整理したリスト"
    )

if __name__ == "__main__":
    # 単体テスト用
    sample = IssueResponse(
        issues=[
            "Backend: パスワードのハッシュ化アルゴリズム（例: Argon2）の指定がありません。",
            "Security: 連続ログイン失敗時のアカウントロックアウト条件が定義されていません。",
            "QA: パスワードの最小・最大文字数などの境界値条件が不足しています。"
        ]
    )
    print("--- Model Dump ---")
    print(sample.model_dump())
    
    print("\n--- Individual Issues ---")
    for i, issue in enumerate(sample.issues, 1):
        print(f"{i}. {issue}")