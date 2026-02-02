"""
IssueDetectionAI
----------------
US / AC の曖昧さ・不足点を文章で洗い出すAI
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


def detect_issues(us_ac: UserStoryAcceptanceCriteria) -> IssueResponse:
    """
    US / AC の問題点を自然言語で返す
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,  # 分析なので多少の柔軟性を許可
    )

    system_prompt = (
        ISSUE_DETECTION_SYSTEM_PROMPT_START
        + ISSUE_DETECTION_SYSTEM_PROMPT_END
    )

    input_prompt = (
        ISSUE_DETECTION_INPUT_PROMPT_START
        + f"""
**Domain**: {us_ac.user_story.domain}
**Persona**: {us_ac.user_story.persona}
**Action**: {us_ac.user_story.action}
**Reason**: {us_ac.user_story.reason}

### Acceptance Criteria
{chr(10).join(f"- {ac}" for ac in us_ac.acceptance_criteria.acceptance_criteria)}
"""
        + ISSUE_DETECTION_INPUT_PROMPT_END
    )

    final_prompt = (
        ISSUE_DETECTION_FINAL_PROMPT_START
        + ISSUE_DETECTION_FINAL_PROMPT_END
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=input_prompt),
        HumanMessage(content=final_prompt),
    ]

    response = llm.invoke(messages).content.strip()
    return IssueResponse(issues=response)


if __name__ == "__main__":
    from src.story_refinement.services.schemas.user_story import UserStory
    from src.story_refinement.services.schemas.acceptance_criteria import AcceptanceCriteria

    sample = UserStoryAcceptanceCriteria(
        user_story=UserStory(
            domain="Login",
            persona="User",
            action="log into the system",
            reason="use the application"
        ),
        acceptance_criteria=AcceptanceCriteria(
            acceptance_criteria=[
                "System authenticates the user"
            ]
        )
    )

    print(detect_issues(sample))
