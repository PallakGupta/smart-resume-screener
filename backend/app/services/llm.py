"""Thin OpenAI-compatible chat client returning text or parsed JSON."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from app.config import get_settings


def llm_available() -> bool:
    return bool(get_settings().openai_api_key.strip())


def _client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key.strip():
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def chat_text(
    *,
    system: str,
    user: str,
    temperature: float = 0.2,
) -> str:
    settings = get_settings()
    response = _client().chat.completions.create(
        model=settings.openai_model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def chat_json(
    *,
    system: str,
    user: str,
    temperature: float = 0.2,
) -> dict[str, Any]:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "model": settings.openai_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # response_format is supported by OpenAI; some compatible servers ignore it
    try:
        response = _client().chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        response = _client().chat.completions.create(**kwargs)

    content = (response.choices[0].message.content or "").strip()
    return _parse_json(content)


def chat_json_array(
    *,
    system: str,
    user: str,
    temperature: float = 0.1,
) -> list[Any]:
    text = chat_text(system=system, user=user, temperature=temperature)
    parsed = _parse_json_loose(text)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("skills", "items", "result", "data"):
            if isinstance(parsed.get(key), list):
                return parsed[key]
    return []


def _parse_json(content: str) -> dict[str, Any]:
    parsed = _parse_json_loose(content)
    if isinstance(parsed, dict):
        return parsed
    raise ValueError(f"Expected JSON object, got: {type(parsed).__name__}")


def _parse_json_loose(content: str) -> Any:
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Grab outermost JSON object or array
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = content.find(start_char)
        end = content.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")
