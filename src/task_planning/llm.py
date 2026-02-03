import os
import json
import time
import random
from typing import Any, Dict, List

from openai import OpenAI


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"{name} is missing. Load it via `source .env` or export it.")
    return v


# ✅ 無限待ちを防ぐ（ただし502等は自前リトライで制御する）
client = OpenAI(
    api_key=_require_env("OPENAI_API_KEY"),
    timeout=60.0,   # 1リクエストあたりの最大待ち時間
    max_retries=0,  # SDKの自動リトライは使わない（自前で制御）
)


def call_llm_json(
    *,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 1400,
) -> Dict[str, Any]:
    print(f"[LLM] request -> model={model}, max_tokens={max_tokens}", flush=True)

    def _do_request() -> Any:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

    try:
        resp = _do_request()
    except Exception as e:
        # 502/503/504/429 は一時障害として再試行（指数バックオフ＋ジッター）
        msg = str(e)
        retryable = any(x in msg for x in ["502", "503", "504", "429"])
        if retryable:
            last = e
            for i in range(3):  # 最大3回
                wait = min(8.0, (2 ** i) + random.random())  # 1~2, 2~3, 4~5秒程度
                print(f"[LLM] retry {i+1}/3 after {wait:.1f}s due to: {type(last).__name__}", flush=True)
                time.sleep(wait)
                try:
                    resp = _do_request()
                    break
                except Exception as e2:
                    last = e2
            else:
                raise RuntimeError(
                    f"LLM request failed after retries. error={type(last).__name__}: {last}"
                ) from last
        else:
            raise RuntimeError(
                f"LLM request failed (non-retryable). error={type(e).__name__}: {e}"
            ) from e

    text = resp.choices[0].message.content or "{}"
    print("[LLM] response <- ok", flush=True)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSONが壊れてても後段(Judge/Repair)で直せるよう raw を残す
        return {"_raw": text}