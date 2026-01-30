"""
ClassifierAI
-------------
US / AC の具体度を 0〜100 で評価するAI
"""

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from pydantic import ValidationError
from dotenv import load_dotenv

from .schemas.us_ac_response import UserStoryAcceptanceCriteria
from .schemas.class_response import ClassifierResponse
from .prompts.classifier_ai_prompt import (
    CLASSIFIER_SYSTEM_PROMPT_START,
    CLASSIFIER_SYSTEM_PROMPT_END,
    CLASSIFIER_INPUT_PROMPT_START,
    CLASSIFIER_INPUT_PROMPT_END,
    CLASSIFIER_FINAL_PROMPT_START,
    CLASSIFIER_FINAL_PROMPT_END,
)

load_dotenv()


def classify_us_ac(us_ac: UserStoryAcceptanceCriteria) -> ClassifierResponse:
    """
    US / AC を受け取り、具体度スコア（0〜100）を返す
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,  # 評価系なのでブレさせない
    )

    system_prompt = (
        CLASSIFIER_SYSTEM_PROMPT_START
        + CLASSIFIER_SYSTEM_PROMPT_END
    )

    input_prompt = (
        CLASSIFIER_INPUT_PROMPT_START
        + f"""
**Domain**: {us_ac.user_story.domain}
**Persona**: {us_ac.user_story.persona}
**Action**: {us_ac.user_story.action}
**Reason**: {us_ac.user_story.reason}

### Acceptance Criteria
{chr(10).join(f"- {ac}" for ac in us_ac.acceptance_criteria.acceptance_criteria)}
"""
        + CLASSIFIER_INPUT_PROMPT_END
    )

    final_prompt = (
        CLASSIFIER_FINAL_PROMPT_START
        + CLASSIFIER_FINAL_PROMPT_END
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=input_prompt),
        HumanMessage(content=final_prompt),
    ]

    raw_response = llm(messages).content.strip()

    try:
        return ClassifierResponse(score=int(raw_response))
    except (ValueError, ValidationError) as e:
        raise RuntimeError(f"ClassifierAI returned invalid output: {raw_response}") from e


if __name__ == "__main__":
    from .schemas.user_story import UserStory
    from .schemas.acceptance_criteria import AcceptanceCriteria

    sample = UserStoryAcceptanceCriteria(
        user_story=UserStory(
            domain="Login",
            persona="User",
            action="log into the system",
            reason="access my account"
        ),
        acceptance_criteria=AcceptanceCriteria(
            acceptance_criteria=[
                "Login succeeds with valid credentials"
            ]
        )
    )

    print(classify_us_ac(sample))
