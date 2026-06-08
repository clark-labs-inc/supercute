"""Minimal OpenAI-compatible chat client used by the benchmark harness.

The client intentionally depends only on the Python standard library. It supports
OpenRouter/OpenAI-style `/chat/completions` endpoints and optional extra request
fields such as provider-specific reasoning controls.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

Message = Mapping[str, str]


@dataclass
class Endpoint:
    """Connection details for one OpenAI-compatible chat model."""

    base_url: str
    model: str
    api_key: Optional[str] = None
    timeout: float = 120.0
    headers: Mapping[str, str] = field(default_factory=dict)
    extra_body: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")


def chat_raw(
    ep: Endpoint,
    messages: Sequence[Message],
    *,
    temperature: float = 0.0,
    **extra_body: Any,
) -> dict[str, Any]:
    """Return the raw JSON response from an OpenAI-compatible chat endpoint."""

    body_dict: dict[str, Any] = {
        "model": ep.model,
        "messages": list(messages),
        "temperature": temperature,
    }
    body_dict.update(dict(ep.extra_body))
    body_dict.update(extra_body)
    body = json.dumps(body_dict).encode("utf-8")

    headers = {"Content-Type": "application/json", **dict(ep.headers)}
    if ep.api_key:
        headers["Authorization"] = f"Bearer {ep.api_key}"

    req = urllib.request.Request(
        f"{ep.base_url}/chat/completions",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=ep.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code} from {ep.base_url}: {detail}") from exc


def chat(
    ep: Endpoint,
    messages: Sequence[Message],
    temperature: float = 0.0,
    **extra_body: Any,
) -> str:
    """Return only the assistant content from a chat completion."""

    payload = chat_raw(ep, messages, temperature=temperature, **extra_body)
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"no choices in response: {str(payload)[:500]}")
    return (choices[0].get("message") or {}).get("content") or ""
