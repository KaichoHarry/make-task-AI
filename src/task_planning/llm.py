import os
import json
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

# .env があれば読む（`python -m src.task_planning.run` を単体で実行しても動くように）
load_dotenv()

_client = None


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(
            f"{name} is missing. Put it in .env (see .env.example) or export it."
        )
    return v


def get_client() -> OpenAI:
    """importした瞬間ではなく、最初に使う時にクライアントを作る。"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=_require_env("OPENAI_API_KEY"),
            timeout=60.0,
            max_retries=2,
        )
    return _client


def call_llm_json(
    *,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 1400,
) -> Dict[str, Any]:
    print(f"[LLM] request -> model={model}, max_tokens={max_tokens}", flush=True)
    resp = get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or "{}"
    print("[LLM] response <- ok", flush=True)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}
