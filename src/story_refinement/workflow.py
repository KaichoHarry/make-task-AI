"""
workflow.py
-----------
LangGraph を用いて
US / AC を「十分に具体的になるまで」改善するワークフローを定義する
"""

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from src.story_refinement.services.schemas.us_ac_response import UserStoryAcceptanceCriteria
from src.story_refinement.services.schemas.issue_response import IssueResponse
from src.story_refinement.services.schemas.class_response import ClassifierResponse

from src.story_refinement.services.classifier_ai import classify_us_ac
from src.story_refinement.services.issue_detection_ai import detect_issues
from src.story_refinement.services.suggestion_ai import suggest_improvements


# =========================
# State 定義
# =========================

class RefinementState(TypedDict):
    """
    LangGraph 上で流れる状態
    """
    us_ac: UserStoryAcceptanceCriteria
    score: Optional[int]
    issues: Optional[str]
    iteration: int


# =========================
# Node 関数定義
# =========================

def classifier_node(state: RefinementState) -> RefinementState:
    """
    US / AC の具体度を評価するノード
    """
    result: ClassifierResponse = classify_us_ac(state["us_ac"])

    return {
        **state,
        "score": result.score,
    }


def issue_detection_node(state: RefinementState) -> RefinementState:
    """
    US / AC の問題点を洗い出すノード
    """
    issue_response: IssueResponse = detect_issues(state["us_ac"])

    return {
        **state,
        "issues": issue_response.issues,
    }



#def suggestion_node(state: RefinementState) -> RefinementState:
    """
    US / AC を改善するノード
    """
#    refined_text: str = suggest_improvements(
#        us_ac=state["us_ac"],
#        issues=IssueResponse(issues=state["issues"]),
#    )

    # ⚠️ ここでは「AIが返した Markdown」をそのまま保持する
    # 後段で parser を噛ませて UserStoryAcceptanceCriteria に戻す想定
    # 今回はワークフロー確認が目的なのでそのまま返す

#    state["iteration"] += 1

#    return {
#        **state,
        # 仮実装：そのまま更新された US/AC として扱う
        # 本番では Markdown → 構造体変換をここに入れる
#        "us_ac": state["us_ac"],
#    }


# =========================
# 分岐ロジック
# =========================

#def should_continue(state: RefinementState) -> str:
    """
    次に進むノードを決定する
    """

    # 成功条件
#    if state["score"] is not None and state["score"] >= 80:
#        return END

    # 失敗条件（ループ上限）
#    if state["iteration"] >= 5:
#        raise RuntimeError(
#            "User Story and Acceptance Criteria could not be refined "
#            "to a sufficient level after 5 iterations."
#        )

    # 継続
#    return "issue_detection"

# =========================
# テスト用
# =========================

def suggestion_node(state: RefinementState) -> RefinementState:
    print(f"\n--- [Step] Suggestion (Iteration: {state['iteration']}) ---")
    
    refined_text: str = suggest_improvements(
        us_ac=state["us_ac"],
        issues=IssueResponse(issues=state["issues"]),
    )

    # デバッグ用にAIが生成したテキストを表示
    print("AI Suggested Improvements (Markdown):")
    print(refined_text[:200] + "...") # 長いので冒頭だけ

    # ⚠️ 【重要修正】
    # 本来はここで Markdown (refined_text) を 
    # UserStoryAcceptanceCriteria オブジェクトにパースする必要がありますが、
    # 今は一旦ループを回すために、ダミーで「改善された」ことにしてスコア判定へ戻します。
    
    # ※ もし suggest_improvements が構造体を返すように作られているなら、
    # そのまま代入してください。
    
    state["iteration"] += 1

    return {
        **state,
        # "us_ac": state["us_ac"], # ← これを更新する必要がある！
        # 一時的なテスト：もし suggest_improvements がテキストを返すなら、
        # 受入条件の1つにそのテキストを突っ込んで「変化」させてみる例：
        "us_ac": UserStoryAcceptanceCriteria(
            user_story=state["us_ac"].user_story,
            acceptance_criteria=AcceptanceCriteria(
                acceptance_criteria=[refined_text] # 仮に全入れ替え
            )
        )
    }

def should_continue(state: RefinementState) -> str:
    print(f"\n--- [Check] Score: {state['score']} | Iteration: {state['iteration']} ---")
    
    if state["score"] is not None and state["score"] >= 80:
        print("✅ Sufficient quality reached.")
        return END

    if state["iteration"] >= 5:
        print("❌ Max iterations reached. Stopping.")
        # Runtime環境を壊さないために、Raiseせず END にするのも手です
        return END 

    return "issue_detection"

# =========================
# Graph 定義
# =========================

def build_refinement_workflow() -> StateGraph:
    """
    LangGraph のワークフローを構築する
    """

    graph = StateGraph(RefinementState)

    # ノード登録
    graph.add_node("classifier", classifier_node)
    graph.add_node("issue_detection", issue_detection_node)
    graph.add_node("suggestion", suggestion_node)

    # エントリーポイント
    graph.set_entry_point("classifier")

    # エッジ定義
    graph.add_conditional_edges(
        "classifier",
        should_continue,
    )

    graph.add_edge("issue_detection", "suggestion")
    graph.add_edge("suggestion", "classifier")

    return graph


# =========================
# 単体実行用
# =========================

if __name__ == "__main__":
    from src.story_refinement.services.schemas.user_story import UserStory
    from src.story_refinement.services.schemas.acceptance_criteria import AcceptanceCriteria

    initial_state: RefinementState = {
        "us_ac": UserStoryAcceptanceCriteria(
            user_story=UserStory(
                domain="Login",
                persona="User",
                action="log in",
                reason="use the app"
            ),
            acceptance_criteria=AcceptanceCriteria(
                acceptance_criteria=[
                    "User can log in"
                ]
            )
        ),
        "score": None,
        "issues": None,
        "iteration": 0,
    }

    workflow = build_refinement_workflow()
    app = workflow.compile()

    result = app.invoke(initial_state)

    print("=== FINAL RESULT ===")
    print(result)
