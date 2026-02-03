import os
import json
from typing import Any, Dict, List

from openai import OpenAI


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is missing. Load it via `source .env` or export it.")
    return v


client = OpenAI(
    api_key=_require_env("OPENAI_API_KEY"),
    timeout=60.0,
    max_retries=2,
)


def call_llm_json(
    *,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 1400,
) -> Dict[str, Any]:
    print(f"[LLM] request -> model={model}, max_tokens={max_tokens}", flush=True)
    resp = client.chat.completions.create(
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
