"""Thin client for any OpenAI-compatible chat endpoint (Groq, Ollama, OpenAI, ...)."""

import json
import re
import time
from typing import TypeVar

from openai import BadRequestError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from opsgraph import config

T = TypeVar("T", bound=BaseModel)


class LLMNotConfigured(RuntimeError):
    pass


class LLMClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        key = api_key if api_key is not None else config.LLM_API_KEY
        if not key:
            raise LLMNotConfigured("LLM_API_KEY is not set; set it in .env to use the LLM path.")
        self.model = model or config.LLM_MODEL
        self._client = OpenAI(base_url=base_url or config.LLM_BASE_URL, api_key=key, timeout=90, max_retries=8)

    @staticmethod
    def _extra() -> dict:
        # For reasoning models on endpoints that accept it (e.g. Groq gpt-oss).
        effort = config.LLM_REASONING_EFFORT
        return {"extra_body": {"reasoning_effort": effort}} if effort else {}

    def _create(self, **kwargs):
        """chat.completions.create that waits out per-minute rate limits (free tiers are tight)."""
        for attempt in range(12):
            try:
                return self._client.chat.completions.create(**kwargs)
            except RateLimitError as exc:
                m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", str(exc))
                wait = (int(m.group(1) or 0) * 60 + float(m.group(2)) + 1) if m else 20
                if wait > 300 or attempt == 11:  # daily quota, not worth waiting for
                    raise
                time.sleep(wait)

    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        resp = self._create(
            model=self.model,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **self._extra(),
        )
        return resp.choices[0].message.content or ""

    def structured(self, schema: type[T], system: str, user: str, retries: int = 2) -> T:
        """Ask for JSON matching `schema`; validate with Pydantic and retry (up to `retries` times) on failure."""
        json_schema = schema.model_json_schema()
        prompt = f"{user}\n\nReturn only JSON that matches this JSON Schema:\n{json.dumps(json_schema)}"
        last_error = ""
        for _ in range(retries + 1):
            extra = f"\n\nYour previous reply was invalid: {last_error}" if last_error else ""
            try:
                resp = self._create(
                    model=self.model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt + extra},
                    ],
                )
                return schema.model_validate_json(resp.choices[0].message.content or "")
            except (ValidationError, BadRequestError) as exc:  # invalid or empty JSON: retry
                last_error = str(exc)[:500]
        raise ValueError(f"model did not return valid {schema.__name__}: {last_error}")
