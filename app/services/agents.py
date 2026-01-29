from pydantic import BaseModel, Field

class ClassificationResult(BaseModel):
    is_clear: bool = Field(description="US/ACが具体的で、エンジニアが迷わず作業できる状態ならTrue")
    reason: str = Field(description="なぜそう判断したかの短い理由")

# プロンプト案
CLASSIFIER_PROMPT = """
あなたはシニアプロダクトマネージャーです。
入力されたユーザーストーリー(US)と受入要件(AC)を評価し、開発者がすぐにタスク（チケット）に分割できるほど明確かどうかを判定してください。

基準：
1. 目的（Why）が明確か？
2. 振る舞い（AC）が具体的で、テスト可能か？
3. 曖昧な表現（「いい感じに」「使いやすく」など）が含まれていないか？
"""

class IssueResult(BaseModel):
    issues: list[str] = Field(description="US/ACに含まれる具体的な不備や、確認が必要な事項のリスト")

# プロンプト案
ISSUE_DETECTOR_PROMPT = """
あなたはQAエンジニアです。
提示されたUS/ACの欠陥を見つけてください。
- どの条件で何が起こるか不明確な点
- 考慮漏れ（エラーケース、エッジケース）
- 技術的に実現不可能、または定義が広すぎる箇所
これらを「質問」または「指摘」としてリストアップしてください。
"""

# ここでは Step 1 で定義した UserStory クラスを再利用します
# プロンプト案
SUGGESTION_PROMPT = """
あなたは優秀なビジネスアナリストです。
現在のUS/ACと、QAからの指摘内容をもとに、より具体的でクリアなUS/ACにアップデートしてください。
元の意図を損なわず、専門用語を適切に使い、エンジニアが実装可能なレベルまで解像度を上げてください。
"""