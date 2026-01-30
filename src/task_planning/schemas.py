# ==========================================
# schemas.py : データの「型（カタ）」を決めるファイル
# ==========================================

# データをきれいに扱うための道具をPythonから借りてきます
from typing import List, Literal
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# TechKanの画面にある「サブカテゴリ」の選択肢を定義します
# AIがこれ以外の勝手な言葉を使わないように制限するためのものです
# ---------------------------------------------------------
SubCategoryType = Literal[
    "[Code][BE]",    # バックエンド（サーバー側のプログラム）
    "[Code][FE]",    # フロントエンド（画面側のプログラム）
    "[Code][DB]",    # データベース（データの保存場所）
    "[Code][Infra]", # インフラ（サーバー設定など）
    "[Test]",        # テスト（プログラムが正しいか確認する作業）
    "[Design]",      # 設計（どう作るか考える作業）
    "[Doc]"          # ドキュメント（説明書作成）
]

# ---------------------------------------------------------
# 1つの「タスク」の中身を定義します
# TechKanの入力画面の項目と1対1で対応しています
# ---------------------------------------------------------
class TechKanTask(BaseModel):
    # タイトル：タスクの名前です
    title: str = Field(
        ..., 
        description="タスクのタイトル (例: ログインAPIの実装)"
    )
    
    # カテゴリ：TechKanの仕様上、ここは常に "Task" という文字にします
    category: Literal["Task"] = Field(
        "Task", 
        description="カテゴリ (TechKanの仕様でTask固定)"
    )
    
    # サブカテゴリ：上で定義したリストの中から1つ選ばせます
    subcategory: SubCategoryType = Field(
        ..., 
        description="作業内容に一番近いサブカテゴリを選んでください"
    )
    
    # ステータス：最初は必ず "Todo" (未着手) にします
    status: Literal["Todo"] = Field(
        "Todo", 
        description="初期ステータス"
    )
    
    # 見積もり時間：AIに変な数字（例えば 1.23時間など）を出させないよう、
    # TechKanでよく使う 0.5, 1.0, 2.0, 3.0, 4.0 の中から選ばせます
    estimated_hours: float = Field(
        ..., 
        description="見積もり工数(h)。0.5, 1.0, 2.0, 3.0, 4.0, のいずれかを選択してください"
    )
    
    # 優先度：High(高), Medium(中), Low(低) のどれかです
    priority: Literal["High", "Medium", "Low"] = Field(
        "Medium", 
        description="優先度"
    )
    
    # 詳細説明：HTMLタグを使って、TechKan上で見やすく表示できるようにします
    description: str = Field(
        ..., 
        description="タスクの詳細内容。HTMLタグ (<h3>, <ul>, <li>) を使って書いてください"
    )

# ---------------------------------------------------------
# 複数のタスクをまとめた「リスト」を定義します
# AIには最終的にこの形（タスクの束）で提出してもらいます
# ---------------------------------------------------------
class TechKanTaskList(BaseModel):
    tasks: List[TechKanTask]