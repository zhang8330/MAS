import re
from contextvars import ContextVar
from openai import OpenAI

_runtime_cfg: ContextVar[dict | None] = ContextVar("runtime_llm_cfg", default=None)


def set_runtime_llm_config(cfg: dict):
    return _runtime_cfg.set(cfg)


def reset_runtime_llm_config(token):
    _runtime_cfg.reset(token)


def _client_and_model(model: str):
    cfg = _runtime_cfg.get() or {}
    api_key = cfg.get("api_key") or ""
    base_url = cfg.get("base_url") or ""
    m = cfg.get("model") or model
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs), m


def call_llm(system: str, user: str, model: str) -> str:
    try:
        client, mm = _client_and_model(model)
        resp = client.chat.completions.create(
            model=mm,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        msg = str(e)
        if "Missing credentials" in msg or "OPENAI_API_KEY" in msg:
            return "{\"mock\": true, \"message\": \"missing_api_key\"}"
        return "{\"mock\": true, \"message\": \"llm_unavailable\"}"


def extract_code(text: str) -> str:
    m = re.search(r"```(?:go)?\n(.*?)```", text or "", re.DOTALL)
    return (m.group(1) if m else (text or "")).strip()
