"""Tests for the LLM provider factory and Gemini message conversion."""

from __future__ import annotations

from app.config import Settings
from app.llm import GeminiClient, OllamaClient, create_llm_client, to_gemini_payload


def test_factory_default_returns_ollama_client():
    settings = Settings(llm_provider="ollama")
    client = create_llm_client(settings)
    assert isinstance(client, OllamaClient)


def test_factory_returns_gemini_client_when_selected():
    settings = Settings(llm_provider="gemini", gemini_api_key="dummy")
    client = create_llm_client(settings)
    assert isinstance(client, GeminiClient)


def test_to_gemini_payload_lifts_system_to_systemInstruction():
    messages = [
        {"role": "system", "content": "you are a helpful copilot"},
        {"role": "user", "content": "hello"},
    ]
    payload = to_gemini_payload(messages)
    assert payload["systemInstruction"]["parts"][0]["text"] == "you are a helpful copilot"
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"][0]["text"] == "hello"


def test_to_gemini_payload_renames_assistant_to_model():
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello back"},
        {"role": "user", "content": "next"},
    ]
    payload = to_gemini_payload(messages)
    roles = [c["role"] for c in payload["contents"]]
    assert roles == ["user", "model", "user"]
    assert "systemInstruction" not in payload


def test_to_gemini_payload_merges_multiple_system_messages():
    messages = [
        {"role": "system", "content": "rule one"},
        {"role": "system", "content": "rule two"},
        {"role": "user", "content": "go"},
    ]
    payload = to_gemini_payload(messages)
    text = payload["systemInstruction"]["parts"][0]["text"]
    assert "rule one" in text and "rule two" in text
