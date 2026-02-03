"""
ClassifierAI が返却する詳細評価のスキーマ

- 各専門家（ペルソナ）ごとのスコアと理由を保持する
- 全体のスコアは各専門家の最低点を採用する
"""

from pydantic import BaseModel, Field, field_validator
from typing import List


class PersonaFeedback(BaseModel):
    """各専門家（ペルソナ）による個別の評価結果"""
    persona: str = Field(..., description="評価を行った専門家の役割（例: backend, security）")
    score: int = Field(..., description="0〜100の具体的スコア")
    reason: str = Field(..., description="そのスコアをつけた具体的な理由・指摘点")

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("score must be between 0 and 100")
        return v


class ClassifierResponse(BaseModel):
    """全専門家の評価を統合したレスポンス"""
    score: int = Field(..., description="全ペルソナの中の最低スコア（ボトルネック判定）")
    feedback_list: List[PersonaFeedback] = Field(..., description="各専門家からの詳細フィードバックリスト")

    @property
    def aggregated_reasons(self) -> str:
        """
        IssueDetectionAI に渡すための結合テキストを作成する。
        各専門家がどこを問題視したかを一覧化する。
        """
        lines = []
        for fb in self.feedback_list:
            lines.append(f"【{fb.persona.upper()}の視点 (Score: {fb.score})】\n{fb.reason}")
        return "\n\n".join(lines)


if __name__ == "__main__":
    # 単体テスト用コード
    feedbacks = [
        PersonaFeedback(
            persona="backend_engineer",
            score=40,
            reason="データ型とエラーレスポンスの定義が不足しており、実装に着手できない。"
        ),
        PersonaFeedback(
            persona="qa_engineer",
            score=60,
            reason="正常系の動作はわかるが、境界値テストのための具体的な数値制限が不明。"
        )
    ]

    # 最低点を全体のスコアとする想定でインスタンス化
    min_score = min(f.score for f in feedbacks)
    sample = ClassifierResponse(score=min_score, feedback_list=feedbacks)

    print("--- Model Dump ---")
    print(sample.model_dump())
    
    print("\n--- Aggregated Reasons for IssueDetectionAI ---")
    print(sample.aggregated_reasons)