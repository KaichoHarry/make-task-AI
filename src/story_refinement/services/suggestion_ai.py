"""
SuggestionAI
-------------
IssueDetectionAI の指摘をもとに
より具体的な US / AC を生成するAI
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
) -> str:
    """
    改善された US / AC（Markdown）を返す
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,  # 文章生成なので少し創造性を許可
    )

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

    return llm.invoke(messages).content.strip()


if __name__ == "__main__":
    from src.story_refinement.services.schemas.user_story import UserStory
    from src.story_refinement.services.schemas.acceptance_criteria import AcceptanceCriteria

    us_ac = UserStoryAcceptanceCriteria(
        user_story=UserStory(
            domain="Login",
            persona="User",
            action="log into the system",
            reason="access features"
        ),
        acceptance_criteria=AcceptanceCriteria(
            acceptance_criteria=[
                "User can log in"
            ]
        )
    )

    issues = IssueResponse(
        issues="The authentication method and error handling are unclear."
    )

    print(suggest_improvements(us_ac, issues))
