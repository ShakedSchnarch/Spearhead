import hashlib
import json
from dataclasses import dataclass
from typing import Optional

import requests

from spearhead.exceptions import ConfigError, DataSourceError


@dataclass
class AIResult:
    content: str
    source: str  # "remote" | "simulated"
    cached: bool = False


class BaseAIClient:
    def generate(self, prompt: str, context: str) -> AIResult:  # pragma: no cover - interface
        raise NotImplementedError


class SimulatedAIClient(BaseAIClient):
    """
    Deterministic offline client for environments without external AI access.
    """

    def generate(self, prompt: str, context: str) -> AIResult:
        summary = f"[SIMULATED] {prompt[:80]}... Context hash={hashlib.md5(context.encode('utf-8')).hexdigest()[:8]}"
        return AIResult(content=summary, source="simulated", cached=False)


class HTTPAIClient(BaseAIClient):
    """
    Minimal HTTP client for chat-completion style APIs.
    Expects OpenAI-compatible payload shape but is generic enough for most providers.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str],
        model: str,
        max_tokens: int = 256,
        temperature: float = 0.2,
        timeout: int = 20,
    ):
        if not base_url:
            raise ConfigError("AI base_url must be configured for HTTP provider.")
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

    def generate(self, prompt: str, context: str) -> AIResult:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        # Prefer strict JSON output for downstream structured rendering.
        # If a provider rejects response_format, retry once without it.
        payload["response_format"] = {"type": "json_object"}

        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
        if resp.status_code != 200 and "response_format" in payload:
            payload.pop("response_format", None)
            resp = requests.post(self.base_url, json=payload, headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise DataSourceError(f"AI provider error: {resp.status_code}")

        try:
            data = resp.json()
            content = (
                data.get("content")
                or data.get("choices", [{}])[0].get("message", {}).get("content")
                or json.dumps(data)
            )
        except Exception as exc:
            raise DataSourceError(f"Invalid AI response: {exc}")

        return AIResult(content=content, source="remote", cached=False)


def build_ai_client(settings) -> BaseAIClient:
    provider = settings.ai.provider
    if not settings.ai.enabled or provider == "offline":
        return SimulatedAIClient()
    if provider == "http":
        return HTTPAIClient(
            base_url=settings.ai.base_url,
            api_key=settings.ai.api_key,
            model=settings.ai.model,
            max_tokens=settings.ai.max_tokens,
            temperature=settings.ai.temperature,
        )
    raise ConfigError(f"Unknown AI provider: {provider}")
