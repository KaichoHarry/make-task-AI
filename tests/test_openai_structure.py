import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

load_dotenv()

class TestSchema(BaseModel):
    is_ok: bool = Field(description="テスト成否")
    message: str = Field(description="AIからのメッセージ")

def test_structured_output():
    # 1. セットアップ
    llm = ChatOpenAI(model="gpt-4o")
    structured_llm = llm.with_structured_output(TestSchema)

    # 2. 実行
    prompt = "「テスト成功です」というメッセージと共にTrueを返してください。"
    result = structured_llm.invoke(prompt)

    # 3. 検証
    print(f"\nAIの回答: {result}")
    assert isinstance(result, TestSchema)
    assert result.is_ok is True
    print("✅ 構造化出力テスト完了！")

if __name__ == "__main__":
    test_structured_output()