from typing import TypedDict
from langgraph.graph import StateGraph, END

# 1. 「すごろくのコマ」が持つデータ（State）を定義
class MyState(TypedDict):
    message: str

# 2. 関数（ノード）を定義：ただ文字を付け足すだけ
def step_1_hello(state: MyState):
    print("--- ステップ1実行 ---")
    return {"message": state["message"] + " Hello"}

def step_2_world(state: MyState):
    print("--- ステップ2実行 ---")
    return {"message": state["message"] + " World!"}

# 3. グラフ（すごろくの盤面）を組み立てる
workflow = StateGraph(MyState)

# 「名前」をつけて関数を登録
workflow.add_node("node_hello", step_1_hello)
workflow.add_node("node_world", step_2_world)

# 進む順番を決める
workflow.set_entry_point("node_hello")      # スタート
workflow.add_edge("node_hello", "node_world") # node_hello の次は node_world
workflow.add_edge("node_world", END)         # node_world の次は ゴール(END)

# 実行できる形にする（コンパイル）
app = workflow.compile()

if __name__ == "__main__":
    # 実行！
    print("実行開始...")
    final_output = app.invoke({"message": "Start ->"})
    print(f"最終結果: {final_output['message']}")