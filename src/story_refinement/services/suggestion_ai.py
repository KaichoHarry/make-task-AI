"""
SuggestionAI
-------------
IssueDetectionAI の指摘をもとに
構造化された US / AC を生成するAI
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from src.story_refinement.services.schemas.us_ac_response import UserStoryAcceptanceCriteria
from src.story_refinement.services.schemas.issue_response import IssueResponse
from src.story_refinement.services.prompts.suggestion_ai_prompt import (
    SUGGESTION_SYSTEM_PROMPT_START,
    SUGGESTION_SYSTEM_PROMPT_END,
    SUGGESTION_INPUT_PROMPT_START,
    SUGGESTION_INPUT_PROMPT_MIDDLE,
    SUGGESTION_INPUT_PROMPT_ISSUES,
    SUGGESTION_INPUT_PROMPT_END,
    SUGGESTION_FINAL_PROMPT_START,
    SUGGESTION_FINAL_PROMPT_END,
)

load_dotenv()

def suggest_improvements(
    us_ac: UserStoryAcceptanceCriteria,
    issues: IssueResponse,
) -> UserStoryAcceptanceCriteria: # 戻り値を型定義に変更
    """
    改善された UserStoryAcceptanceCriteria オブジェクトを返す
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,
    )

    # 【重要】構造化出力を定義
    structured_llm = llm.with_structured_output(UserStoryAcceptanceCriteria)

    system_prompt = (
        SUGGESTION_SYSTEM_PROMPT_START
        + SUGGESTION_SYSTEM_PROMPT_END
    )

    input_prompt = (
        SUGGESTION_INPUT_PROMPT_START
        + f"""
**Domain**: {us_ac.user_story.domain}
**Persona**: {us_ac.user_story.persona}
**Action**: {us_ac.user_story.action}
**Reason**: {us_ac.user_story.reason}
"""
        + SUGGESTION_INPUT_PROMPT_MIDDLE
        + f"""
{chr(10).join(f"- {ac}" for ac in us_ac.acceptance_criteria.acceptance_criteria)}
"""
        + SUGGESTION_INPUT_PROMPT_ISSUES
        + f"""
{issues.issues}
"""
        + SUGGESTION_INPUT_PROMPT_END
    )

    final_prompt = (
        SUGGESTION_FINAL_PROMPT_START
        + SUGGESTION_FINAL_PROMPT_END
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=input_prompt),
        HumanMessage(content=final_prompt),
    ]

    # invokeの結果は自動的に UserStoryAcceptanceCriteria オブジェクトになる
    return structured_llm.invoke(messages)

if __name__ == "__main__":
    # テスト実行用のコード（略）
    # ...
    result = suggest_improvements(us_ac, issues)
    print("--- Refined Result ---")
    print(f"Domain: {result.user_story.domain}")
    print(f"AC Count: {len(result.acceptance_criteria.acceptance_criteria)}")
    print(result)