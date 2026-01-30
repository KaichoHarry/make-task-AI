# ==========================================
# generator.py : AIを動かすメインのプログラム
# ==========================================

import json # データをJSON形式で扱うための道具
# LangChainという、AIを便利に使うためのライブラリを読み込みます
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# さっき作った「データの型」と「指示書」を、同じフォルダ(.ドット)から読み込みます
from .schemas import TechKanTaskList
from .prompts import TASK_GENERATION_SYSTEM_PROMPT

def generate_tasks(us_json_data: list) -> TechKanTaskList:
    """
    ここがメインの関数です。
    ユーザーストーリーのデータ(us_json_data)を受け取って、
    AIにタスクリストを作らせて返します。
    """
    
    # -----------------------------------------------------
    # 1. AIモデルの準備
    # -----------------------------------------------------
    # model="gpt-4o": 最新の賢いモデルを使います
    # temperature=0: 余計な創造性を挟まず、真面目に答えさせます（0〜1で設定）
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # -----------------------------------------------------
    # 2. 出力形式の固定（パーサーの準備）
    # -----------------------------------------------------
    # AIの返事を、schemas.pyで作った「TechKanTaskList」の形に強制変換する道具です
    parser = PydanticOutputParser(pydantic_object=TechKanTaskList)

    # -----------------------------------------------------
    # 3. プロンプト（命令文）の組み立て
    # -----------------------------------------------------
    # 「システム設定(prompts.py)」と「ユーザーの入力データ」を合体させます
    prompt = ChatPromptTemplate.from_messages([
        # システムへの指示（あなたの役割はPMです...という内容）
        ("system", TASK_GENERATION_SYSTEM_PROMPT),
        
        # ユーザーからの入力
        # {input_json} に実際の要件データが入ります
        # {format_instructions} には「このJSON形式で返してね」という指示が自動で入ります
        ("user", "以下の要件定義データをタスク化してください:\n\n{input_json}\n\n{format_instructions}")
    ])

    # -----------------------------------------------------
    # 4. 実行チェーンの作成
    # -----------------------------------------------------
    # プロンプト(指示) -> LLM(AI) -> パーサー(整形) の順にデータを流すパイプラインを作ります
    chain = prompt | llm | parser
    
    try:
        # -------------------------------------------------
        # 5. 実行！
        # -------------------------------------------------
        # invoke() で実際にAIにデータを投げて結果を待ちます
        result = chain.invoke({
            # 日本語が含まれるので ensure_ascii=False で文字化けを防ぎます
            "input_json": json.dumps(us_json_data, ensure_ascii=False),
            "format_instructions": parser.get_format_instructions()
        })
        
        # 成功したら結果（タスクのリスト）を返します
        return result
        
    except Exception as e:
        # もしエラーが起きたら、ターミナルに赤文字っぽい雰囲気でエラーを表示します
        print(f"❌ Error generating tasks: {e}")
        # エラーの内容をそのまま呼び出し元に伝えます
        raise e