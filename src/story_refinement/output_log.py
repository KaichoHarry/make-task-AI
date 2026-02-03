import os
import json
from datetime import datetime
from glob import glob

class WorkflowLogger:
    def __init__(self, log_dir="history_log", max_files=5):
        # workflow.pyがあるディレクトリを基準にする
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(base_dir, log_dir)
        self.max_files = max_files
        self.current_log = {
            "setting": {},
            "input_us_ac": {},
            "loops": []
        }
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def set_config(self, target_score, max_iterations):
        """===setting=== の情報を記録"""
        self.current_log["setting"] = {
            "target_score": target_score,
            "max_iterations": max_iterations
        }

    def set_initial_input(self, us_ac_obj):
        """===input_US_AC=== の情報を記録"""
        self.current_log["input_us_ac"] = us_ac_obj.model_dump()

    def add_loop_log(self, score, issues, suggestion_obj):
        """各ループ（===Loop===）の内容を蓄積"""
        # issuesが文字列の場合は改行で分割してリスト化、リストの場合はそのまま
        formatted_issues = issues if isinstance(issues, list) else issues.strip().split('\n')
        
        loop_entry = {
            "classifier_score": score,
            "issue_detection_list": formatted_issues,
            "suggestion_us_ac": suggestion_obj.model_dump()
        }
        self.current_log["loops"].append(loop_entry)

    def save(self):
        """ファイル保存と古いファイルの削除"""
        # ファイル名の生成: YYYY_MM_DD_HH_MM_SS_output.json
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        filename = f"{timestamp}_output.json"
        filepath = os.path.join(self.log_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.current_log, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Log saved: {filepath}")
        self._rotate_logs()

    def _rotate_logs(self):
        """古いログファイルを削除（最大5つ）"""
        files = sorted(glob(os.path.join(self.log_dir, "*_output.json")))
        while len(files) > self.max_files:
            oldest_file = files.pop(0)
            os.remove(oldest_file)
            print(f"🗑️ Deleted old log: {oldest_file}")