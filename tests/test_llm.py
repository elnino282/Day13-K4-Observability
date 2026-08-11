from __future__ import annotations

from types import SimpleNamespace

from google import genai

from app.llm import GeminiLLM, build_llm


def test_build_llm_defaults_to_fake(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    client = build_llm()
    assert client.provider == "fake"


def test_gemini_llm_maps_text_and_usage_without_network(monkeypatch) -> None:
    response = SimpleNamespace(
        text="Câu trả lời quan sát được.",
        usage_metadata=SimpleNamespace(
            prompt_token_count=12,
            candidates_token_count=8,
            thoughts_token_count=3,
        ),
    )

    class Models:
        def generate_content(self, **kwargs):
            assert kwargs["model"] == "gemini-3.1-flash-lite"
            assert kwargs["config"]["max_output_tokens"] == 1024
            return response

    class Client:
        models = Models()

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    monkeypatch.setattr(genai, "Client", lambda **kwargs: Client())
    client = GeminiLLM(api_key="test-key", model="gemini-3.1-flash-lite")
    result = client.generate("Test prompt")

    assert result.text == "Câu trả lời quan sát được."
    assert result.usage.input_tokens == 12
    assert result.usage.output_tokens == 11
