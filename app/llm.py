"""LLM chat clients.

Two providers are supported and share a small ``LlmClient`` protocol so the
rest of the app does not care which one is configured:

* :class:`OllamaClient` — local Ollama server, ``/api/chat`` endpoint.
* :class:`GeminiClient` — Google Gemini REST API, ``generateContent`` endpoint.

The factory :func:`create_llm_client` returns the right client based on
``settings.llm_provider``. Both clients wrap an async ``httpx.AsyncClient`` with
bounded timeouts and bounded retries; all failures surface as ``UpstreamError``
so the API layer can return a consistent 502.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

import httpx

from .config import Settings
from .errors import UpstreamError

logger = logging.getLogger(__name__)


class LlmClient(Protocol):
    """Common surface shared by OllamaClient and GeminiClient."""

    async def chat(self, messages: list[dict[str, str]]) -> str: ...

    async def ping(self) -> bool: ...

    async def aclose(self) -> None: ...


# --------------------------------------------------------------------------- #
# Ollama                                                                      #
# --------------------------------------------------------------------------- #
class OllamaClient:
    """Thin async wrapper around the Ollama chat API."""

    def __init__(self, settings: Settings) -> None:
        self._url = settings.ollama_url
        self._model = settings.model_name
        self._max_retries = max(0, settings.llm_max_retries)
        self._client = httpx.AsyncClient(timeout=settings.llm_timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {"model": self._model, "messages": messages, "stream": False}
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(self._url, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content")
                if not isinstance(content, str) or not content.strip():
                    raise UpstreamError("Model returned an empty response")
                return content
            except UpstreamError:
                raise
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.warning(
                    "Ollama HTTP %s on attempt %d", exc.response.status_code, attempt + 1
                )
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning("Ollama request failed on attempt %d: %s", attempt + 1, exc)

            if attempt < self._max_retries:
                await asyncio.sleep(0.5 * (2**attempt))

        raise UpstreamError(f"Language model is unavailable: {last_exc}")

    async def ping(self) -> bool:
        base = self._url.rsplit("/api/", 1)[0]
        try:
            resp = await self._client.get(f"{base}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False


# --------------------------------------------------------------------------- #
# Gemini                                                                      #
# --------------------------------------------------------------------------- #
def to_gemini_payload(messages: list[dict[str, str]]) -> dict:
    """Convert OpenAI-style messages to Gemini's generateContent payload.

    * ``system`` messages collapse into ``systemInstruction``.
    * ``assistant`` becomes Gemini's ``model`` role.
    * Other roles are sent as ``user``.
    """
    system_parts: list[str] = []
    contents: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        text = str(msg.get("content", ""))
        if role == "system":
            if text:
                system_parts.append(text)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})

    body: dict = {"contents": contents}
    if system_parts:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
    return body


class GeminiClient:
    """Async client for the Google Gemini ``generateContent`` REST endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.model_name or "gemini-2.5-flash"
        self._base = settings.gemini_url.rstrip("/")
        self._max_retries = max(0, settings.llm_max_retries)
        self._client = httpx.AsyncClient(timeout=settings.llm_timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    async def chat(self, messages: list[dict[str, str]]) -> str:
        if not self._api_key:
            raise UpstreamError(
                "Gemini API key is not configured. Set COPILOT_GEMINI_API_KEY in .env."
            )

        url = f"{self._base}/{self._model}:generateContent"
        payload = to_gemini_payload(messages)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    url, json=payload, headers=self._headers()
                )
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    raise UpstreamError(
                        f"Gemini returned no candidates (response: {data})"
                    )
                parts = candidates[0].get("content", {}).get("parts") or []
                text = "".join(p.get("text", "") for p in parts)
                if not text.strip():
                    raise UpstreamError("Gemini returned an empty response")
                return text
            except UpstreamError:
                raise
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.warning(
                    "Gemini HTTP %s on attempt %d: %s",
                    exc.response.status_code,
                    attempt + 1,
                    exc.response.text[:300],
                )
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning("Gemini request failed on attempt %d: %s", attempt + 1, exc)

            if attempt < self._max_retries:
                await asyncio.sleep(0.5 * (2**attempt))

        raise UpstreamError(f"Gemini is unavailable: {last_exc}")

    async def ping(self) -> bool:
        if not self._api_key:
            return False
        try:
            resp = await self._client.get(
                f"{self._base}?pageSize=1", headers=self._headers(), timeout=5.0
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False


# --------------------------------------------------------------------------- #
# Factory                                                                     #
# --------------------------------------------------------------------------- #
def create_llm_client(settings: Settings) -> LlmClient:
    """Build the LLM client matching ``settings.llm_provider``."""
    if settings.llm_provider == "gemini":
        logger.info("Using Gemini provider with model %s", settings.model_name)
        return GeminiClient(settings)
    logger.info("Using Ollama provider with model %s", settings.model_name)
    return OllamaClient(settings)
