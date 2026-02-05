# src/task_planning/grouping/schema.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple


# -------------------------
# Grouping policy defaults
# -------------------------
DEFAULT_MAX_AC_PER_GROUP = 10

DEFAULT_TARGET_GROUPS_MIN = 8
DEFAULT_TARGET_GROUPS_MAX = 12
DEFAULT_MAX_GROUPS = 15

DEFAULT_MIN_GROUP_SIZE = 3  # "orphan(1-2)禁止" の下限


# -------------------------
# Helpers
# -------------------------
def _is_str_list(xs: Any) -> bool:
    return isinstance(xs, list) and all(isinstance(x, str) and x.strip() for x in xs)


def _dedup_preserve(xs: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in xs:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _log_kind(ac_text: str) -> str:
    """
    audit/security/log/other をざっくり判定（ログ分離バリデーション用）
    """
    t = (ac_text or "").lower()
    # audit 優先
    if "audit" in t or "tamper" in t or "改ざん" in t or "耐改ざん" in t:
        return "audit"
    # security 次
    if "security log" in t or "セキュリティログ" in t or "ブルート" in t or "brute" in t:
        return "security"
    if "log" in t or "ログ" in t:
        return "log"
    return "other"


# -------------------------
# Normalizer
# -------------------------
def normalize_grouping_obj(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM出力をある程度「形だけ」整える（壊れにくくする）
    - groups が無ければ空
    - group_id 無ければ補完
    - ac_ids を strip / 重複除去 / 空要素除去
    - label/tags/rationale は任意（無ければ補完）
    """
    out: Dict[str, Any] = {"groups": [], "meta": {}}
    if not isinstance(obj, dict):
        return out

    out["meta"] = obj.get("meta", {}) if isinstance(obj.get("meta"), dict) else {}
    groups = obj.get("groups", [])
    if not isinstance(groups, list):
        groups = []

    fixed: List[Dict[str, Any]] = []
    for idx, g in enumerate(groups, start=1):
        if not isinstance(g, dict):
            continue

        gid = g.get("group_id")
        if not isinstance(gid, str) or not gid.strip():
            gid = f"G{idx:02d}"
        gid = gid.strip()

        ac_ids_raw = g.get("ac_ids", [])
        if not isinstance(ac_ids_raw, list):
            ac_ids_raw = []
        ac_ids = [str(x).strip() for x in ac_ids_raw if isinstance(x, str) and str(x).strip()]
        ac_ids = _dedup_preserve(ac_ids)

        label = g.get("label")
        if not isinstance(label, str):
            label = ""
        label = label.strip()

        rationale = g.get("rationale")
        if not isinstance(rationale, str):
            rationale = ""
        rationale = rationale.strip()

        tags_raw = g.get("tags", [])
        if not isinstance(tags_raw, list):
            tags_raw = []
        tags = [str(t).strip() for t in tags_raw if isinstance(t, str) and str(t).strip()]
        tags = _dedup_preserve(tags)

        fixed.append(
            {
                "group_id": gid,
                "ac_ids": ac_ids,
                "label": label,
                "rationale": rationale,
                "tags": tags,
            }
        )

    out["groups"] = fixed
    return out


# -------------------------
# Validator
# -------------------------
def validate_grouping(
    grouping_obj: Dict[str, Any],
    *,
    ac_map: Dict[str, str],
    max_ac_per_group: int = DEFAULT_MAX_AC_PER_GROUP,
    target_groups_min: int = DEFAULT_TARGET_GROUPS_MIN,
    target_groups_max: int = DEFAULT_TARGET_GROUPS_MAX,
    max_groups: int = DEFAULT_MAX_GROUPS,
    min_group_size: int = DEFAULT_MIN_GROUP_SIZE,
    require_log_split: bool = True,
) -> Tuple[bool, List[str]]:
    """
    グルーピングの強バリデーション（安定運用向け）

    強制:
    - groups: non-empty list
    - group_id unique
    - 各group ac_ids: non-empty list[str]
    - 各group size <= max_ac_per_group
    - groups_count <= max_groups
    - 全ACを「ちょうど1回」カバー（欠け/重複/未知 禁止）
    - orphan(1-2)禁止（ただし total_acs が少なすぎる場合は緩和）
    - ログ2系統分離（audit vs security）は強制（require_log_split=True の時）

    注意(警告):
    - groups_count が 8〜12 から外れること自体は “警告” 扱いにする
      （※ただし十分なAC数があるのに極端な群数は実質NGに寄せる）
    """
    issues: List[str] = []

    if not isinstance(grouping_obj, dict):
        return False, ["grouping_obj must be dict"]

    groups = grouping_obj.get("groups")
    if not isinstance(groups, list) or not groups:
        return False, ["groups must be a non-empty list"]

    # hard: count upper bound
    if len(groups) > int(max_groups):
        issues.append(f"groups_count exceeds max_groups ({len(groups)} > {max_groups})")

    # hard: group_id unique / each group shape
    seen_gid = set()
    for i, g in enumerate(groups, start=1):
        if not isinstance(g, dict):
            issues.append(f"groups[{i}] must be object")
            continue

        gid = g.get("group_id")
        if not isinstance(gid, str) or not gid.strip():
            issues.append(f"groups[{i}].group_id is missing/empty")
        else:
            gid = gid.strip()
            if gid in seen_gid:
                issues.append(f"duplicate group_id: {gid}")
            seen_gid.add(gid)

        ac_ids = g.get("ac_ids")
        if not _is_str_list(ac_ids):
            issues.append(f"groups[{i}].ac_ids must be non-empty list[str]")
            continue

        if len(ac_ids) > int(max_ac_per_group):
            issues.append(f"groups[{i}] size exceeds max_ac_per_group ({len(ac_ids)} > {max_ac_per_group})")

    # hard: Coverage exact once
    all_ac_ids = list(ac_map.keys())
    all_set = set(all_ac_ids)

    assigned: List[str] = []
    for g in groups:
        if isinstance(g, dict) and isinstance(g.get("ac_ids"), list):
            assigned.extend([a for a in g["ac_ids"] if isinstance(a, str) and a.strip()])

    assigned_set = set(assigned)

    missing = [a for a in all_ac_ids if a not in assigned_set]
    unknown = [a for a in assigned if a not in all_set]

    count: Dict[str, int] = {}
    for a in assigned:
        count[a] = count.get(a, 0) + 1
    dup = sorted([a for a, c in count.items() if c >= 2])

    if missing:
        issues.append(f"missing ACs (not assigned): {missing[:20]}{'...' if len(missing) > 20 else ''}")
    if unknown:
        issues.append(f"unknown AC ids (invented): {unknown[:20]}{'...' if len(unknown) > 20 else ''}")
    if dup:
        issues.append(f"duplicate assignment (AC appears in multiple groups): {dup[:20]}{'...' if len(dup) > 20 else ''}")

    total_acs = len(all_ac_ids)

    # hard: orphan groups (1-2) disallow — but relax if too few ACs to satisfy
    # 例: total_acs が 1〜4 などだと 3以上のグループを作れないケースがある
    if total_acs >= int(min_group_size) + 2:
        orphan_sizes = []
        for g in groups:
            ac_ids = g.get("ac_ids", [])
            if isinstance(ac_ids, list) and 1 <= len(ac_ids) < int(min_group_size):
                orphan_sizes.append((g.get("group_id", "?"), len(ac_ids)))
        if orphan_sizes:
            issues.append(f"orphan groups found (size < {min_group_size}): {orphan_sizes}")

    # hard: log split (audit vs security must not mix)
    if require_log_split:
        mixed = []
        for g in groups:
            ac_ids = g.get("ac_ids", [])
            if not isinstance(ac_ids, list):
                continue
            kinds = set()
            for a in ac_ids:
                if a in ac_map:
                    kinds.add(_log_kind(ac_map[a]))
            if "audit" in kinds and "security" in kinds:
                mixed.append(g.get("group_id", "?"))
        if mixed:
            issues.append(f"log groups must be split (audit vs security). mixed_groups={mixed}")

    # warning-like: target range (8-12)
    # ただし total_acs が少ない/制約上不可能な場合は警告を弱める
    # - 目安: 8 groups * 3 size = 24 AC 以上なら狙いを強めに見る
    if total_acs >= int(target_groups_min) * int(min_group_size):
        if not (int(target_groups_min) <= len(groups) <= int(target_groups_max)) and len(groups) <= int(max_groups):
            # これは「失敗」扱いにすると壊れやすいので、prefixを warning にする
            issues.append(
                f"warning: groups_count={len(groups)} not in target range [{target_groups_min},{target_groups_max}]"
            )

    ok = all(not str(x).startswith("warning:") for x in issues) and len(
        [x for x in issues if not str(x).startswith("warning:")]
    ) == 0

    # ↑ ok を「warningはOK」にするならこう
    # (warningは issues に残したまま、ok=True を返す)
    hard_issues = [x for x in issues if not str(x).startswith("warning:")]
    ok = len(hard_issues) == 0
    return ok, issues


# -------------------------
# Fallback (heuristic)
# -------------------------
def simple_fallback_grouping(
    ac_map: Dict[str, str],
    *,
    max_ac_per_group: int = DEFAULT_MAX_AC_PER_GROUP,
    min_group_size: int = DEFAULT_MIN_GROUP_SIZE,
) -> Dict[str, Any]:
    """
    LLMが壊れた時用のフォールバック。
    - キーワードで大まかにバケット
    - max_ac_per_group で分割
    - orphan(1-2) は近いバケットへ吸収（直前が空きある場合）
    """
    def bucket(ac_text: str) -> str:
        t = (ac_text or "").lower()
        if "jwt" in t or "token" in t:
            return "token_jwt"
        if "password" in t or "bcrypt" in t or "hash" in t or "ソルト" in t:
            return "password_hash"
        if "email" in t or "domain" in t:
            return "email_validation"
        if "lock" in t or "ロック" in t or "failed" in t or "失敗" in t:
            return "lockout"
        if "csrf" in t or "session fixation" in t:
            return "session_csrf"
        if "rate" in t or "429" in t:
            return "rate_limit"
        if "log" in t or "ログ" in t:
            k = _log_kind(ac_text)
            if k == "audit":
                return "log_audit"
            if k == "security":
                return "log_security"
            return "log_misc"
        if "ui" in t or "mask" in t or "画面" in t:
            return "ui"
        return "other"

    buckets: Dict[str, List[str]] = {}
    for ac_id, ac_text in ac_map.items():
        b = bucket(ac_text)
        buckets.setdefault(b, []).append(ac_id)

    # chunk by max_ac_per_group
    groups: List[Dict[str, Any]] = []
    gid = 1
    for bname, ids in buckets.items():
        ids = _dedup_preserve(ids)
        for i in range(0, len(ids), int(max_ac_per_group)):
            chunk = ids[i : i + int(max_ac_per_group)]
            groups.append(
                {
                    "group_id": f"G{gid:02d}",
                    "ac_ids": chunk,
                    "label": bname,
                    "rationale": "fallback heuristic bucket",
                    "tags": [bname],
                }
            )
            gid += 1

    # absorb orphan groups (size 1-2) into previous if possible
    if len(ac_map) >= int(min_group_size) + 2:
        merged: List[Dict[str, Any]] = []
        for g in groups:
            if len(g["ac_ids"]) < int(min_group_size) and merged:
                # absorb into last if it has space
                if len(merged[-1]["ac_ids"]) + len(g["ac_ids"]) <= int(max_ac_per_group):
                    merged[-1]["ac_ids"].extend(g["ac_ids"])
                    merged[-1]["ac_ids"] = _dedup_preserve(merged[-1]["ac_ids"])
                    continue
            merged.append(g)
        groups = merged

    return {"groups": groups, "meta": {"fallback": True}}