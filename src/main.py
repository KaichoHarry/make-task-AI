from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
import os
import json
import subprocess
import tempfile

# story_refinement 側の型
from src.story_refinement.services.schemas.user_story import UserStory
from src.story_refinement.services.schemas.acceptance_criteria import AcceptanceCriteria
from src.story_refinement.services.schemas.us_ac_response import UserStoryAcceptanceCriteria

# workflow 本体（あなたが作ったやつ）
from src.story_refinement.workflow import build_refinement_workflow, TARGET_SCORE, MAX_ITERATIONS
from src.story_refinement.output_log import WorkflowLogger


app = FastAPI(title="make-task-AI API", version="0.1.0")


# -------------------------
# 入出力スキーマ
# -------------------------
class FlatUSAC(BaseModel):
    domain: str
    persona: str
    action: str
    reason: str
    acceptance_criteria: List[str] = Field(min_length=1)


class TasksResponse(BaseModel):
    tasks: List[Dict[str, Any]]
    meta: Optional[Dict[str, Any]] = None


# -------------------------
# Utils
# -------------------------
def to_nested_usac(flat: FlatUSAC) -> UserStoryAcceptanceCriteria:
    return UserStoryAcceptanceCriteria(
        user_story=UserStory(
            domain=flat.domain,
            persona=flat.persona,
            action=flat.action,
            reason=flat.reason,
        ),
        acceptance_criteria=AcceptanceCriteria(
            acceptance_criteria=flat.acceptance_criteria
        ),
    )


def to_flat_dict(usac: UserStoryAcceptanceCriteria) -> Dict[str, Any]:
    return {
        "domain": usac.user_story.domain,
        "persona": usac.user_story.persona,
        "action": usac.user_story.action,
        "reason": usac.user_story.reason,
        "acceptance_criteria": usac.acceptance_criteria.acceptance_criteria,
    }


# -------------------------
# Endpoints
# -------------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/refine", response_model=FlatUSAC)
def refine(payload: FlatUSAC):
    """
    入力US/AC(フラット) → story_refinement workflow → refined(フラット)を返す
    out_refined.json も history_log2 に保存
    """
    # workflow logger（API用に毎回作る）
    logger = WorkflowLogger(log_dir="history_log2", max_files=5)
    logger.set_config(target_score=TARGET_SCORE, max_iterations=MAX_ITERATIONS)

    initial_us_ac = to_nested_usac(payload)
    logger.set_initial_input(initial_us_ac)

    initial_state = {
        "us_ac": initial_us_ac,
        "score": None,
        "expert_feedback_text": None,
        "issues": None,
        "iteration": 0,
    }

    workflow = build_refinement_workflow()
    app_graph = workflow.compile()

    out_path = os.path.join(
        os.path.dirname(__file__),
        "story_refinement",
        "history_log2",
        "out_refined.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    try:
        result = app_graph.invoke(initial_state)
        refined_obj: UserStoryAcceptanceCriteria = result["us_ac"]

        # out_refined.json に保存（フラット）
        refined_flat = to_flat_dict(refined_obj)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(refined_flat, f, ensure_ascii=False, indent=2)

        return FlatUSAC(**refined_flat)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"refine failed: {e}")

    finally:
        logger.save()


@app.post("/tasks", response_model=TasksResponse)
def generate_tasks(payload: FlatUSAC):
    """
    フラットUS/AC → task_planning CLI (python -m src.task_planning.run) → tasks を返す
    """
    in_path = None
    out_path = None

    try:
        # 入力を一時ファイルに保存
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json", encoding="utf-8"
        ) as f_in:
            json.dump(payload.model_dump(), f_in, ensure_ascii=False, indent=2)
            in_path = f_in.name

        # 出力先（一時ファイルパスだけ用意）
        fd, out_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

        # task_planning 実行
        # もし export-mode 等が必要ならここに引数追加できる
        cmd = [
            "python3",
            "-u",
            "-m",
            "src.task_planning.run",
            "-i",
            in_path,
            "-o",
            out_path,
        ]

        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "task_planning failed",
                    "stdout": (p.stdout or "")[-4000:],
                    "stderr": (p.stderr or "")[-4000:],
                },
            )

        # 結果JSONを読み込み
        data = json.load(open(out_path, encoding="utf-8"))

        # data が {"tasks": [...], "meta": {...}} 前提
        # meta が無ければ None になるだけ
        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"task generation failed: {e}")

    finally:
        # 一時ファイル削除
        try:
            if in_path and os.path.exists(in_path):
                os.remove(in_path)
        except Exception:
            pass
        try:
            if out_path and os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass