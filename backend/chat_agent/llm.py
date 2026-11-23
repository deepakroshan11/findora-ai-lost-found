"""
Minimal client for any OpenAI-compatible chat-completions API.

Groq, Google Gemini (OpenAI-compat endpoint), OpenRouter, Ollama and OpenAI all
speak this format, so switching provider is a config change, not a code change:

    LLM_API_KEY    the provider's API key (required — assistant is disabled without it)
    LLM_BASE_URL   default: Groq  https://api.groq.com/openai/v1
                   Gemini:        https://generativelanguage.googleapis.com/v1beta/openai
    LLM_MODEL      default: llama-3.3-70b-versatile  (must support tool calling)

Only `requests` is used — no provider SDK — so every byte on the wire is visible.
"""
import os

import requests

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class LLMError(Exception):
    """Raised for any failure talking to the LLM provider."""


class LLMClient:
    def __init__(self, api_key=None, base_url=None, model=None, timeout=30):
        self.api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY", "")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages, tools=None) -> dict:
        """Send one chat-completions request and return the assistant `message` dict.

        The returned dict has `content` (str or None) and, when the model wants to
        use a tool, `tool_calls` (a list of {id, type, function:{name, arguments}}).
        """
        if not self.configured:
            raise LLMError("LLM_API_KEY is not set")

        payload = {"model": self.model, "messages": messages, "temperature": 0.2}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f"network error: {exc}") from exc

        if resp.status_code == 429:
            raise LLMError("rate limited by the LLM provider")
        if resp.status_code != 200:
            raise LLMError(f"provider returned HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            return resp.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("unexpected response format from the LLM provider") from exc
