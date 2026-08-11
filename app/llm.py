from __future__ import annotations

import os
from typing import Protocol

from .incidents import STATE
from .mock_llm import FakeLLM, FakeResponse, FakeUsage


class LLMClient(Protocol):
    model: str
    provider: str

    def generate(self, prompt: str) -> FakeResponse: ...


class GeminiLLM:
    provider = "gemini"

    def __init__(self, *, api_key: str, model: str) -> None:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str) -> FakeResponse:
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - guarded by requirements
            raise RuntimeError("google-genai is required for the Gemini provider") from exc

        with genai.Client(api_key=self.api_key) as client:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"max_output_tokens": 512},
            )

        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty text response")

        usage = response.usage_metadata
        input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        visible_output = int(getattr(usage, "candidates_token_count", 0) or 0)
        thinking_output = int(getattr(usage, "thoughts_token_count", 0) or 0)
        output_tokens = visible_output + thinking_output
        if STATE["cost_spike"]:
            output_tokens *= 4

        return FakeResponse(
            text=text,
            usage=FakeUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            model=self.model,
        )


def build_llm(model: str | None = None) -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "fake").strip().lower()
    if provider == "gemini":
        resolved_model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        return GeminiLLM(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=resolved_model,
        )
    if provider == "fake":
        resolved_model = model or os.getenv("LLM_MODEL", "claude-sonnet-4-5")
        client = FakeLLM(model=resolved_model)
        client.provider = "fake"
        return client
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
