"""
ClassifierAI
-------------
5人の専門家（ペルソナ）の視点から US / AC の具体度を厳格に評価する
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# スキーマとプロンプトのインポート
from src.story_refinement.services.schemas.us_ac_response import UserStoryAcceptanceCriteria
from src.story_refinement.services.schemas.class_response import ClassifierResponse, PersonaFeedback
from src.story_refinement.services.prompts.classifier_ai_prompt import (
    CLASSIFIER_COMMON_SYSTEM_START,
    CLASSIFIER_COMMON_SYSTEM_END,
    CLASSIFIER_INPUT_START,
    CLASSIFIER_INPUT_END,
    CLASSIFIER_FINAL_INSTRUCTION,
    PERSONA_PROMPTS
)

load_dotenv()

def classify_us_ac(us_ac: UserStoryAcceptanceCriteria) -> ClassifierResponse:
    """
    US / AC を受け取り、5人の専門家による詳細評価を統合して返す
    """

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
    )

    # PersonaFeedback モデルの形式で出力を強制する
    structured_llm = llm.with_structured_output(PersonaFeedback)

    # 評価対象のテキスト化
    us_ac_text = f"""
**Domain**: {us_ac.user_story.domain}
**Persona**: {us_ac.user_story.persona}
**Action**: {us_ac.user_story.action}
**Reason**: {us_ac.user_story.reason}

### Acceptance Criteria
{chr(10).join(f"- {ac}" for ac in us_ac.acceptance_criteria.acceptance_criteria)}
"""

    feedback_list = []

    print("\n--- Multi-Persona Evaluation Starting ---")

    # 5つのペルソナごとに評価を実行
    for persona_key, persona_instruction in PERSONA_PROMPTS.items():
        # システムプロンプトの組み立て
        system_content = (
            persona_instruction 
            + CLASSIFIER_COMMON_SYSTEM_START 
            + CLASSIFIER_COMMON_SYSTEM_END
        )

        # ユーザープロンプトの組み立て
        human_content = (
            CLASSIFIER_INPUT_START 
            + us_ac_text 
            + CLASSIFIER_INPUT_END 
            + CLASSIFIER_FINAL_INSTRUCTION
        )

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content),
        ]

        # AIの実行（構造化された PersonaFeedback オブジェクトが返る）
        feedback: PersonaFeedback = structured_llm.invoke(messages)
        
        # どのペルソナの回答か明示的にセット
        feedback.persona = persona_key
        feedback_list.append(feedback)

        print(f"   [{persona_key.upper():<16}] Score: {feedback.score}")

    # 全ペルソナの中の最低スコアを取得（ボトルネックを基準にする）
    final_score = min(f.score for f in feedback_list)
    print(f"--- Final Unified Score: {final_score} ---\n")

    return ClassifierResponse(
        score=final_score,
        feedback_list=feedback_list
    )


if __name__ == "__main__":
    from src.story_refinement.services.schemas.user_story import UserStory
    from src.story_refinement.services.schemas.acceptance_criteria import AcceptanceCriteria

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

    result = classify_us_ac(sample)
    print("=== FULL FEEDBACK ===")
    for fb in result.feedback_list:
        print(f"\n[{fb.persona.upper()}]")
        print(f"Reason: {fb.reason}")
    
    print("\n=== AGGREGATED TEXT FOR ISSUE DETECTION ===")
    print(result.aggregated_reasons)