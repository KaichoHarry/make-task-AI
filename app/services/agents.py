import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.prompts.agent_prompts import CLASSIFIER_PROMPT, ISSUE_DETECTOR_PROMPT, SUGGESTION_PROMPT
from app.schemas.ai_response import ClassificationResult, IssueResult

# モデルの初期化
# ※ Dockerコンテナ内で実行する場合、環境変数 OPENAI_API_KEY が設定されている必要があります
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 1. 判定ノード (Classifier)
def classifier_node(state: dict):
    print("\n--- [Node] Classifier: 判定中 ---")
    structured_llm = llm.with_structured_output(ClassificationResult)
    
    human_content = f"US: {state.get('user_story')}\nAC: {state.get('acceptance_criteria')}"
    
    result = structured_llm.invoke([
        SystemMessage(content=CLASSIFIER_PROMPT),
        HumanMessage(content=human_content)
    ])
    
    print(f"判定結果: {'✅ OK' if result.is_clear else '❌ NG'}")
    print(f"理由: {result.reason}")
    
    return {
        "is_clear": result.is_clear,
        "reason": result.reason
    }

# 2. 欠陥検出ノード (Issue Detector)
def issue_detector_node(state: dict):
    print("\n--- [Node] Issue Detector: 不備を抽出中 ---")
    structured_llm = llm.with_structured_output(IssueResult)
    
    human_content = f"US: {state.get('user_story')}\nAC: {state.get('acceptance_criteria')}"
    
    result = structured_llm.invoke([
        SystemMessage(content=ISSUE_DETECTOR_PROMPT),
        HumanMessage(content=human_content)
    ])
    
    for i, issue in enumerate(result.issues, 1):
        print(f"指摘{i}: {issue}")
        
    return {"issues": result.issues}

# ---------------------------------------------------------
# 単体テスト用のメイン処理
# ---------------------------------------------------------
if __name__ == "__main__":
    # テスト用の入力データ（わざと曖昧なものを渡してみます）
    test_state = {
        "user_story": "ユーザーとして、ログインしていい感じに商品を探したい。",
        "acceptance_criteria": "1. ログインができること。 2. 検索が使いやすいこと。",
        "revision_count": 0
    }

    print("=== Agent単体テスト開始 ===")
    
    # 1. 判定を実行してみる
    print("\n>>> テスト1: Classifierの実行")
    classification = classifier_node(test_state)
    
    # 2. 判定がNGなら、不備を抽出してみる
    if not classification["is_clear"]:
        print("\n>>> テスト2: Issue Detectorの実行")
        issues = issue_detector_node(test_state)
    
    print("\n=== テスト完了 ===")