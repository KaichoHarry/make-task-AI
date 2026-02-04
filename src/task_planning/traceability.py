from __future__ import annotations
from typing import Any, Dict, List, Set, Tuple

def _flatten_tasks(group_results: List[Dict[str, Any]]) -> List[Tuple[int, int, Dict[str, Any]]]:
    """(group_index, task_index, task_obj)"""
    out = []
    for gi, gr in enumerate(group_results or []):
        for ti, t in enumerate((gr.get("tasks") or []) if isinstance(gr, dict) else []):
            if isinstance(t, dict):
                out.append((gi, ti, t))
    return out

def _task_text(task: Dict[str, Any]) -> str:
    # 近さ判定用の雑テキスト（高速）
    return f"{task.get('title','')} {task.get('description','')}".lower()

def _choose_best_task(tasks: List[Dict[str, Any]], ac_text: str) -> int:
    """
    超簡易スコア: AC文のキーワードが title/description にどれだけ含まれるか
    0件なら先頭タスクに寄せる
    """
    ac = (ac_text or "").lower()
    keys = [k for k in ac.replace("(", " ").replace(")", " ").replace("/", " ").split() if len(k) >= 4]
    if not tasks:
        return -1

    best_i = 0
    best = -1
    for i, t in enumerate(tasks):
        txt = _task_text(t)
        score = sum(1 for k in keys[:12] if k in txt)  # 上限つける
        if score > best:
            best = score
            best_i = i
    return best_i

def enforce_ac_traceability(
    *,
    ac_map: Dict[str, str],
    grouping: Dict[str, Any],
    group_results: List[Dict[str, Any]],
    mode: str = "attach",  # "attach" or "create_task"
) -> Dict[str, Any]:
    """
    すべてのACが tasks のどこかに必ず現れるようにする。
    - attach: 既存タスクの ac_ids に追記
    - create_task: 未割当ACだけまとめたタスクをグループごとに追加
    """
    all_ac_ids: List[str] = list(ac_map.keys())
    covered: Set[str] = set()

    # 既存カバレッジ
    for gr in group_results or []:
        for t in (gr.get("tasks") or []) if isinstance(gr, dict) else []:
            if isinstance(t, dict) and isinstance(t.get("ac_ids"), list):
                for a in t["ac_ids"]:
                    if isinstance(a, str):
                        covered.add(a)

    missing = [a for a in all_ac_ids if a not in covered]
    if not missing:
        return {
            "missing_ac_ids": [],
            "mode": mode,
            "changed": False,
        }

    # AC→group を引けるように
    ac_to_group: Dict[str, str] = {}
    for g in (grouping.get("groups") or []) if isinstance(grouping, dict) else []:
        if not isinstance(g, dict):
            continue
        gid = str(g.get("group_id", ""))
        for a in (g.get("ac_ids") or []):
            if isinstance(a, str):
                ac_to_group[a] = gid

    # group_results を group_id で引く
    gid_to_index: Dict[str, int] = {}
    for i, gr in enumerate(group_results or []):
        if isinstance(gr, dict) and isinstance(gr.get("group_id"), str):
            gid_to_index[gr["group_id"]] = i

    changed = False

    if mode == "create_task":
        # グループごとに未割当ACをまとめてタスク1個追加
        bucket: Dict[str, List[str]] = {}
        for a in missing:
            gid = ac_to_group.get(a, "G00")
            bucket.setdefault(gid, []).append(a)

        for gid, acs in bucket.items():
            gi = gid_to_index.get(gid)
            if gi is None:
                continue
            gr = group_results[gi]
            tasks = gr.setdefault("tasks", [])
            if not isinstance(tasks, list):
                gr["tasks"] = tasks = []
            tasks.append(
                {
                    "title": "Traceability: cover unassigned ACs",
                    "category": "Task",
                    "subcategory": "[Doc]",
                    "status": "Todo",
                    "priority": "Low",
                    "estimate_hours": 1,
                    "ac_ids": acs,
                    "related_task_titles": [],
                    "description": "Auto-added to ensure every AC is traceable to at least one task.",
                }
            )
            changed = True

    else:
        # attach: 既存タスクへ “追記” して完全カバーにする
        for a in missing:
            gid = ac_to_group.get(a, "")
            gi = gid_to_index.get(gid)
            if gi is None:
                # グループ不明なら最初のグループに寄せる
                gi = 0 if group_results else None
            if gi is None:
                continue

            gr = group_results[gi]
            tasks = (gr.get("tasks") or []) if isinstance(gr, dict) else []
            tasks = [t for t in tasks if isinstance(t, dict)]
            if not tasks:
                continue

            best_i = _choose_best_task(tasks, ac_map.get(a, ""))
            if best_i < 0:
                continue

            ac_ids = tasks[best_i].setdefault("ac_ids", [])
            if not isinstance(ac_ids, list):
                tasks[best_i]["ac_ids"] = ac_ids = []
            if a not in ac_ids:
                ac_ids.append(a)
                changed = True

    return {
        "missing_ac_ids": missing,
        "mode": mode,
        "changed": changed,
    }