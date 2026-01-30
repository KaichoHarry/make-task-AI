# ==========================================
# schemas.py : AIが出力するデータの「型（ルールブック）」
# ==========================================

from typing import List, Literal
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# 1. サブカテゴリの選択肢を定義
# ---------------------------------------------------------
# ここに書かれている文字列以外がAIから返ってきたらエラーにします。
# これにより、TechKanアプリ側で分類不能になるのを防ぎます。
SubCategoryType = Literal[
    "[Code][BE]",    # バックエンド実装 (Pythonなど)
    "[Code][FE]",    # フロントエンド実装 (Next.jsなど)
    "[Code][DB]",    # データベース設計・SQL
    "[Code][Infra]", # インフラ・サーバー設定 (Dockerなど)
    "[Test]",        # テストコード作成
    "[Design]",      # 設計・ドキュメント作成
    "[Doc]"          # その他ドキュメント
]

# ---------------------------------------------------------
# 2. タスク単体の設計図 (TechKanTask)
# ---------------------------------------------------------
class TechKanTask(BaseModel):
    # --- タスクのタイトル ---
    # description="..." の中は「AIへの指示」です。
    # ここで "in English" と書くことで、AIに英語出力を強制しています。
    title: str = Field(
        ..., 
        description="Technical title of the task in English (e.g., '[Auth] Implement Login API')."
    )
    
    # --- カテゴリ (固定値) ---
    # TechKanシステムが認識できるように、常に "Task" という文字を入れさせます。
    category: Literal["Task"] = Field(
        "Task", 
        description="Fixed category 'Task' for TechKan system."
    )
    
    # --- サブカテゴリ ---
    # 上で定義した SubCategoryType のリストから1つ選ばせます。
    subcategory: SubCategoryType = Field(
        ..., 
        description="Select the most appropriate subcategory."
    )
    
    # --- ステータス (初期値) ---
    # 作成直後は必ず "Todo" (未着手) になるように固定します。
    status: Literal["Todo"] = Field(
        "Todo", 
        description="Initial status must always be 'Todo'."
    )
    
    # --- 見積もり時間 (数値) ---
    # float = 小数点を含む数字 です。
    # 0.5h, 1.0h... のように具体的な数値を指定させています。
    estimated_hours: float = Field(
        ..., 
        description="Estimated effort in hours. Choose from: 0.5, 1.0, 2.0, 3.0, 4.0."
    )
    
    # --- 優先度 ---
    # High, Medium, Low の3つ以外は認めない設定です。
    priority: Literal["High", "Medium", "Low"] = Field(
        "Medium", 
        description="Task priority."
    )
    
    # --- 詳細説明 (HTML) ---
    # ここが一番重要です。
    # 1. "in English" -> 中身を英語で書かせる
    # 2. "using HTML tags" -> <h3>や<ul>を使って見やすく整形させる
    # これにより、TechKanの画面にそのまま貼り付けられるHTMLが生成されます。
    description: str = Field(
        ..., 
        description="Detailed task description in English using HTML tags (<h3>, <ul>, <li>). Must include Objective, Technical Approach, and Definition of Done."
    )

# ---------------------------------------------------------
# 3. タスクリストの定義 (TechKanTaskList)
# ---------------------------------------------------------
# AIは最終的にこの形でデータを返します。
# 「TechKanTask（上で定義したもの）がたくさん入っているリスト」という意味です。
class TechKanTaskList(BaseModel):
    tasks: List[TechKanTask]