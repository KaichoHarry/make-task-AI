import json
import os
from dotenv import load_dotenv  # <--- 追加！
load_dotenv()
from src.task_planning.generator import generate_tasks

def main():
    # 1. 画像にあるテストデータを読み込む
    file_path = "tests/fixtures/login_us001.json"
    
    print(f"📂 {file_path} を読み込んでいます...")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # 【重要】generatorは「リスト(配列)」を受け取る仕様なので、
        # 単体のオブジェクト({})ならリスト([])で包みます
        if isinstance(data, dict):
            input_data = [data]
        else:
            input_data = data

        print("🤖 AIにタスク生成を依頼中... (20〜30秒かかります)")
        
        # 2. あなたが作ったAI機能を呼び出す
        result = generate_tasks(input_data)
        
        # 3. 結果をきれいに表示する
        # model_dump_json(indent=2) で見やすいJSON文字列にしてくれます
        print("\n🎉 生成成功！以下のタスクが作成されました:\n")
        print(result.model_dump_json(indent=2))

        # ファイルにも保存してみる（確認用）
        with open("output_test.json", "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
        print("\n💾 output_test.json にも保存しました")

    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {file_path}")
        print("パスが正しいか確認してください")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()