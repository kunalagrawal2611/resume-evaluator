"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from models import ModelProvider, OllamaProvider, GeminiProvider

logger = logging.getLogger(__name__)


def format_llm_error(exc: Exception) -> str:
    """Turn provider errors into user-friendly messages for the web UI."""
    msg = str(exc).strip()
    lower = msg.lower()

    if any(
        phrase in lower
        for phrase in (
            "quota exceeded",
            "exceeded your current quota",
            "rate limit",
            "resource exhausted",
            "too many requests",
        )
    ) or " 429 " in f" {msg} ":
        return (
            "Gemini API quota exceeded. Resume extraction makes several API calls, "
            "so the free tier daily limit is easy to hit. Wait and try again later, "
            "pick another Gemini model from the dropdown (e.g. Gemini 2.0 Flash Lite), "
            "or switch to Ollama locally."
        )

    if "api key" in lower or "api_key" in lower or "permission denied" in lower:
        return f"Gemini API key error. Check your key in Settings: {msg}"

    if "model" in lower and ("not found" in lower or "not supported" in lower):
        return f"Gemini model error. Pick a different model from the dropdown: {msg}"

    if "unavailable" in lower or " 503 " in f" {msg} ":
        return (
            "Gemini is temporarily overloaded for this model. Wait a minute and try again, "
            "or pick another model from the dropdown."
        )

    return msg or exc.__class__.__name__


class LLMRequestError(RuntimeError):
    """Raised when an LLM provider request fails in a user-visible way."""

    def __init__(self, message: str, *, original: Exception | None = None):
        super().__init__(message)
        self.original = original


def normalize_gemini_api_key(key: str) -> str:
    cleaned = key.strip().strip('"').strip("'")
    return "".join(ch for ch in cleaned if not ch.isspace())


def is_valid_gemini_api_key_format(key: str) -> bool:
    """Google AI Studio keys use AIza (legacy) or AQ. (auth keys)."""
    key = normalize_gemini_api_key(key)
    if key.startswith("AIza") and len(key) >= 30:
        return True
    if key.startswith("AQ.") and len(key) >= 20:
        return True
    return False


def validate_gemini_api_key(key: str) -> None:
    key = normalize_gemini_api_key(key)
    if not key:
        raise ValueError(
            "Gemini API key is required. Paste it in Settings before uploading."
        )
    if not is_valid_gemini_api_key_format(key):
        raise ValueError(
            "That does not look like a Google AI Studio API key. "
            "Create one at https://aistudio.google.com/apikey. "
            "Valid keys start with AIza or AQ."
        )


def sanitize_json_schema_for_gemini(schema: Any) -> Any:
    """Strip Pydantic JSON Schema fields the google-genai SDK rejects."""
    unsupported = {
        "exclusiveMinimum",
        "exclusiveMaximum",
        "title",
        "default",
    }
    if isinstance(schema, dict):
        return {
            key: sanitize_json_schema_for_gemini(value)
            for key, value in schema.items()
            if key not in unsupported
        }
    if isinstance(schema, list):
        return [sanitize_json_schema_for_gemini(item) for item in schema]
    return schema


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from markdown code blocks.

    Args:
        response_text: Text that may contain JSON wrapped in markdown code blocks

    Returns:
        Text with markdown code block syntax removed
    """

    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8 :]

    # Remove leading ```json if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    # Remove trailing ``` if present
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider based on the model name.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider (either OllamaProvider or GeminiProvider)
    """
    import prompt

    gemini_api_key = prompt.GEMINI_API_KEY
    active_provider = prompt.PROVIDER

    model_provider = prompt.MODEL_PROVIDER_MAPPING.get(model_name)
    if model_provider is None:
        if active_provider == ModelProvider.GEMINI.value or model_name.startswith("gemini"):
            model_provider = ModelProvider.GEMINI
        else:
            model_provider = ModelProvider.OLLAMA

    if model_provider == ModelProvider.GEMINI:
        validate_gemini_api_key(gemini_api_key)
        logger.info(f"🔄 Using Google Gemini API provider with model {model_name}")
        return GeminiProvider(api_key=gemini_api_key)

    logger.info(f"🔄 Using Ollama provider with model {model_name}")
    return OllamaProvider()
