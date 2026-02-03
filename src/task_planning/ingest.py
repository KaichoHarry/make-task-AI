import json
import re
from typing import Any, Dict, List, Tuple, Optional


BULLET_RE = re.compile(r"^\s*(?:[-*•]|[0-9]+[.)]|[A-Za-z][.)])\s+")


def _extract_acs_from_text(text: str) -> List[str]:
    lines = [ln.rstrip() for ln in text.splitlines()]
    acs: List[str] = []
    buf: List[str] = []

    def flush():
        nonlocal buf
        joined = " ".join([x.strip() for x in buf]).strip()
        if joined:
            acs.append(joined)
        buf = []

    for ln in lines:
        if not ln.strip():
            flush()
            continue

        if BULLET_RE.match(ln):
            flush()
            ln = BULLET_RE.sub("", ln).strip()
            buf.append(ln)
        else:
            # 続き行として扱う（チャット貼り付けでよくある）
            if buf:
                buf.append(ln.strip())
            else:
                # 先頭が箇条書きじゃない単独行もACとして拾う
                buf.append(ln.strip())

    flush()
    return acs


def _try_parse_json(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


def _normalize_from_json(obj: Any) -> List[str]:
    """
    対応例:
    - {"acceptance_criteria": [...]} / {"ac": [...]} / {"acs": [...]}
    - [{"ac_text": ...}, ...]
    - ["...", "..."]
    - {"items":[{"ac_text":...}, ...]} など
    """
    if isinstance(obj, dict):
        for k in ["acceptance_criteria", "ac", "acs"]:
            if k in obj and isinstance(obj[k], list):
                return [str(x).strip() for x in obj[k] if str(x).strip()]

        if "items" in obj and isinstance(obj["items"], list):
            items = obj["items"]
            out = []
            for it in items:
                if isinstance(it, dict) and "ac_text" in it:
                    out.append(str(it["ac_text"]).strip())
                elif isinstance(it, str):
                    out.append(it.strip())
            return [x for x in out if x]

        # それっぽいキーがない場合は全部文字列化してテキスト扱いへ
        return []

    if isinstance(obj, list):
        if all(isinstance(x, str) for x in obj):
            return [x.strip() for x in obj if x.strip()]
        if all(isinstance(x, dict) for x in obj):
            out = []
            for it in obj:
                if "ac_text" in it:
                    out.append(str(it["ac_text"]).strip())
                elif "description" in it:
                    out.append(str(it["description"]).strip())
            return [x for x in out if x]
    return []


def ingest_input(raw_text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns:
      ac_items: [{"ac_index": 1, "ac_text": "..."}...]
      meta: {"input_format": "..."}
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return [], {"input_format": "empty"}

    obj = _try_parse_json(raw_text)
    if obj is not None:
        acs = _normalize_from_json(obj)
        if acs:
            return (
                [{"ac_index": i + 1, "ac_text": acs[i]} for i in range(len(acs))],
                {"input_format": "json"},
            )
        # JSONとして読めたがAC抽出できない → テキスト扱いに落とす

    acs = _extract_acs_from_text(raw_text)
    return (
        [{"ac_index": i + 1, "ac_text": acs[i]} for i in range(len(acs))],
        {"input_format": "text"},
    )