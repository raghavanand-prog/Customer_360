"""Provider-agnostic LLM interface (§7 of the Adobe-JD AI phase).

Two implementations exist:

- `NotConfiguredProvider` -- the one actually running in this environment,
  since no LLM API key is configured or paid for anywhere in this project.
  It never fabricates a model response; it says plainly that no provider is
  configured and returns the retrieved context so the caller still gets
  something useful and honest.
- `AnthropicProvider` -- a real implementation using Anthropic's Messages
  API over a plain HTTPS call (stdlib `urllib`, no SDK dependency added for
  a path that has not been exercised against a live account). It is
  code-complete and unit-testable for its request/response shaping, but its
  actual network behaviour against the real API has NOT been verified live
  in this session -- there is no API key available to do so. This is
  reported honestly in docs/AI_EVALUATION.md rather than claimed as tested.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Iterator, Protocol

NOT_CONFIGURED_MESSAGE = (
    "AI provider not configured. No LLM API key is set (ANTHROPIC_API_KEY), "
    "so no model-generated explanation is available. The retrieved "
    "platform documentation and customer data below are real; only the "
    "natural-language synthesis step is unavailable."
)


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str | None = None
    configured: bool = True
    raw: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    def generate(self, system: str, messages: list[LLMMessage]) -> LLMResponse:
        ...

    def stream(self, system: str, messages: list[LLMMessage]) -> Iterator[str]:
        ...

    def structured_generate(self, system: str, messages: list[LLMMessage], schema: dict) -> dict:
        ...


class NotConfiguredProvider:
    """The provider actually active in this environment (no API key set)."""

    name = "none"

    def generate(self, system: str, messages: list[LLMMessage]) -> LLMResponse:
        return LLMResponse(text=NOT_CONFIGURED_MESSAGE, provider=self.name, model=None, configured=False)

    def stream(self, system: str, messages: list[LLMMessage]) -> Iterator[str]:
        # Deliberately yields the full message once -- never simulates
        # token-by-token output with artificial delays for an unconfigured
        # provider, per the "do not fake streaming" requirement.
        yield NOT_CONFIGURED_MESSAGE

    def structured_generate(self, system: str, messages: list[LLMMessage], schema: dict) -> dict:
        return {"configured": False, "message": NOT_CONFIGURED_MESSAGE}


class AnthropicProvider:
    """Real Anthropic Messages API integration.

    Implemented against the documented API shape but not exercised live in
    this session (no credential available here). If you configure
    ANTHROPIC_API_KEY yourself and it doesn't work, that is real,
    unverified-by-me risk -- treat it as such until you've tested it.
    """

    name = "anthropic"
    _endpoint = "https://api.anthropic.com/v1/messages"
    _api_version = "2023-06-01"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def _request(self, system: str, messages: list[LLMMessage], stream: bool, max_tokens: int = 1024) -> dict:
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "stream": stream,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        req = urllib.request.Request(
            self._endpoint,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": self._api_version,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed HTTPS host
            return json.loads(resp.read().decode("utf-8"))

    def generate(self, system: str, messages: list[LLMMessage]) -> LLMResponse:
        try:
            data = self._request(system, messages, stream=False)
        except urllib.error.URLError as exc:
            return LLMResponse(
                text=f"AI provider request failed: {exc}. No fabricated answer is returned.",
                provider=self.name,
                model=self._model,
                configured=True,
            )
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        return LLMResponse(text=text, provider=self.name, model=self._model, configured=True, raw=data)

    def stream(self, system: str, messages: list[LLMMessage]) -> Iterator[str]:
        # SSE token streaming against the real API is implemented at the
        # transport level in c360/api/v1/ai.py (which reads this provider's
        # raw HTTPS response line-by-line); this convenience method returns
        # the full response in one piece for callers that don't need
        # incremental tokens, since it delegates to `generate`.
        yield self.generate(system, messages).text

    def structured_generate(self, system: str, messages: list[LLMMessage], schema: dict) -> dict:
        instructed_system = system + "\n\nRespond with JSON matching this schema only: " + json.dumps(schema)
        response = self.generate(instructed_system, messages)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "model did not return valid JSON", "raw_text": response.text}


def get_llm_provider(api_key: str, model: str) -> LLMProvider:
    if api_key:
        return AnthropicProvider(api_key=api_key, model=model)
    return NotConfiguredProvider()
