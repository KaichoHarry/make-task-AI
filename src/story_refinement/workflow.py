"""
workflow.py
-----------
5人の専門家（ClassifierAI）のフィードバックをリレーし、
US / AC を多角的な視点でブラッシュアップする LangGraph ワークフロー
"""

from typing import TypedDict, Optional, List

from langgraph.graph import StateGraph, END

from src.story_refinement.services.schemas.us_ac_response import UserStoryAcceptanceCriteria
from src.story_refinement.services.schemas.issue_response import IssueResponse
from src.story_refinement.services.schemas.class_response import ClassifierResponse

from src.story_refinement.services.classifier_ai import classify_us_ac
from src.story_refinement.services.issue_detection_ai import detect_issues
from src.story_refinement.services.suggestion_ai import suggest_improvements

# ロガーのインポート
from src.story_refinement.output_log import WorkflowLogger

# =========================
# State 定義
# =========================

class RefinementState(TypedDict):
    """
    LangGraph 上で流れる状態
    """
    us_ac: UserStoryAcceptanceCriteria
    score: Optional[int]
    expert_feedback_text: Optional[str]  # 専門家たちの詳細な言い分
    issues: Optional[List[str]]          # 整理された課題リスト
    iteration: int

# =========================
# 設定
# =========================
logger = WorkflowLogger()
TARGET_SCORE = 85  # 5人のプロが納得する基準なので少し高めに設定
MAX_ITERATIONS = 5

# =========================
# Node 関数定義
# =========================

def classifier_node(state: RefinementState) -> RefinementState:
    """
    5人の専門家がそれぞれの視点で評価し、詳細なフィードバックを生成する
    """
    print(f"\n===== [Iteration {state['iteration']}: Professional Review] =====")
    result: ClassifierResponse = classify_us_ac(state["us_ac"])
    
    # ターミナルに詳細な理由を出力
    for fb in result.feedback_list:
        print(f"  ▶ {fb.persona.upper():<16} | Score: {fb.score}")
        print(f"    Reason: {fb.reason}")

    return { 
        **state, 
        "score": result.score, 
        "expert_feedback_text": result.aggregated_reasons 
    }

def issue_detection_node(state: RefinementState) -> RefinementState:
    """
    専門家のフィードバックを元に、具体的な修正ポイントをリスト化する
    """
    print("\n--- [Issue Detection: Consolidating Critiques] ---")
    issue_response: IssueResponse = detect_issues(
        state["us_ac"], 
        state["expert_feedback_text"]
    )
    
    for i, issue in enumerate(issue_response.issues, 1):
        print(f"  {i}. {issue}")

    return { **state, "issues": issue_response.issues }

def suggestion_node(state: RefinementState) -> RefinementState:
    """
    指摘事項を全て反映した新しい US / AC を生成する
    """
    print("\n--- [Suggestion AI: Refinement in progress...] ---")
    refined_obj: UserStoryAcceptanceCriteria = suggest_improvements(
        us_ac=state["us_ac"],
        issues=IssueResponse(issues=state["issues"]),
    )
    
    # ロガーにこのターンの記録を保存
    logger.add_loop_log(
        score=state["score"],
        issues=state["issues"],
        suggestion_obj=refined_obj
    )

    state["iteration"] += 1
    return { **state, "us_ac": refined_obj }

def should_continue(state: RefinementState) -> str:
    print(f"\n--- [Decision] Final Score: {state['score']} ---")
    
    if state["score"] is not None and state["score"] >= TARGET_SCORE:
        print("✅ All professionals satisfied. Sufficient quality reached.")
        return END

    if state["iteration"] >= MAX_ITERATIONS:
        print("❌ Max iterations reached. Stopping refinement.")
        return END 

    return "issue_detection"

# =========================
# Graph 定義
# =========================

def build_refinement_workflow() -> StateGraph:
    graph = StateGraph(RefinementState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("issue_detection", issue_detection_node)
    graph.add_node("suggestion", suggestion_node)

    graph.set_entry_point("classifier")

    graph.add_conditional_edges(
        "classifier",
        should_continue,
    )

    graph.add_edge("issue_detection", "suggestion")
    graph.add_edge("suggestion", "classifier")

    return graph

# =========================
# 実行
# =========================

if __name__ == "__main__":
    from src.story_refinement.services.schemas.user_story import UserStory
    from src.story_refinement.services.schemas.acceptance_criteria import AcceptanceCriteria

    initial_us_ac = UserStoryAcceptanceCriteria(
        user_story=UserStory(
            domain="Hệ thống quản lý công việc nội bộ：Tạo và theo dõi task",
            persona="Là nhân viên trong công ty",
            action="tôi muốn tạo và theo dõi các task công việc của mình",
            reason="để tôi có thể quản lý tiến độ và hoàn thành công việc đúng hạn"
        ),
        acceptance_criteria=AcceptanceCriteria(
            acceptance_criteria=[
                "Người dùng phải đăng nhập thì mới có thể tạo và xem task",
                "Người dùng có thể tạo task mới với tiêu đề và mô tả",
                "Mỗi task phải có trạng thái (Chưa làm / Đang làm / Hoàn thành)",
                "Người dùng có thể chỉnh sửa nội dung task của mình",
                "Người dùng có thể xóa task do mình tạo",
                "Task có thể được gán ngày hết hạn (deadline)",
                "Danh sách task có thể được sắp xếp theo deadline hoặc trạng thái",
                "Người dùng chỉ có thể xem và chỉnh sửa task của chính mình",
                "Khi không có task nào, hệ thống hiển thị thông báo “Không có task”",
                "Thay đổi trạng thái task phải được lưu ngay lập tức và phản ánh trên màn hình"
            ]
        )
    )

    logger.set_config(target_score=TARGET_SCORE, max_iterations=MAX_ITERATIONS)
    logger.set_initial_input(initial_us_ac)

    initial_state: RefinementState = {
        "us_ac": initial_us_ac,
        "score": None,
        "expert_feedback_text": None,
        "issues": None,
        "iteration": 0,
    }

    workflow = build_refinement_workflow()
    app = workflow.compile()

    try:
        result = app.invoke(initial_state)
        print("\n\n=== FINAL RESULT ===")
        print(f"Final Score: {result['score']}")
        print(result['us_ac'])
    except Exception as e:
        print(f"Error during workflow: {e}")
    finally:
        logger.save()