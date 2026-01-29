from typing import TypedDict
from langgraph.graph import StateGraph, END

# 1. 状態(State)の定義
class TestState(TypedDict):
    revision_count: int
    is_clear: bool

# 2. 各ノード（AIの代わりをする関数）の定義
def classifier_node(state: TestState):
    print(f"--- Classifier: 現在の修正回数 {state['revision_count']} ---")
    # 2回修正されたらクリア（True）にするという仮のロジック
    if state['revision_count'] >= 2:
        return {"is_clear": True}
    return {"is_clear": False}

def suggestion_node(state: TestState):
    print("--- Suggestion: USを修正します ---")
    return {"revision_count": state['revision_count'] + 1}

# 3. 分岐条件の定義
def decide_next_node(state: TestState):
    if state["is_clear"]:
        return "end"
    return "suggest"

# 4. グラフの構築
workflow = StateGraph(TestState)

workflow.add_node("classify", classifier_node)
workflow.add_node("suggest", suggestion_node)

workflow.set_entry_point("classify")

# 条件付きエッジ（ここがシーケンス図の alt 部分）
workflow.add_conditional_edges(
    "classify",
    decide_next_node,
    {
        "end": END,
        "suggest": "suggest"
    }
)

workflow.add_edge("suggest", "classify")

app = workflow.compile()

# 5. 実行
def test_graph_flow():
    print("\n--- グラフの実行開始 ---")
    initial_state = {"revision_count": 0, "is_clear": False}
    result = app.invoke(initial_state)
    print(f"--- 最終結果: {result} ---")
    assert result["is_clear"] is True
    assert result["revision_count"] == 2

if __name__ == "__main__":
    test_graph_flow()