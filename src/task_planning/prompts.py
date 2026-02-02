import json
import time
import google.generativeai as genai
from prompts import TASK_GENERATION_SYSTEM_PROMPT

# ==========================================
# 設定エリア
# ==========================================
BATCH_SIZE = 5  # 1回に処理するACの数（5個程度が最も高密度になります）

# 2回目以降に自動挿入する「クギを刺す」プロンプト
REMINDER_PROMPT = """
Great. Now proceed with the next batch of ACs.

⚠️ **CRITICAL REMINDERS (DO NOT FORGET):**
1. **Maintain the 4-Layer Structure**: [DB], [BE], [FE], [Test] for EVERY single AC.
2. **Tech Stack**: Next.js (Zod), FastAPI (Pydantic), SQLAlchemy.
3. **Consistency**: Use the same naming conventions as the previous batch.
4. **No Summary**: Do not summarize. Keep the high density.

Here are the next ACs:
"""

# ==========================================
# メイン処理
# ==========================================
def generate_tasks_automatically(json_file_path):
    # 1. JSONデータの読み込み
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_acs = data.get("acceptance_criteria", [])
    total_acs = len(all_acs)
    print(f"🚀 Total ACs found: {total_acs}")

    # 2. モデルの準備 (APIキーは環境変数等で設定済みとする)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-latest", # コンテキストウィンドウが広いモデル推奨
        system_instruction=TASK_GENERATION_SYSTEM_PROMPT
    )
    
    # チャットセッションの開始（これで文脈を記憶させる）
    chat = model.start_chat(history=[])
    
    generated_tasks_log = []

    # 3. バッチ処理ループ
    for i in range(0, total_acs, BATCH_SIZE):
        batch_acs = all_acs[i : i + BATCH_SIZE]
        current_batch_num = (i // BATCH_SIZE) + 1
        print(f"\nProcessing Batch {current_batch_num} (AC {i+1} to {min(i+BATCH_SIZE, total_acs)})...")

        # --- ここが自動化のキモ ---
        if i == 0:
            # 初回: 普通にACを渡す
            user_message = f"Here is the first batch of ACs:\n{json.dumps(batch_acs)}"
        else:
            # 2回目以降: 「リマインダー」＋「次のAC」を結合して渡す
            user_message = f"{REMINDER_PROMPT}\n{json.dumps(batch_acs)}"
        # ------------------------

        try:
            # AIに送信
            response = chat.send_message(user_message)
            
            # 結果を表示・保存（実際はここでパースして保存処理を入れる）
            print(f"✅ Batch {current_batch_num} Complete. Output length: {len(response.text)} chars")
            generated_tasks_log.append(response.text)
            
            # APIレート制限対策（必要に応じて）
            time.sleep(2) 

        except Exception as e:
            print(f"❌ Error in Batch {current_batch_num}: {e}")
            break

    print("\n🎉 All batches processed successfully!")
    return generated_tasks_log

if __name__ == "__main__":
    # 実行
    results = generate_tasks_automatically("login_us001.json")
    
    # 必要なら結果をファイルに保存
    with open("final_high_density_tasks.md", "w", encoding="utf-8") as f:
        f.write("\n\n".join(results))