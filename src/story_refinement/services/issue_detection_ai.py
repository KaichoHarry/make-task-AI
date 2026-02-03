"""
IssueDetectionAI
----------------
専門家（ClassifierAI）のフィードバックと元の US/AC を照らし合わせ、
具体的な改善・修正が必要なポイントを整理するAI
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from src.story_refinement.services.schemas.us_ac_response import UserStoryAcceptanceCriteria
from src.story_refinement.services.schemas.issue_response import IssueResponse
from src.story_refinement.services.prompts.issue_detection_ai_prompt import (
    ISSUE_DETECTION_SYSTEM_PROMPT_START,
    ISSUE_DETECTION_SYSTEM_PROMPT_END,
    ISSUE_DETECTION_INPUT_PROMPT_START,
    ISSUE_DETECTION_INPUT_PROMPT_END,
    ISSUE_DETECTION_FINAL_PROMPT_START,
    ISSUE_DETECTION_FINAL_PROMPT_END,
)

load_dotenv()

def detect_issues(us_ac: UserStoryAcceptanceCriteria, expert_feedback: str) -> IssueResponse:
    """
    US / AC と専門家からのダメ出しを受け取り、構造化された指摘リストを返す
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3, # 専門家の意見を解釈するため、少し柔軟性を持たせる
    )

    # 構造化出力を有効化 (IssueResponse: List[str])
    structured_llm = llm.with_structured_output(IssueResponse)

    # システムプロンプトの組み立て
    system_prompt = (
        ISSUE_DETECTION_SYSTEM_PROMPT_START
        + ISSUE_DETECTION_SYSTEM_PROMPT_END
    )

    # インプットプロンプトの組み立て（専門家のフィードバック用セクションを追加）
    input_prompt = (
        ISSUE_DETECTION_INPUT_PROMPT_START
        + f"""
**Domain**: {us_ac.user_story.domain}
**Persona**: {us_ac.user_story.persona}
**Action**: {us_ac.user_story.action}
**Reason**: {us_ac.user_story.reason}

### Acceptance Criteria
{chr(10).join(f"- {ac}" for ac in us_ac.acceptance_criteria.acceptance_criteria)}

### Expert Feedback (Specialized Personas)
{expert_feedback}
"""
        + ISSUE_DETECTION_INPUT_PROMPT_END
    )

    # 最終指示プロンプトの組み立て
    final_prompt = (
        ISSUE_DETECTION_FINAL_PROMPT_START
        + ISSUE_DETECTION_FINAL_PROMPT_END
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=input_prompt),
        HumanMessage(content=final_prompt),
    ]

    # 直接 IssueResponse オブジェクト（指摘事項のリスト）が返ってくる
    return structured_llm.invoke(messages)


if __name__ == "__main__":
    from src.story_refinement.services.schemas.user_story import UserStory
    from src.story_refinement.services.schemas.acceptance_criteria import AcceptanceCriteria

    # テストデータ
    sample_us_ac = UserStoryAcceptanceCriteria(
        user_story=UserStory(
            domain="Login",
            persona="User",
            action="log in",
            reason="access features"
        ),
        acceptance_criteria=AcceptanceCriteria(
            acceptance_criteria=["User can log in"]
        )
    )

    # ClassifierAIから渡ってくる想定のフィードバックテキスト
    sample_feedback = """
【BACKEND_ENGINEERの視点 (Score: 30)】
具体的な認証アルゴリズムやパスワードハッシュ化の指定がない。

【SECURITY_ENGINEERの視点 (Score: 20)】
ログイン失敗時のロックアウト仕様や2要素認証の検討が全くなされていない。
"""

    print("--- Issue Detection Testing ---")
    result = detect_issues(sample_us_ac, sample_feedback)
    print(f"Detected Issues: {result.issues}")