from typing import TypedDict, List, Annotated
import operator
from .user_story import UserStory

class GraphState(TypedDict):
    """
    LangGraph内でノード間を渡り歩くデータの構造
    """
    # 現在のUS/AC（各AIがここを上書き、あるいは参照する）
    current_us_ac: UserStory
    
    # 議論の履歴（Issue Detection AIが見つけた問題点などを記録）
    issues: Annotated[List[str], operator.add]
    
    # 修正回数のカウント（無限ループ防止用）
    revision_count: int
    
    # Classifier AIが最終的にOKを出したかどうかのフラグ
    is_clear: bool