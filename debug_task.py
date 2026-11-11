"""
動作確認用スクリプト。

使い方:
    python debug_task.py                                  # login_us001 で実行
    python debug_task.py tests/fixtures/login_us005.json  # 入力JSONを指定

task_planning のCLI（src/task_planning/run.py）をそのまま呼び、
結果を output_test.json に保存して概要を表示します。
"""
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from src.task_planning import run as task_run  # noqa: E402

OUTPUT_PATH = "output_test.json"


def main() -> None:
    in_path = sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/login_us001.json"
    print(f"📂 {in_path} を読み込んでいます...")
    print("🤖 AIにタスク生成を依頼中... (数十秒〜数分かかります)")

    sys.argv = ["run", "-i", in_path, "-o", OUTPUT_PATH]
    task_run.main()

    with open(OUTPUT_PATH, encoding="utf-8") as f:
        out = json.load(f)

    meta = out.get("meta", {})
    print("\n🎉 生成完了")
    print(f"  ACs={meta.get('ac_count_selected')} groups={meta.get('group_count')} "
          f"tasks={meta.get('total_tasks')} fallback={meta.get('fallback')}")
    if meta.get("fallback"):
        print("  ⚠ フォールバック動作です（LLM呼び出しに失敗している可能性）。上の [WARN] を確認してください。")
    print(f"💾 {OUTPUT_PATH} に保存しました")


if __name__ == "__main__":
    main()
